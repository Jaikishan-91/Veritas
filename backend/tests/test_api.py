import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VERITAS_DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("VERITAS_LOCAL_STORAGE_DIR", str(tmp_path / "obj"))
    monkeypatch.setenv("VERITAS_WORKERS", "0")
    from app import config, db, storage, worker
    for fn in (config.get_settings, db.get_sessionmaker, storage.get_store, worker._pool):
        fn.cache_clear()
    from app.main import app
    with TestClient(app) as c:
        yield c
    for fn in (config.get_settings, db.get_sessionmaker, storage.get_store):
        fn.cache_clear()


def test_upload_analyze_review_flow(client, tampered_pdf, monkeypatch):
    from app import config
    monkeypatch.setattr(config.get_settings(), "min_coverage", 0.99)  # OCR disabled -> coverage < 1 -> review
    r = client.post("/api/documents", files={"file": ("inv.pdf", tampered_pdf, "application/pdf")})
    assert r.status_code == 201, r.text
    doc_id = r.json()["id"]
    d = client.get(f"/api/documents/{doc_id}").json()
    assert d["status"] == "completed" and d["risk_band"] == "high"
    assert d["findings"] and all(0 <= f["contribution"] <= 1 for f in d["findings"])
    assert any(f["bbox"] for f in d["findings"])
    assert client.get(d["file_url"]).content == tampered_pdf
    for a in d["artifacts"]:
        assert client.get(a["url"]).headers["content-type"] == "image/png"
    assert d["needs_review"]
    assert doc_id in [x["id"] for x in client.get("/api/reviews").json()]
    rv = client.post(f"/api/documents/{doc_id}/reviews", json={"decision": "tampered", "notes": "amount retyped"})
    assert rv.status_code == 201
    assert doc_id not in [x["id"] for x in client.get("/api/reviews").json()]


def test_upload_rejects_unsupported(client):
    r = client.post("/api/documents", files={"file": ("x.pdf", b"GIF89a fake", "application/pdf")})
    assert r.status_code == 415


def test_upload_rejects_oversize(client, monkeypatch):
    from app import config
    monkeypatch.setattr(config.get_settings(), "max_upload_mb", 0)
    r = client.post("/api/documents", files={"file": ("a.png", b"\x89PNG\r\n\x1a\n" + b"0" * 10, "image/png")})
    assert r.status_code == 413


def test_corrupt_file_fails_cleanly(client):
    r = client.post("/api/documents", files={"file": ("a.png", b"\x89PNG\r\n\x1a\nbroken", "image/png")})
    d = client.get(f"/api/documents/{r.json()['id']}").json()
    assert d["status"] == "failed" and "Unreadable" in d["error"]


def test_invalid_review_and_404(client):
    assert client.get("/api/documents/nope").status_code == 404
    assert client.post("/api/documents/nope/reviews", json={"decision": "tampered"}).status_code == 404

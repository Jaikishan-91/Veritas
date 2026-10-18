import pytest
from fastapi.testclient import TestClient

ADMIN = ("admin@example.com", "admin-password-1")
CSRF = {"X-Requested-With": "veritas"}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("VERITAS_DATABASE_URL", f"sqlite:///{tmp_path}/t.db")
    monkeypatch.setenv("VERITAS_LOCAL_STORAGE_DIR", str(tmp_path / "obj"))
    monkeypatch.setenv("VERITAS_WORKERS", "0")
    monkeypatch.setenv("VERITAS_BOOTSTRAP_ADMIN_EMAIL", ADMIN[0])
    monkeypatch.setenv("VERITAS_BOOTSTRAP_ADMIN_PASSWORD", ADMIN[1])
    from app import auth, config, db, storage, worker
    caches = (config.get_settings, db.get_sessionmaker, storage.get_store, worker._pool)
    for fn in caches:
        fn.cache_clear()
    auth.reset_throttle()
    from app.main import app
    with TestClient(app):  # run lifespan once (schema + bootstrap admin)
        yield app
    for fn in caches:
        fn.cache_clear()


def login(app, email, password) -> TestClient:
    c = TestClient(app, headers=CSRF)
    r = c.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return c


@pytest.fixture
def admin(app):
    return login(app, *ADMIN)


def make_user(admin, email, role, pw="user-password-1"):
    r = admin.post("/api/users", json={"email": email, "password": pw, "role": role})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def client(admin):
    return admin


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
    assert rv.status_code == 201 and rv.json()["reviewer"] == ADMIN[0]
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


# --- authentication / authorization -------------------------------------------------------------

def test_unauthenticated_rejected(app):
    c = TestClient(app, headers=CSRF)
    assert c.get("/api/health").status_code == 200
    for path in ("/api/documents", "/api/reviews", "/api/auth/me", "/api/users"):
        assert c.get(path).status_code == 401, path
    assert c.post("/api/documents", files={"file": ("a.png", b"x", "image/png")}).status_code == 401


def test_login_failures_and_lockout(app):
    c = TestClient(app)
    for _ in range(5):
        assert c.post("/api/auth/login", json={"email": ADMIN[0], "password": "wrong"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}).status_code == 429
    assert c.post("/api/auth/login", json={"email": "nobody@x.io", "password": "x"}).status_code == 401


def test_session_cookie_flags_and_logout(app):
    c = TestClient(app, headers=CSRF)
    r = c.post("/api/auth/login", json={"email": ADMIN[0].upper(), "password": ADMIN[1]})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/api" in cookie
    assert c.get("/api/auth/me").json()["role"] == "admin"
    token = c.cookies.get("veritas_session")
    assert c.post("/api/auth/logout").status_code == 204
    replay = TestClient(app, cookies={"veritas_session": token})
    assert replay.get("/api/auth/me").status_code == 401  # session revoked server-side


def test_csrf_header_required_for_writes(admin, app):
    no_header = TestClient(app, cookies=dict(admin.cookies))
    assert no_header.get("/api/documents").status_code == 200
    assert no_header.post("/api/documents", files={"file": ("a.png", b"x", "image/png")}).status_code == 403


def test_analyst_isolation_and_roles(admin, app, copy_move_png):
    make_user(admin, "a1@example.com", "analyst")
    make_user(admin, "a2@example.com", "analyst")
    make_user(admin, "rev@example.com", "reviewer")
    a1, a2 = login(app, "a1@example.com", "user-password-1"), login(app, "a2@example.com", "user-password-1")
    rev = login(app, "rev@example.com", "user-password-1")

    doc_id = a1.post("/api/documents", files={"file": ("c.png", copy_move_png[0], "image/png")}).json()["id"]
    d = a1.get(f"/api/documents/{doc_id}").json()
    assert [x["id"] for x in a1.get("/api/documents").json()] == [doc_id]
    # another analyst cannot see, download or list it
    assert a2.get(f"/api/documents/{doc_id}").status_code == 404
    assert a2.get(f"/api/documents/{doc_id}/file").status_code == 404
    if d["artifacts"]:
        assert a2.get(d["artifacts"][0]["url"]).status_code == 404
    assert a2.get("/api/documents").json() == []
    # analysts cannot review or manage users
    assert a1.get("/api/reviews").status_code == 403
    assert a1.post(f"/api/documents/{doc_id}/reviews", json={"decision": "tampered"}).status_code == 403
    assert a1.get("/api/users").status_code == 403
    # reviewers see everything and can review
    assert rev.get(f"/api/documents/{doc_id}").status_code == 200
    assert rev.post(f"/api/documents/{doc_id}/reviews", json={"decision": "authentic"}).status_code == 201
    assert rev.post("/api/users", json={"email": "x@y.z", "password": "0123456789"}).status_code == 403


def test_user_management(admin, app):
    u = make_user(admin, "bob@example.com", "analyst")
    assert admin.post("/api/users", json={"email": "BOB@example.com", "password": "0123456789"}).status_code == 409
    assert admin.post("/api/users", json={"email": "short@x.io", "password": "123"}).status_code == 422
    bob = login(app, "bob@example.com", "user-password-1")
    assert admin.patch(f"/api/users/{u['id']}", json={"active": False}).json()["active"] is False
    assert bob.get("/api/auth/me").status_code == 401  # sessions revoked on deactivation
    assert TestClient(app).post("/api/auth/login", json={"email": "bob@example.com", "password": "user-password-1"}).status_code == 401
    me = admin.get("/api/auth/me").json()
    assert admin.patch(f"/api/users/{me['id']}", json={"role": "analyst"}).status_code == 400

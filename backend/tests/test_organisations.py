from fastapi.testclient import TestClient

from test_api import CSRF, login, make_user
from test_api import admin, app  # noqa: F401
from test_signup import PW, code_of, outbox, signup  # noqa: F401


def org_signup(app, outbox, email="org@example.com", username="acme"):
    c = TestClient(app, headers=CSRF)
    assert signup(c, email, username=username, account_type="organisation").status_code == 202
    r = c.post("/api/auth/verify", json={"email": email, "code": code_of(outbox)})
    assert r.status_code == 200, r.text
    return c, r.json()


def test_organisation_needs_approval_then_reviews_submitted_documents(admin, app, outbox, clean_pdf, monkeypatch):
    from app import config
    monkeypatch.setattr(config.get_settings(), "min_coverage", 0.0)  # clean doc is not routed to the admin queue
    org, me = org_signup(app, outbox)
    assert me["role"] == "organisation" and me["approved"] is False and me["username"] == "acme"
    make_user(admin, "u@example.com", "user")
    user = login(app, "u@example.com", "user-password-1")

    # pending: cannot review, not offered to users, cannot be submitted to
    assert org.get("/api/reviews").status_code == 403
    assert user.get("/api/organisations").json() == []
    up = {"files": {"file": ("c.pdf", clean_pdf, "application/pdf")}, "data": {"organisation_id": me["id"]}}
    assert user.post("/api/documents", **up).status_code == 422

    assert admin.patch(f"/api/users/{me['id']}", json={"approved": True}).json()["approved"] is True
    assert user.get("/api/organisations").json() == [{"id": me["id"], "username": "acme"}]
    doc = user.post("/api/documents", **up).json()
    assert doc["organisation"] == "acme" and doc["needs_review"] is False

    # every submitted document reaches the organisation, flagged or not; nobody else gains access
    assert [d["id"] for d in org.get("/api/reviews").json()] == [doc["id"]]
    assert org.get(f"/api/documents/{doc['id']}/file").status_code == 200
    assert admin.get(f"/api/documents/{doc['id']}").status_code == 404  # unflagged, unreviewed, not the admin's
    assert org.post(f"/api/documents/{doc['id']}/reviews", json={"decision": "accepted"}).status_code == 201
    other, _ = org_signup(app, outbox, "org2@example.com", "otherorg")
    admin.patch(f"/api/users/{_['id']}", json={"approved": True})
    assert other.get(f"/api/documents/{doc['id']}").status_code == 404

    # revoking approval revokes access
    admin.patch(f"/api/users/{me['id']}", json={"approved": False})
    assert org.get(f"/api/documents/{doc['id']}").status_code == 404


def test_users_cannot_submit_to_non_organisations(admin, app, clean_pdf):
    u = make_user(admin, "u@example.com", "user")
    other = make_user(admin, "v@example.com", "user")
    c = login(app, "u@example.com", "user-password-1")
    for target in (other["id"], u["id"], "missing"):
        r = c.post("/api/documents", files={"file": ("c.pdf", clean_pdf, "application/pdf")},
                   data={"organisation_id": target})
        assert r.status_code == 422


def test_usernames_unique_and_usable_for_login(admin, app, outbox):
    make_user(admin, "jkuser@example.com", "user")  # username "jkuser"
    c = TestClient(app, headers=CSRF)
    assert signup(c, "new@example.com", username="JKUser").status_code == 409  # case-insensitive
    assert signup(c, "new@example.com", username="a b").status_code == 422
    r = admin.post("/api/users", json={"email": "x@example.com", "username": "jkuser", "password": "0123456789"})
    assert r.status_code == 409
    assert login(app, "JKuser", "user-password-1").get("/api/auth/me").json()["email"] == "jkuser@example.com"
    assert TestClient(app).post("/api/auth/login", json={"email": "jkuser", "password": "wrong-password"}).status_code == 401


def test_upgrade_adds_columns_to_legacy_tables(tmp_path):
    from sqlalchemy import create_engine, inspect, text

    from app.db import upgrade_data
    eng = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with eng.begin() as c:
        c.execute(text("CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, email VARCHAR(254), role VARCHAR(16))"))
        c.execute(text("CREATE TABLE documents (id VARCHAR(36) PRIMARY KEY)"))
        c.execute(text("CREATE TABLE reviews (id INTEGER PRIMARY KEY, decision VARCHAR(16))"))
        c.execute(text("INSERT INTO users VALUES ('r1', 'rev@example.com', 'reviewer')"))
    upgrade_data(eng)
    upgrade_data(eng)  # idempotent
    cols = {t: {c["name"] for c in inspect(eng).get_columns(t)} for t in ("users", "documents")}
    assert {"username", "approved"} <= cols["users"] and "organisation_id" in cols["documents"]
    with eng.connect() as c:
        # existing reviewers become organisations that are already approved
        assert c.execute(text("SELECT role, approved FROM users")).one() == ("organisation", 1)

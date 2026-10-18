from test_api import admin, app, login, make_user  # noqa: F401


def setup_flagged(admin, app, copy_move_png):
    make_user(admin, "owner@example.com", "user")
    make_user(admin, "rev@example.com", "reviewer")
    owner, rev = login(app, "owner@example.com", "user-password-1"), login(app, "rev@example.com", "user-password-1")
    doc_id = owner.post("/api/documents", files={"file": ("c.png", copy_move_png[0], "image/png")}).json()["id"]
    assert owner.get(f"/api/documents/{doc_id}").json()["needs_review"]
    return owner, rev, doc_id


def test_decision_notifies_owner_in_app_and_by_email(admin, app, copy_move_png, monkeypatch):
    from app import notifications
    sent = []
    monkeypatch.setattr(notifications, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    owner, rev, doc_id = setup_flagged(admin, app, copy_move_png)
    assert rev.post(f"/api/documents/{doc_id}/reviews", json={"decision": "rejected", "notes": "patch cloned"}).status_code == 201
    ns = owner.get("/api/notifications").json()
    assert len(ns) == 1 and ns[0]["kind"] == "review_rejected" and not ns[0]["read"]
    assert "rejected" in ns[0]["message"] and "patch cloned" in ns[0]["message"] and ns[0]["document_id"] == doc_id
    assert sent and sent[0][0] == "owner@example.com" and "rejected" in sent[0][1]
    summary = owner.get("/api/documents").json()[0]
    assert summary["decision"] == "rejected" and summary["reviewed"]
    # other users cannot see or mark the owner's notifications
    assert rev.get("/api/notifications").json() == []
    assert rev.post(f"/api/notifications/{ns[0]['id']}/read").status_code == 404
    assert owner.post(f"/api/notifications/{ns[0]['id']}/read").json()["read"] is True
    rev.post(f"/api/documents/{doc_id}/reviews", json={"decision": "accepted"})
    assert owner.post("/api/notifications/read-all").status_code == 204
    assert all(n["read"] for n in owner.get("/api/notifications").json())


def test_email_failure_does_not_fail_review(admin, app, copy_move_png, monkeypatch):
    from app import notifications
    from app.mailer import MailError

    def boom(*a):
        raise MailError("down")
    monkeypatch.setattr(notifications, "send_email", boom)
    owner, rev, doc_id = setup_flagged(admin, app, copy_move_png)
    assert rev.post(f"/api/documents/{doc_id}/reviews", json={"decision": "accepted"}).status_code == 201
    assert owner.get("/api/notifications").json()[0]["kind"] == "review_accepted"


def test_reviewers_keep_access_after_review(admin, app, copy_move_png, monkeypatch):
    from app import notifications
    monkeypatch.setattr(notifications, "send_email", lambda *a: None)
    owner, rev, doc_id = setup_flagged(admin, app, copy_move_png)
    rev.post(f"/api/documents/{doc_id}/reviews", json={"decision": "accepted"})
    assert doc_id not in [d["id"] for d in rev.get("/api/reviews").json()]  # pending tab
    reviewed = rev.get("/api/reviews", params={"include_reviewed": True}).json()
    assert [d["decision"] for d in reviewed if d["id"] == doc_id] == ["accepted"]
    for who in (rev, admin):
        assert who.get(f"/api/documents/{doc_id}").status_code == 200
        assert who.get(f"/api/documents/{doc_id}/file").status_code == 200


def test_invalid_decision_and_self_review_no_notification(admin, app, copy_move_png):
    _, rev, doc_id = setup_flagged(admin, app, copy_move_png)
    assert rev.post(f"/api/documents/{doc_id}/reviews", json={"decision": "tampered"}).status_code == 422
    own = admin.post("/api/documents", files={"file": ("c.png", copy_move_png[0], "image/png")}).json()["id"]
    admin.post(f"/api/documents/{own}/reviews", json={"decision": "accepted"})
    assert admin.get("/api/notifications").json() == []


def test_data_upgrade_renames_legacy_values(app):
    from sqlalchemy import text
    from app.db import get_sessionmaker, upgrade_data
    sm = get_sessionmaker()
    with sm() as s:
        s.execute(text("INSERT INTO users (id, email, password_hash, role, active, email_verified, created_at) "
                       "VALUES ('u1', 'old@example.com', 'x', 'analyst', 1, 1, CURRENT_TIMESTAMP)"))
        s.execute(text("INSERT INTO documents (id, filename, kind, mime, size, sha256, storage_key, status, needs_review, "
                       "review_reasons, page_sizes, detector_runs, created_at) VALUES ('d1','f','png','image/png',1,'0','k',"
                       "'completed',1,'[]','[]','[]',CURRENT_TIMESTAMP)"))
        s.execute(text("INSERT INTO reviews (document_id, decision, notes, reviewer, created_at) VALUES "
                       "('d1','authentic','','r',CURRENT_TIMESTAMP), ('d1','tampered','','r',CURRENT_TIMESTAMP)"))
        s.commit()
    upgrade_data(sm.kw["bind"])
    upgrade_data(sm.kw["bind"])  # idempotent
    with sm() as s:
        assert s.scalar(text("SELECT role FROM users WHERE id='u1'")) == "user"
        assert sorted(s.scalars(text("SELECT decision FROM reviews WHERE document_id='d1'"))) == ["accepted", "rejected"]

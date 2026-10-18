import re

import pytest
from fastapi.testclient import TestClient

from test_api import ADMIN, CSRF, login, make_user  # noqa: F401  (fixtures re-exported below)
from test_api import admin, app  # noqa: F401

PW = "signup-password-1"


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    from app import auth
    monkeypatch.setattr(auth, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


def code_of(outbox) -> str:
    return re.search(r"\b(\d{6})\b", outbox[-1][2]).group(1)


def signup(c, email="new@example.com", pw=PW):
    return c.post("/api/auth/signup", json={"email": email, "password": pw})


def test_signup_verify_login(app, outbox):
    c = TestClient(app, headers=CSRF)
    assert signup(c, "New@Example.com").status_code == 202
    assert outbox[-1][0] == "new@example.com"
    # unverified account cannot log in
    r = c.post("/api/auth/login", json={"email": "new@example.com", "password": PW})
    assert r.status_code == 403 and r.json()["detail"] == "email_not_verified"
    wrong = f"{(int(code_of(outbox)) + 1) % 10**6:06d}"
    assert c.post("/api/auth/verify", json={"email": "new@example.com", "code": wrong}).status_code == 400
    r = c.post("/api/auth/verify", json={"email": "new@example.com", "code": code_of(outbox)})
    assert r.status_code == 200 and r.json()["role"] == "analyst"
    assert c.get("/api/auth/me").status_code == 200  # verify logs the user in
    # code is single-use; verified email cannot sign up again
    assert c.post("/api/auth/verify", json={"email": "new@example.com", "code": code_of(outbox)}).status_code == 400
    assert signup(c).status_code == 409
    assert TestClient(app).post("/api/auth/login", json={"email": "new@example.com", "password": PW}).status_code == 200


def test_otp_attempt_limit(app, outbox):
    c = TestClient(app)
    signup(c)
    good = code_of(outbox)
    wrong = f"{(int(good) + 1) % 10**6:06d}"
    for _ in range(5):
        assert c.post("/api/auth/verify", json={"email": "new@example.com", "code": wrong}).status_code == 400
    assert c.post("/api/auth/verify", json={"email": "new@example.com", "code": good}).status_code == 400  # burned


def test_otp_expiry(app, outbox, monkeypatch):
    from app import config
    monkeypatch.setattr(config.get_settings(), "otp_ttl_minutes", -1)
    c = TestClient(app)
    signup(c)
    assert c.post("/api/auth/verify", json={"email": "new@example.com", "code": code_of(outbox)}).status_code == 400


def test_resend_cooldown_and_no_enumeration(app, outbox, monkeypatch):
    c = TestClient(app)
    signup(c)
    assert c.post("/api/auth/resend", json={"email": "new@example.com"}).status_code == 202
    assert len(outbox) == 1  # within cooldown: no second email
    from app import config
    monkeypatch.setattr(config.get_settings(), "otp_resend_seconds", 0)
    c.post("/api/auth/resend", json={"email": "new@example.com"})
    assert len(outbox) == 2
    first_is_dead = c.post("/api/auth/verify", json={"email": "new@example.com", "code": re.search(r"\b(\d{6})\b", outbox[0][2]).group(1)})
    assert first_is_dead.status_code == 400 or outbox[0][2] == outbox[1][2]  # only newest code valid
    r = c.post("/api/auth/resend", json={"email": "nobody@example.com"})
    assert r.status_code == 202 and len(outbox) == 2  # same response, nothing sent


def test_signup_validation_and_mail_failure(app, monkeypatch):
    c = TestClient(app)
    assert signup(c, "not-an-email").status_code == 422
    assert signup(c, pw="short").status_code == 422
    from app import auth
    from app.mailer import MailError

    def boom(*a):
        raise MailError("down")
    monkeypatch.setattr(auth, "send_email", boom)
    assert signup(c).status_code == 502


def test_signup_disabled(app, monkeypatch):
    from app import config
    monkeypatch.setattr(config.get_settings(), "allow_signup", False)
    assert signup(TestClient(app)).status_code == 403


def test_console_mailer_when_smtp_unset(caplog):
    from app.mailer import send_email
    with caplog.at_level("WARNING"):
        send_email("x@example.com", "subj", "code 123456")
    assert "123456" in caplog.text

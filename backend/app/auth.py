"""Cookie-session authentication and role-based access (ADR-009)."""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import AuthSession, Document, OtpCode, User, get_db, get_sessionmaker
from .mailer import MailError, send_email

log = logging.getLogger(__name__)

COOKIE = "veritas_session"
CSRF_HEADER = "X-Requested-With"
ROLES = ("analyst", "reviewer", "admin")
Role = Literal["analyst", "reviewer", "admin"]

# --- passwords (stdlib scrypt) ---------------------------------------------------------------
_N, _R, _P = 2**14, 8, 1


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${dk.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, dk = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=len(dk) // 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(got.hex(), dk)


_DUMMY_HASH = hash_password(secrets.token_hex(8))  # equalise timing for unknown emails

# --- login throttling (per email, in-process; fine for the single-process MVP) ---------------
_MAX_FAILS, _WINDOW = 5, 15 * 60
_fails: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def _throttled(key: str) -> bool:
    with _lock:
        q = _fails[key]
        while q and q[0] < time.monotonic() - _WINDOW:
            q.popleft()
        return len(q) >= _MAX_FAILS


def _record_fail(key: str) -> None:
    with _lock:
        _fails[key].append(time.monotonic())


def reset_throttle() -> None:
    with _lock:
        _fails.clear()


# --- sessions ---------------------------------------------------------------------------------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # SQLite returns naive datetimes


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Not authenticated")
    sess = db.get(AuthSession, _hash_token(token))
    if sess is None or _aware(sess.expires_at) < datetime.now(timezone.utc) or not sess.user.active:
        raise HTTPException(401, "Session expired")
    if request.method not in ("GET", "HEAD", "OPTIONS") and not request.headers.get(CSRF_HEADER):
        raise HTTPException(403, f"Missing {CSRF_HEADER} header")
    return sess.user


def require(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient role")
        return user
    return dep


def can_see(user: User, doc: Document) -> bool:
    """Owners see their documents; reviewers/admins additionally see documents routed for human review."""
    return doc.owner_id == user.id or (user.role in ("reviewer", "admin") and doc.needs_review)


def bootstrap_admin() -> None:
    s = get_settings()
    if not (s.bootstrap_admin_email and s.bootstrap_admin_password):
        return
    with get_sessionmaker()() as db:
        if db.scalar(select(func.count()).select_from(User)) == 0:
            db.add(User(email=s.bootstrap_admin_email.lower(), password_hash=hash_password(s.bootstrap_admin_password),
                        role="admin", email_verified=True))
            db.commit()


# --- API --------------------------------------------------------------------------------------
router = APIRouter(prefix="/api")


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    active: bool
    created_at: datetime


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=256)


def _check_email(v: str) -> str:
    v = v.strip().lower()
    if "@" not in v or len(v) < 3:
        raise ValueError("invalid email")
    return v


class UserCreate(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=10, max_length=256)
    role: Role = "analyst"
    _email = field_validator("email")(_check_email)


class UserUpdate(BaseModel):
    role: Role | None = None
    active: bool | None = None
    password: str | None = Field(None, min_length=10, max_length=256)


@router.post("/auth/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if _throttled(email):
        raise HTTPException(429, "Too many failed attempts; try again later")
    user = db.scalar(select(User).where(User.email == email))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not (user and ok and user.active):
        _record_fail(email)
        raise HTTPException(401, "Invalid email or password")
    if not user.email_verified:  # password was correct, so revealing this is safe
        raise HTTPException(403, "email_not_verified")
    _start_session(db, user, response)
    return user


def _start_session(db: Session, user: User, response: Response) -> None:
    s = get_settings()
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.execute(delete(AuthSession).where(AuthSession.expires_at < now))  # opportunistic cleanup
    db.add(AuthSession(token_hash=_hash_token(token), user_id=user.id, expires_at=now + timedelta(hours=s.session_hours)))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=s.session_hours * 3600, httponly=True, samesite="strict",
                        secure=s.cookie_secure, path="/api")


# --- sign-up with emailed one-time code ------------------------------------------------------
_secret: bytes | None = None


def _otp_key() -> bytes:
    global _secret
    if _secret is None:
        k = get_settings().secret_key
        if not k:
            log.warning("VERITAS_SECRET_KEY not set; using a random key (pending OTP codes are lost on restart)")
            k = secrets.token_hex(32)
        _secret = k.encode()
    return _secret


def _otp_hash(user_id: str, code: str) -> str:
    return hmac.new(_otp_key(), f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


def _issue_otp(db: Session, user: User) -> None:
    s = get_settings()
    now = datetime.now(timezone.utc)
    last = db.scalar(select(OtpCode).where(OtpCode.user_id == user.id).order_by(OtpCode.created_at.desc()))
    if last and (now - _aware(last.created_at)).total_seconds() < s.otp_resend_seconds:
        return  # cooldown: keep the existing code (prevents mail bombing)
    db.execute(delete(OtpCode).where(OtpCode.user_id == user.id))  # only the newest code is valid
    code = f"{secrets.randbelow(10**6):06d}"
    db.add(OtpCode(user_id=user.id, code_hash=_otp_hash(user.id, code),
                   expires_at=now + timedelta(minutes=s.otp_ttl_minutes)))
    db.commit()
    try:
        send_email(user.email, f"Your Veritas verification code: {code}",
                   f"Your Veritas verification code is {code}\n\nIt expires in {s.otp_ttl_minutes} minutes. "
                   "If you did not sign up, ignore this email.")
    except MailError as e:
        db.execute(delete(OtpCode).where(OtpCode.user_id == user.id))  # allow an immediate retry
        db.commit()
        raise HTTPException(502, "Could not send verification email; try again later") from e


class SignupIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=10, max_length=256)
    _email = field_validator("email")(_check_email)


class VerifyIn(BaseModel):
    email: str = Field(max_length=254)
    code: str = Field(pattern=r"^\d{6}$")


class EmailIn(BaseModel):
    email: str = Field(max_length=254)


@router.post("/auth/signup", status_code=202)
def signup(body: SignupIn, db: Session = Depends(get_db)):
    if not get_settings().allow_signup:
        raise HTTPException(403, "Sign-up is disabled")
    user = db.scalar(select(User).where(User.email == body.email))
    if user and user.email_verified:
        raise HTTPException(409, "Email already registered")
    if user is None:
        user = User(email=body.email, password_hash=hash_password(body.password), role="analyst")
        db.add(user)
    else:  # unverified re-sign-up: new password; the emailed code still proves mailbox ownership
        user.password_hash = hash_password(body.password)
    db.commit()
    _issue_otp(db, user)
    return {"status": "verification_required", "email": user.email}


@router.post("/auth/verify", response_model=UserOut)
def verify(body: VerifyIn, response: Response, db: Session = Depends(get_db)):
    s = get_settings()
    bad = HTTPException(400, "Invalid or expired code")
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user is None or user.email_verified or not user.active:
        raise bad
    otp = db.scalar(select(OtpCode).where(OtpCode.user_id == user.id, OtpCode.consumed.is_(False)))
    if otp is None or _aware(otp.expires_at) < datetime.now(timezone.utc) or otp.attempts >= s.otp_max_attempts:
        raise bad
    if not hmac.compare_digest(otp.code_hash, _otp_hash(user.id, body.code)):
        otp.attempts += 1
        db.commit()
        raise bad
    otp.consumed = True
    user.email_verified = True
    db.commit()
    _start_session(db, user, response)
    return user


@router.post("/auth/resend", status_code=202)
def resend(body: EmailIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if user and not user.email_verified and user.active:
        _issue_otp(db, user)
    return {"status": "sent_if_pending"}  # same answer either way: no account enumeration


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, _: User = Depends(current_user), db: Session = Depends(get_db)):
    db.execute(delete(AuthSession).where(AuthSession.token_hash == _hash_token(request.cookies[COOKIE])))
    db.commit()
    response.delete_cookie(COOKIE, path="/api")


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(require("admin")), db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.created_at)).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, _: User = Depends(require("admin")), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(409, "Email already registered")
    u = User(email=body.email, password_hash=hash_password(body.password), role=body.role, email_verified=True)
    db.add(u)
    db.commit()
    return u


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, body: UserUpdate, admin: User = Depends(require("admin")), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(404, "User not found")
    if u.id == admin.id and (body.active is False or (body.role and body.role != "admin")):
        raise HTTPException(400, "Admins cannot demote or deactivate themselves")
    if body.role is not None:
        u.role = body.role
    if body.active is not None:
        u.active = body.active
    if body.password is not None:
        u.password_hash = hash_password(body.password)
    if body.active is False or body.password is not None:
        db.execute(delete(AuthSession).where(AuthSession.user_id == u.id))  # revoke sessions
    db.commit()
    return u


import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from auth_service.app.models import User, AuthSession


SESSION_LIFETIME_DAYS = 7


def get_or_create_user(
    db: Session,
    tpu_data: dict,
) -> User:
    tpu_subject = str(tpu_data["user_id"])

    person = tpu_data.get("lichnost") or {}

    first_name = person.get("imya") or ""
    last_name = person.get("familiya") or ""

    full_name = f"{first_name} {last_name}".strip()
    if not full_name:
        full_name = tpu_subject

    email = tpu_data.get("email")

    user = db.scalar(
        select(User).where(
            User.tpu_subject == tpu_subject
        )
    )

    if user is None:
        user = User(
            tpu_subject=tpu_subject,
            name=full_name,
            email=email,
        )
        db.add(user)
    else:
        user.name = full_name
        user.email = email

    db.commit()
    db.refresh(user)

    return user


def hash_session_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_session(
    db: Session,
    user: User,
) -> str:
    token = secrets.token_urlsafe(32)

    auth_session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=SESSION_LIFETIME_DAYS),
    )

    db.add(auth_session)
    db.commit()

    return token


def get_user_by_session(
    db: Session,
    token: str,
) -> User | None:
    if not token:
        return None

    token_hash = hash_session_token(token)

    now = datetime.now(timezone.utc)

    return db.scalar(
        select(User)
        .join(
            AuthSession,
            AuthSession.user_id == User.id,
        )
        .where(
            AuthSession.token_hash == token_hash,
            AuthSession.expires_at > now,
        )
    )


def delete_session(
    db: Session,
    token: str,
) -> None:
    if not token:
        return

    auth_session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash
            == hash_session_token(token)
        )
    )

    if auth_session is not None:
        db.delete(auth_session)
        db.commit()

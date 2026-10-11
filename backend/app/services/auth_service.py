import secrets
import time

from app.schemas.auth import User


sessions: dict[str, tuple[User, float]] = {}


def create_session(profile: dict, expires_in: int) -> str:
    user = User(
        id=profile["user_id"],
        email=profile["email"],
        first_name=profile["first_name"],
        last_name=profile["last_name"],
    )
    session_id = secrets.token_urlsafe(32)
    expires_at = time.time() + min(expires_in, 86400)
    sessions[session_id] = (user, expires_at)
    return session_id


def get_user(session_id: str) -> User | None:
    session = sessions.get(session_id)
    if session is None:
        return None

    user, expires_at = session
    if expires_at <= time.time():
        sessions.pop(session_id, None)
        return None

    return user


def logout(session_id: str) -> None:
    sessions.pop(session_id, None)

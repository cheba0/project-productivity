import secrets
import time
from threading import Lock

from app.schemas.auth import User


users: dict[int, User] = {}

# Токены ТПУ хранятся только на сервере.
sessions: dict[str, dict] = {}

storage_lock = Lock()


def create_tpu_session(
    profile: dict,
    tokens: dict,
) -> str:
    try:
        user = User(
            id=int(profile["user_id"]),
            email=profile["email"],
            first_name=profile["first_name"],
            last_name=profile["last_name"],
        )
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            "Неожиданный формат профиля ТПУ"
        ) from None

    try:
        access_token = tokens["access_token"]
        lifetime = int(tokens["expires_in"])

        if not isinstance(access_token, str) or not access_token:
            raise ValueError

        if lifetime <= 0:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            "Неожиданный формат токена ТПУ"
        ) from None

    session_id = secrets.token_urlsafe(32)

    with storage_lock:
        users[user.id] = user

        sessions[session_id] = {
            "user_id": user.id,
            "access_token": access_token,
            "refresh_token": tokens.get("refresh_token"),
            "expires_at": time.time() + min(lifetime, 86400),
        }

    return session_id


def get_user_by_session(session_id: str) -> User | None:
    with storage_lock:
        session = sessions.get(session_id)

        if session is None:
            return None

        if session["expires_at"] <= time.time():
            sessions.pop(session_id, None)
            return None

        return users.get(session["user_id"])


def logout(session_id: str) -> None:
    with storage_lock:
        sessions.pop(session_id, None)
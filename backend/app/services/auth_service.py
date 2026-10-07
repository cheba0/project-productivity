import secrets

from app.schemas.auth import User


# Временное хранилище пользователей
users: dict[int, User] = {}

# Временное хранилище сессий
sessions: dict[str, int] = {}


def get_mock_tpu_user() -> dict:
    """
    Имитирует ответ API ТПУ.
    Потом эту функцию заменим реальным запросом.
    """
    return {
        "user_id": 163098,
        "email": "user@tpu.ru",
        "lichnost": {
            "familiya": "Иванов",
            "imya": "Иван",
        },
    }


def register_user() -> tuple[User, str]:
    tpu_user = get_mock_tpu_user()

    user_id = tpu_user["user_id"]

    if user_id in users:
        raise ValueError("User already registered")

    person = tpu_user["lichnost"]

    user = User(
        id=user_id,
        email=tpu_user["email"],
        first_name=person["imya"],
        last_name=person["familiya"],
    )

    users[user_id] = user

    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = user_id

    return user, session_id


def login_user() -> tuple[User, str]:
    tpu_user = get_mock_tpu_user()

    user_id = tpu_user["user_id"]

    if user_id not in users:
        raise ValueError("User is not registered")

    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = user_id

    return users[user_id], session_id


def get_user_by_session(session_id: str) -> User | None:
    user_id = sessions.get(session_id)

    if user_id is None:
        return None

    return users.get(user_id)


def logout(session_id: str) -> None:
    sessions.pop(session_id, None)
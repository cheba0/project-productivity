from app.schemas.auth import User


users = {
    1: User(
        id=1,
        email="student@example.com",
        first_name="Иван",
        last_name="Иванов",
    )
}


sessions: dict[str, int] = {}


def login() -> str:
    session_id = "test-session-123"

    sessions[session_id] = 1

    return session_id


def get_user_by_session(session_id: str) -> User | None:
    user_id = sessions.get(session_id)

    if user_id is None:
        return None

    return users.get(user_id)


def logout(session_id: str) -> None:
    sessions.pop(session_id, None)
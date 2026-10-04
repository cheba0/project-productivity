from fastapi import APIRouter, Response, Cookie, HTTPException

from app.services.auth_service import (
    login,
    get_user_by_session,
    logout,
)
from app.schemas.auth import User

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/login")
def auth_login(response: Response):
    session_id = login()

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
    )

    return {
        "message": "Successfully logged in"
    }
    
@router.get("/me", response_model=User)
def auth_me(session_id: str | None = Cookie(default=None)):
    if session_id is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    user = get_user_by_session(session_id)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid session",
        )

    return user

@router.post("/logout")
def auth_logout(
    response: Response,
    session_id: str | None = Cookie(default=None),
):
    if session_id is not None:
        logout(session_id)

    response.delete_cookie("session_id")

    return {
        "message": "Successfully logged out"
    }
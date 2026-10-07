from fastapi import APIRouter, Response, Cookie, HTTPException

from app.services.auth_service import (
    register_user,
    login_user,
    get_user_by_session,
    logout,
)
from app.schemas.auth import User


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post("/register")
def auth_register(response: Response):
    try:
        user, session_id = register_user()
    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        )

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
    )

    return {
        "message": "Successfully registered",
        "user": user,
    }


@router.post("/login")
def auth_login(response: Response):
    try:
        user, session_id = login_user()
    except ValueError as error:
        raise HTTPException(
            status_code=401,
            detail=str(error),
        )

    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
    )

    return {
        "message": "Successfully logged in",
        "user": user,
    }


@router.get("/me", response_model=User)
def auth_me(
    session_id: str | None = Cookie(default=None),
):
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
import secrets

from fastapi import APIRouter, Cookie, HTTPException, Response
from fastapi.responses import RedirectResponse

from app.schemas.auth import User
from app.services.auth_service import create_session, get_user, logout
from app.services.tpu_service import (
    TPUError,
    exchange_code_for_token,
    get_authorization_url,
    get_tpu_user,
)


router = APIRouter(prefix="/auth", tags=["Auth"])

FRONTEND_URL = "http://localhost:5173"
OAUTH_COOKIE_PATH = "/auth/tpu"


def redirect_to_frontend(error: bool = False) -> RedirectResponse:
    url = f"{FRONTEND_URL}/?auth_error=tpu_login_failed" if error else FRONTEND_URL
    response = RedirectResponse(url, status_code=303)
    response.delete_cookie("oauth_state", path=OAUTH_COOKIE_PATH)
    response.delete_cookie("code_verifier", path=OAUTH_COOKIE_PATH)
    return response


@router.get("/tpu/login")
def tpu_login():
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)

    try:
        authorization_url = get_authorization_url(state, code_verifier)
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from None

    response = RedirectResponse(authorization_url, status_code=302)
    cookie_options = {
        "max_age": 600,
        "path": OAUTH_COOKIE_PATH,
        "httponly": True,
        "samesite": "lax",
    }
    response.set_cookie("oauth_state", state, **cookie_options)
    response.set_cookie("code_verifier", code_verifier, **cookie_options)
    return response


@router.get("/tpu/callback")
def tpu_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None),
    code_verifier: str | None = Cookie(default=None),
):
    valid_state = (
        state
        and oauth_state
        and secrets.compare_digest(state, oauth_state)
    )
    if error or not code or not code_verifier or not valid_state:
        return redirect_to_frontend(error=True)

    try:
        tokens = exchange_code_for_token(code, code_verifier)
        profile = get_tpu_user(tokens["access_token"])
        session_id = create_session(profile, int(tokens["expires_in"]))
    except (TPUError, KeyError, TypeError, ValueError):
        return redirect_to_frontend(error=True)

    response = redirect_to_frontend()
    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/me", response_model=User)
def auth_me(session_id: str | None = Cookie(default=None)):
    user = get_user(session_id) if session_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("/logout")
def auth_logout(
    response: Response,
    session_id: str | None = Cookie(default=None),
):
    if session_id:
        logout(session_id)
    response.delete_cookie("session_id")
    return {"message": "Successfully logged out"}

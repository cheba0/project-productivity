# import secrets

# from fastapi import APIRouter, Response, Cookie, HTTPException
# from fastapi.responses import RedirectResponse

# from app.services.auth_service import (
#     register_user,
#     login_user,
#     get_user_by_session,
#     logout,
# )
# from app.services.tpu_service import get_authorization_url
# from app.schemas.auth import User


# router = APIRouter(
#     prefix="/auth",
#     tags=["Auth"],
# )


# @router.post("/register")
# def auth_register(response: Response):
#     try:
#         user, session_id = register_user()
#     except ValueError as error:
#         raise HTTPException(
#             status_code=409,
#             detail=str(error),
#         )

#     response.set_cookie(
#         key="session_id",
#         value=session_id,
#         httponly=True,
#         samesite="lax",
#     )

#     return {
#         "message": "Successfully registered",
#         "user": user,
#     }


# @router.post("/login")
# def auth_login(response: Response):
#     try:
#         user, session_id = login_user()
#     except ValueError as error:
#         raise HTTPException(
#             status_code=401,
#             detail=str(error),
#         )

#     response.set_cookie(
#         key="session_id",
#         value=session_id,
#         httponly=True,
#         samesite="lax",
#     )

#     return {
#         "message": "Successfully logged in",
#         "user": user,
#     }

# @router.get("/tpu/login")
# def tpu_login():
#     state = secrets.token_urlsafe(32)

#     try:
#         authorization_url = get_authorization_url(state)

#     except ValueError as error:
#         raise HTTPException(
#             status_code=503,
#             detail=str(error),
#         )

#     response = RedirectResponse(
#         url=authorization_url,
#         status_code=302,
#     )

#     response.set_cookie(
#         key="oauth_state",
#         value=state,
#         httponly=True,
#         samesite="lax",
#     )

#     return response

# @router.get("/me", response_model=User)
# def auth_me(
#     session_id: str | None = Cookie(default=None),
# ):
#     if session_id is None:
#         raise HTTPException(
#             status_code=401,
#             detail="Not authenticated",
#         )

#     user = get_user_by_session(session_id)

#     if user is None:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid session",
#         )

#     return user


# @router.post("/logout")
# def auth_logout(
#     response: Response,
#     session_id: str | None = Cookie(default=None),
# ):
#     if session_id is not None:
#         logout(session_id)

#     response.delete_cookie("session_id")

#     return {
#         "message": "Successfully logged out"
#     }

import secrets
import time
from threading import Lock

from fastapi import APIRouter, Cookie, HTTPException, Response
from fastapi.responses import RedirectResponse

from app.schemas.auth import User
from app.services.auth_service import (
    create_tpu_session,
    get_user_by_session,
    logout,
)
from app.services.tpu_service import (
    TPUError,
    exchange_code_for_token,
    get_authorization_url,
    get_tpu_user,
)


router = APIRouter(prefix="/auth", tags=["Auth"])

FRONTEND_URL = "http://localhost:5173"

# Для HTTP на localhost — False.
# При публикации на HTTPS обязательно использовать True.
COOKIE_SECURE = False

OAUTH_TTL = 600

pending_oauth: dict[str, dict] = {}
oauth_lock = Lock()


def clear_oauth_cookie(response: Response) -> None:
    response.delete_cookie(
        "oauth_state",
        path="/auth/tpu",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )


def failed_login() -> RedirectResponse:
    response = RedirectResponse(
        f"{FRONTEND_URL}/?auth_error=tpu_login_failed",
        status_code=303,
    )
    clear_oauth_cookie(response)
    return response


@router.get("/tpu/login")
def tpu_login():
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)

    try:
        authorization_url = get_authorization_url(
            state,
            code_verifier,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from None

    now = time.time()

    with oauth_lock:
        # Удаляем просроченные попытки входа.
        expired = [
            key
            for key, value in pending_oauth.items()
            if value["expires_at"] <= now
        ]

        for key in expired:
            pending_oauth.pop(key, None)

        pending_oauth[state] = {
            "code_verifier": code_verifier,
            "expires_at": now + OAUTH_TTL,
        }

    response = RedirectResponse(
        authorization_url,
        status_code=302,
    )

    response.set_cookie(
        key="oauth_state",
        value=state,
        max_age=OAUTH_TTL,
        path="/auth/tpu",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )

    response.headers["Cache-Control"] = "no-store"

    return response


@router.get("/tpu/callback")
def tpu_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str | None = Cookie(default=None),
    ):
    # Сначала проверяем связь callback с браузером,
    # который начал вход.
    if not state or not oauth_state:
        print("OAuth: отсутствует state или cookie oauth_state")
        return failed_login()

    if not secrets.compare_digest(state, oauth_state):
        print("OAuth: state не совпадает с cookie")
        return failed_login()

    # pop делает попытку входа одноразовой.
    with oauth_lock:
        attempt = pending_oauth.pop(state, None)

    if attempt is None:
        print("OAuth: попытка не найдена или уже использована")
        return failed_login()

    if attempt["expires_at"] <= time.time():
        print("OAuth: срок попытки истёк")
        return failed_login()

    if error:
        # Показываем только известные коды, без описания ошибки.
        known_errors = {
            "invalid_request",
            "unauthorized_client",
            "access_denied",
            "unsupported_response_type",
            "invalid_scope",
            "server_error",
            "temporarily_unavailable",
            "invalid_grant",
        }
        safe_error = error if error in known_errors else "other"
        print(f"OAuth: ТПУ вернул ошибку {safe_error}")
        return failed_login()

    if not code:
        print("OAuth: ТПУ не передал code")
        return failed_login()
    
    try:
        tokens = exchange_code_for_token(
            code,
            attempt["code_verifier"],
        )

        profile = get_tpu_user(tokens["access_token"])

        session_id = create_tpu_session(profile, tokens)
    except (TPUError, ValueError) as exc:
        print(f"OAuth: {type(exc).__name__}: {exc}")
        return failed_login()

    # Заменяем старую сессию этого браузера.
    # Cookie старой сессии обрабатывается ниже отдельно
    # через параметр маршрута при необходимости.

    response = RedirectResponse(
        FRONTEND_URL,
        status_code=303,
    )

    response.set_cookie(
        key="session_id",
        value=session_id,
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        # Cookie сессионная: сервер проверяет срок сам.
    )

    clear_oauth_cookie(response)
    response.headers["Cache-Control"] = "no-store"

    return response


@router.get("/me", response_model=User)
def auth_me(
    session_id: str | None = Cookie(default=None),
    ):
    user = (
        get_user_by_session(session_id)
        if session_id
        else None
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    return user


@router.post("/logout")
def auth_logout(
    response: Response,
    session_id: str | None = Cookie(default=None),
):
    if session_id:
        logout(session_id)

    response.delete_cookie(
        key="session_id",
        path="/",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="lax",
    )

    return {"message": "Successfully logged out"}
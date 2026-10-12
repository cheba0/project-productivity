
import secrets
from urllib.parse import urlencode

import httpx

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from auth_service.app.config import settings
from auth_service.app.database import get_db
from auth_service.app.services.tpu_oauth import (
    get_authorization_url,
    exchange_code_for_token,
    get_tpu_user,
)
from auth_service.app.services.session_service import (
    get_or_create_user,
    create_session,
    get_user_by_session,
    delete_session,
)


app = FastAPI(title="Auth Service")

FRONTEND_URL = "http://localhost:5173"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth_service"}


@app.get("/auth/tpu/login")
def tpu_login():
    state = secrets.token_urlsafe(32)

    response = RedirectResponse(
        url=get_authorization_url(state),
        status_code=302,
    )

    response.set_cookie(
        key="tpu_oauth_state",
        value=state,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600,
        path="/auth/tpu",
    )

    return response


@app.get("/auth/tpu/callback")
async def tpu_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    state = request.query_params.get("state")
    expected_state = request.cookies.get("tpu_oauth_state")
    code = request.query_params.get("code")

    if (
        not state
        or not expected_state
        or not secrets.compare_digest(state, expected_state)
        or not code
    ):
        response = RedirectResponse(
            f"{FRONTEND_URL}/?auth_error=invalid_state",
            status_code=302,
        )
        response.delete_cookie(
            "tpu_oauth_state",
            path="/auth/tpu",
        )
        return response

    try:
        token_data = await exchange_code_for_token(code)
        tpu_user = await get_tpu_user(
            token_data["access_token"]
        )

        user = get_or_create_user(db, tpu_user)
        session_token = create_session(db, user)

    except (httpx.HTTPError, ValueError, KeyError):
        response = RedirectResponse(
            f"{FRONTEND_URL}/?auth_error=tpu_failed",
            status_code=302,
        )
        response.delete_cookie(
            "tpu_oauth_state",
            path="/auth/tpu",
        )
        return response

    response = RedirectResponse(
        FRONTEND_URL,
        status_code=302,
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )

    response.delete_cookie(
        "tpu_oauth_state",
        path="/auth/tpu",
    )

    return response


@app.get("/auth/me")
def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get("session_token")

    user = get_user_by_session(db, token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    parts = user.name.split(" ", 1)

    return {
        "id": str(user.id),
        "first_name": parts[0],
        "last_name": parts[1] if len(parts) > 1 else "",
        "email": user.email,
    }


@app.post("/auth/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get("session_token")

    if token:
        delete_session(db, token)

    response = Response(status_code=204)

    response.delete_cookie(
        "session_token",
        path="/",
    )

    return response

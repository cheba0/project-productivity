
import os
import secrets

import httpx
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from urllib.parse import urlparse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

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

from auth_service.app.projects_router import router as projects_router
app.include_router(projects_router)
from auth_service.app.live_router import router as live_router
app.include_router(live_router)

FRONTEND_URL = os.getenv("TPU_FRONTEND_URL", "https://tpu-metrics.duckdns.org").rstrip("/")
OAUTH_COOKIE_PATH = "/auth/tpu"


def cookie_secure() -> bool:
    """HTTPS browser cookies by default; HTTP only in explicitly opted-in local dev."""
    value = os.getenv("TPU_COOKIE_SECURE", "true").strip().lower()
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        if urlparse(FRONTEND_URL).hostname not in {"localhost", "127.0.0.1"}:
            raise RuntimeError(
                "Insecure auth cookies are allowed only with a localhost TPU_FRONTEND_URL"
            )
        return False
    raise RuntimeError("TPU_COOKIE_SECURE must be true or false")


frontend = urlparse(FRONTEND_URL)
if (
    frontend.scheme not in {"https", "http"}
    or not frontend.hostname
    or frontend.username or frontend.password
    or frontend.path not in ("", "/")
    or frontend.query or frontend.fragment
):
    raise RuntimeError("TPU_FRONTEND_URL must be a plain HTTP(S) origin")
if frontend.scheme == "http" and frontend.hostname not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("Non-local TPU_FRONTEND_URL must use HTTPS")
if frontend.scheme == "http" and cookie_secure():
    raise RuntimeError("For local HTTP frontend set TPU_COOKIE_SECURE=false")



UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def trusted_browser_origin(request: Request) -> bool:
    """Accept only our exact browser origin (or exact Referer origin fallback)."""
    origin = request.headers.get("origin")
    if origin is not None:
        return origin == FRONTEND_URL
    referer = request.headers.get("referer")
    if not referer:
        return False
    parsed = urlparse(referer)
    if parsed.username or parsed.password:
        return False
    return f"{parsed.scheme}://{parsed.netloc}" == FRONTEND_URL


@app.middleware("http")
async def csrf_origin_guard(request: Request, call_next):
    """Block cookie-authenticated browser writes with missing/foreign origins.

    OAuth callback uses state+PKCE on GET; it is not a mutating browser API.
    Bearer-less requests are still validated by the normal auth dependency.
    """
    if (request.method in UNSAFE_METHODS
            and request.cookies.get("session_token")
            and not trusted_browser_origin(request)):
        return JSONResponse(
            status_code=403, content={"detail": "Untrusted request origin"}
        )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth_service"}


@app.get("/auth/tpu/login")
def tpu_login():
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)

    authorization_url = get_authorization_url(
        state,
        code_verifier,
    )

    response = RedirectResponse(
        authorization_url,
        status_code=302,
    )

    cookie_options = {
        "httponly": True,
        "secure": cookie_secure(),
        "samesite": "lax",
        "max_age": 600,
        "path": OAUTH_COOKIE_PATH,
    }

    response.set_cookie(
        "tpu_oauth_state",
        state,
        **cookie_options,
    )

    response.set_cookie(
        "tpu_code_verifier",
        code_verifier,
        **cookie_options,
    )

    return response


def redirect_to_frontend(
    error: str | None = None,
) -> RedirectResponse:
    url = (
        f"{FRONTEND_URL}/?auth_error={error}"
        if error
        else FRONTEND_URL
    )

    response = RedirectResponse(
        url,
        status_code=303,
    )

    response.delete_cookie(
        "tpu_oauth_state",
        path=OAUTH_COOKIE_PATH,
    )

    response.delete_cookie(
        "tpu_code_verifier",
        path=OAUTH_COOKIE_PATH,
    )

    return response


@app.get("/auth/tpu/callback")
async def tpu_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    state = request.query_params.get("state")
    code = request.query_params.get("code")
    error = request.query_params.get("error")

    expected_state = request.cookies.get("tpu_oauth_state")
    code_verifier = request.cookies.get("tpu_code_verifier")

    valid_state = bool(
        state
        and expected_state
        and secrets.compare_digest(
            state,
            expected_state,
        )
    )

    if (
        error
        or not code
        or not code_verifier
        or not valid_state
    ):
        return redirect_to_frontend("invalid_state")

    try:
        token_data = await exchange_code_for_token(
            code,
            code_verifier,
        )

        tpu_user = await get_tpu_user(
            token_data["access_token"]
        )

        user = get_or_create_user(
            db,
            tpu_user,
        )

        session_token = create_session(
            db,
            user,
        )

    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        TypeError,
    ):
        return redirect_to_frontend("tpu_failed")

    response = redirect_to_frontend()

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=cookie_secure(),
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )

    return response


@app.get("/auth/me")
def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get("session_token")

    user = get_user_by_session(
        db,
        token,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    parts = user.name.split(" ", 1)

    return {
        "id": str(user.id),
        "first_name": parts[0],
        "last_name": (
            parts[1]
            if len(parts) > 1
            else ""
        ),
        "email": user.email,
    }


@app.post("/auth/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get("session_token")

    if token:
        delete_session(
            db,
            token,
        )

    response = Response(status_code=204)

    response.delete_cookie(
        "session_token",
        path="/",
    )

    return response

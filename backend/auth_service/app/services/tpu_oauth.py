
import base64
import hashlib
from urllib.parse import urlencode

import httpx

from auth_service.app.config import settings


TPU_AUTHORIZE_URL = "https://oauth.tpu.ru/authorize"
TPU_TOKEN_URL = "https://oauth.tpu.ru/access_token"
TPU_USER_URL = "https://oauth.tpu.ru/user"


def get_authorization_url(
    state: str,
    code_verifier: str,
) -> str:
    digest = hashlib.sha256(
        code_verifier.encode("utf-8")
    ).digest()

    code_challenge = (
        base64.urlsafe_b64encode(digest)
        .rstrip(b"=")
        .decode("ascii")
    )

    params = {
        "client_id": settings.tpu_client_id,
        "redirect_uri": settings.tpu_redirect_uri,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    return f"{TPU_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_token(
    code: str,
    code_verifier: str,
) -> dict:
    data = {
        "client_id": settings.tpu_client_id,
        "client_secret": settings.tpu_client_secret,
        "redirect_uri": settings.tpu_redirect_uri,
        "code": code,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            TPU_TOKEN_URL,
            data=data,
        )
        response.raise_for_status()
        result = response.json()

    if not isinstance(result, dict) or not result.get("access_token"):
        raise ValueError("TPU did not return an access token")

    return result


async def get_tpu_user(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            TPU_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}"
            },
        )
        response.raise_for_status()
        result = response.json()

    if not isinstance(result, dict):
        raise ValueError("Invalid TPU user response")

    if not result.get("user_id"):
        raise ValueError("TPU user_id is missing")

    # Приводим ответ старого API к формату нового Auth Service
    if not result.get("lichnost"):
        result["lichnost"] = {
            "imya": result.get("first_name") or "",
            "familiya": result.get("last_name") or "",
        }

    return result

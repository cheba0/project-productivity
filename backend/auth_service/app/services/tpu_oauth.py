
from urllib.parse import urlencode

import httpx

from auth_service.app.config import settings


TPU_AUTHORIZE_URL = "https://oauth.tpu.ru/authorize"
TPU_TOKEN_URL = "https://oauth.tpu.ru/access_token"
TPU_USER_URL = "https://api.tpu.ru/v2/auth/user"


def get_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.tpu_client_id,
        "redirect_uri": settings.tpu_redirect_uri,
        "response_type": "code",
        "state": state,
    }

    return f"{TPU_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    data = {
        "client_id": settings.tpu_client_id,
        "client_secret": settings.tpu_client_secret,
        "redirect_uri": settings.tpu_redirect_uri,
        "code": code,
        "grant_type": "authorization_code",
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
    params = {
        "apiKey": settings.tpu_api_key,
        "access_token": access_token,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            TPU_USER_URL,
            params=params,
        )

        response.raise_for_status()
        result = response.json()

    if not isinstance(result, dict) or not result.get("user_id"):
        raise ValueError("TPU did not return a valid user")

    return result

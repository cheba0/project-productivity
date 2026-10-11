import base64
import hashlib
from urllib.parse import urlencode

import requests

from app.config import settings


TPU_AUTHORIZE_URL = "https://oauth.tpu.ru/authorize"
TPU_TOKEN_URL = "https://oauth.tpu.ru/access_token"
TPU_USER_URL = "https://oauth.tpu.ru/user"


class TPUError(Exception):
    pass


def get_authorization_url(state: str, code_verifier: str) -> str:
    if not all((
        settings.tpu_client_id,
        settings.tpu_client_secret,
        settings.tpu_redirect_uri,
    )):
        raise ValueError("TPU OAuth is not configured")

    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    params = {
        "client_id": settings.tpu_client_id,
        "redirect_uri": settings.tpu_redirect_uri,
        "response_type": "code",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{TPU_AUTHORIZE_URL}?{urlencode(params)}"


def request_json(method: str, url: str, **kwargs) -> dict:
    try:
        response = requests.request(method, url, timeout=15, **kwargs)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        raise TPUError("TPU request failed") from error


def exchange_code_for_token(code: str, code_verifier: str) -> dict:
    return request_json(
        "POST",
        TPU_TOKEN_URL,
        data={
            "client_id": settings.tpu_client_id,
            "client_secret": settings.tpu_client_secret,
            "redirect_uri": settings.tpu_redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        },
    )


def get_tpu_user(access_token: str) -> dict:
    return request_json(
        "GET",
        TPU_USER_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )

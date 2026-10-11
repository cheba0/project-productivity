import base64
import hashlib
from urllib.parse import urlencode

import requests

from app.config import settings


TPU_AUTHORIZE_URL = "https://oauth.tpu.ru/authorize"
TPU_TOKEN_URL = "https://oauth.tpu.ru/access_token"
TPU_USER_URL = "https://oauth.tpu.ru/user"


class TPUError(Exception):
    """Ошибка обращения к ТПУ."""


def check_configuration() -> None:
    required = {
        "TPU_CLIENT_ID": settings.tpu_client_id,
        "TPU_CLIENT_SECRET": settings.tpu_client_secret,
        "TPU_API_KEY": settings.tpu_api_key,
        "TPU_REDIRECT_URI": settings.tpu_redirect_uri,
    }

    missing = [name for name, value in required.items() if not value]

    if missing:
        raise ValueError(
            "Не заданы настройки: " + ", ".join(missing)
        )


def get_authorization_url(
    state: str,
    code_verifier: str,
) -> str:
    check_configuration()

    digest = hashlib.sha256(
        code_verifier.encode("ascii")
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


def read_json(
    response: requests.Response,
    stage: str,
) -> dict:
    if not response.ok:
        raise TPUError(
            f"{stage}: HTTP {response.status_code}"
        )

    try:
        data = response.json()
    except ValueError:
        content_type = response.headers.get(
            "Content-Type", "не указан"
        )
        raise TPUError(
            f"{stage}: ответ не JSON, Content-Type={content_type}"
        ) from None

    if not isinstance(data, dict):
        raise TPUError(f"{stage}: ожидался JSON-объект")

    if data.get("error"):
        raise TPUError(f"{stage}: ТПУ отклонил запрос")

    return data


def exchange_code_for_token(
    code: str,
    code_verifier: str,
) -> dict:
    try:
        response = requests.post(
            TPU_TOKEN_URL,
            data={
                "client_id": settings.tpu_client_id,
                "client_secret": settings.tpu_client_secret,
                "redirect_uri": settings.tpu_redirect_uri,
                "code": code,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
            timeout=15,
        )
    except requests.RequestException:
        raise TPUError("Не удалось связаться с ТПУ") from None

    data = read_json(response, "Обмен кода на токен")

    if not isinstance(data.get("access_token"), str):
        raise TPUError("ТПУ не вернул токен доступа")

    return data


def get_tpu_user(access_token: str) -> dict:
    try:
        response = requests.get(
            TPU_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=15,
        )
    except requests.RequestException:
        raise TPUError(
            "Не удалось получить профиль ТПУ"
        ) from None

    data = read_json(response, "Получение профиля")

    # Для диагностики выводим только названия полей.
    print("TPU profile fields:", list(data.keys()))

    return data

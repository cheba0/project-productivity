from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # TPU ключей нет
    tpu_client_id: str | None = None
    tpu_client_secret: str | None = None
    tpu_api_key: str | None = None
    tpu_redirect_uri: str | None = None

    
    redmine_url: str | None = None
    redmine_api_key: str | None = None

    gitlab_url: str = "https://gitlab.com"
    gitlab_access_token: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    tpu_client_id: str
    tpu_client_secret: str
    tpu_api_key: str
    tpu_redirect_uri: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
from pydantic import BaseModel, Field, HttpUrl


class MemberProfileUpdate(BaseModel):
    phone: str | None = Field(None, max_length=50)
    telegram: str | None = Field(None, max_length=100)
    gitlab_profile_url: HttpUrl | None = None
    redmine_profile_url: HttpUrl | None = None
    gitlab_email: str | None = Field(None, max_length=255)
    redmine_user_id: int | None = Field(None, ge=1)

"""API-контракты. Поля в snake_case; названия не нужно переводить в UI."""
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class ProjectListFilter(str, Enum):
    active = "active"         # Все неархивные и неприостановленные проекты.
    paused = "paused"         # «На паузе».
    archived = "archived"     # Архив.
    all = "all"


class ProjectWrite(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    showcase_url: HttpUrl | None = None
    gitlab_url: HttpUrl | None = None
    redmine_url: HttpUrl | None = None
    gitlab_token: str | None = Field(default=None, min_length=1, repr=False)
    redmine_token: str | None = Field(default=None, min_length=1, repr=False)
    sprint_weeks: int = Field(default=1, ge=1, le=12)
    active_after_days: int = Field(default=3, ge=0)
    delayed_after_days: int = Field(default=7, ge=1)
    start_date: date | None = None
    deadline: date | None = None

    @model_validator(mode="after")
    def verify_ranges(self):
        if self.delayed_after_days <= self.active_after_days:
            raise ValueError("delayed_after_days must exceed active_after_days")
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValueError("deadline cannot precede start_date")
        if self.gitlab_token and not self.gitlab_url:
            raise ValueError("gitlab_url is required with gitlab_token")
        if self.redmine_token and not self.redmine_url:
            raise ValueError("redmine_url is required with redmine_token")
        return self

    @field_validator("name")
    @classmethod
    def strip_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("name cannot be empty")
        return value


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    showcase_url: HttpUrl | None = None
    gitlab_url: HttpUrl | None = None
    redmine_url: HttpUrl | None = None
    gitlab_token: str | None = Field(default=None, min_length=1, repr=False)
    redmine_token: str | None = Field(default=None, min_length=1, repr=False)
    sprint_weeks: int | None = Field(default=None, ge=1, le=12)
    active_after_days: int | None = Field(default=None, ge=0)
    delayed_after_days: int | None = Field(default=None, ge=1)
    start_date: date | None = None
    deadline: date | None = None


class ProjectMemberCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if value.count("@") != 1 or "." not in value.split("@")[-1]:
            raise ValueError("invalid email")
        return value


class ProjectMemberView(BaseModel):
    id: UUID
    email: str
    name: str | None
    role: str
    is_pending: bool
    is_owner: bool


class ProjectView(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    showcase_url: str | None
    gitlab_url: str | None
    redmine_url: str | None
    gitlab_token_configured: bool
    redmine_token_configured: bool
    sprint_weeks: int
    active_after_days: int
    delayed_after_days: int
    start_date: date | None
    deadline: date | None
    is_paused: bool
    archived_at: datetime | None
    status: str                  # working/delayed/idle/unknown/paused/archived
    status_label: str
    progress_percent: int | None  # null — данных пока нет, не подменять 0%.
    tasks_done: int | None
    tasks_total: int | None
    gitlab_inactive_days: int | None
    redmine_inactive_days: int | None
    commits_per_day: list[int] | None
    members: list[ProjectMemberView]
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: list[ProjectView]
    counts: dict[str, int]       # active, paused, archived, all


class ConfirmDelete(BaseModel):
    name: str                    # Должно точно совпадать с названием проекта.

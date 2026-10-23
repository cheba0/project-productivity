"""Проекты интерфейса Productivity; не путать с analytics.project_mappings."""
from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, JSON, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from auth_service.app.database import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("sprint_weeks BETWEEN 1 AND 12", name="ck_projects_sprint_weeks"),
        CheckConstraint("active_after_days >= 0 AND delayed_after_days > active_after_days", name="ck_projects_activity_days"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, unique=True)
    owner_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    showcase_url: Mapped[str | None] = mapped_column(String(2048))
    gitlab_url: Mapped[str | None] = mapped_column(String(2048))
    redmine_url: Mapped[str | None] = mapped_column(String(2048))
    # Ни токены, ни их хэши не возвращаются в API. Только зашифрованные данные.
    gitlab_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    redmine_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    sprint_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active_after_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    delayed_after_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    start_date: Mapped[date | None] = mapped_column(Date)
    deadline: Mapped[date | None] = mapped_column(Date)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project", cascade="all, delete-orphan", passive_deletes=True)


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "email", name="uq_project_member_email"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    # pending — пользователь ещё не вошёл через TPU с данным email.
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    project: Mapped[Project] = relationship(back_populates="members")


class ProjectActivity(Base):
    """Снимок метрик, который в дальнейшем заполняет аналитический сборщик."""
    __tablename__ = "project_activity"

    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    last_gitlab_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_redmine_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tasks_done: Mapped[int | None] = mapped_column(Integer)
    tasks_total: Mapped[int | None] = mapped_column(Integer)
    commits_per_day: Mapped[list | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

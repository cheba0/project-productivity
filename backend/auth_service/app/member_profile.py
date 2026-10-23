"""Дополнительные сведения участника в конкретном проекте."""
from uuid import UUID
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from auth_service.app.database import Base


class MemberProfile(Base):
    __tablename__ = 'project_member_profiles'
    member_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('project_members.id', ondelete='CASCADE'), primary_key=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    telegram: Mapped[str | None] = mapped_column(String(100))
    gitlab_profile_url: Mapped[str | None] = mapped_column(String(2048))
    redmine_profile_url: Mapped[str | None] = mapped_column(String(2048))
    gitlab_email: Mapped[str | None] = mapped_column(String(255))
    redmine_user_id: Mapped[int | None] = mapped_column(Integer)

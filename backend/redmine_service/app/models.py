
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from redmine_service.app.database import Base


class RedmineConnection(Base):
    __tablename__ = "redmine_connections"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False
    )
    base_url: Mapped[str] = mapped_column(String(2048))
    token_secret_ref: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RedmineProject(Base):
    __tablename__ = "redmine_projects"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "external_project_id",
            name="uq_redmine_connection_project"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("redmine_connections.id"),
        nullable=False
    )
    external_project_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String(255))
    identifier: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)


class RedmineUser(Base):
    __tablename__ = "redmine_users"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "external_user_id",
            name="uq_redmine_connection_user"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("redmine_connections.id"),
        nullable=False
    )
    external_user_id: Mapped[int] = mapped_column(BigInteger)
    login: Mapped[str | None] = mapped_column(String(255))
    firstname: Mapped[str | None] = mapped_column(String(255))
    lastname: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))


class RedmineStatus(Base):
    __tablename__ = "redmine_statuses"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "external_status_id",
            name="uq_redmine_connection_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("redmine_connections.id"),
        nullable=False
    )
    external_status_id: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)


class RedmineIssue(Base):
    __tablename__ = "redmine_issues"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "external_issue_id",
            name="uq_redmine_connection_issue"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("redmine_connections.id"),
        nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("redmine_projects.id"),
        nullable=False
    )
    external_issue_id: Mapped[int] = mapped_column(BigInteger)
    assignee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("redmine_users.id")
    )
    status_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("redmine_statuses.id"),
        nullable=False
    )
    subject: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    priority_name: Mapped[str | None] = mapped_column(String(255))
    tracker_name: Mapped[str | None] = mapped_column(String(255))
    estimated_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    spent_hours: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    done_ratio: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RedmineIssueStatusHistory(Base):
    __tablename__ = "redmine_issue_status_history"
    __table_args__ = (
        UniqueConstraint(
            "issue_id", "external_journal_id",
            name="uq_redmine_issue_journal"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    issue_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("redmine_issues.id"),
        nullable=False
    )
    external_journal_id: Mapped[int] = mapped_column(BigInteger)
    changed_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("redmine_users.id")
    )
    old_status_id: Mapped[int | None] = mapped_column(Integer)
    new_status_id: Mapped[int] = mapped_column(Integer)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RedmineTimeEntry(Base):
    __tablename__ = "redmine_time_entries"
    __table_args__ = (
        UniqueConstraint(
            "connection_id", "external_entry_id",
            name="uq_redmine_connection_time_entry"
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("redmine_connections.id"),
        nullable=False
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("redmine_projects.id"),
        nullable=False
    )
    issue_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("redmine_issues.id")
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("redmine_users.id"),
        nullable=False
    )
    external_entry_id: Mapped[int] = mapped_column(BigInteger)
    hours: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    activity_name: Mapped[str | None] = mapped_column(String(255))
    comments: Mapped[str | None] = mapped_column(Text)
    spent_on: Mapped[date] = mapped_column(Date)


from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    JSON,
    String,
)
from sqlalchemy.dialects.postgresql import UUID


class RedmineOutboxEvent(Base):
    __tablename__ = "redmine_outbox_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("redmine_connections.id"),
        nullable=False,
        index=True,
    )

    event_type = Column(
        String(100),
        nullable=False,
    )

    payload = Column(
        JSON,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    published_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

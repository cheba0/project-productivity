
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from analytics_service.app.database import Base


class ProjectMapping(Base):
    __tablename__ = "project_mappings"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    gitlab_connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    gitlab_project_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    redmine_connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    redmine_project_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class UserMapping(Base):
    __tablename__ = "user_mappings"

    __table_args__ = (
        UniqueConstraint(
            "project_mapping_id",
            "gitlab_user_id",
            name="uq_mapping_gitlab_user",
        ),
        UniqueConstraint(
            "project_mapping_id",
            "redmine_user_id",
            name="uq_mapping_redmine_user",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_mapping_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project_mappings.id"),
        nullable=False,
    )

    gitlab_user_id: Mapped[int] = mapped_column(BigInteger)
    redmine_user_id: Mapped[int] = mapped_column(BigInteger)

    confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    gitlab_author_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )


class TaskCommitMapping(Base):
    __tablename__ = "task_commit_mappings"

    __table_args__ = (
        UniqueConstraint(
            "project_mapping_id",
            "redmine_issue_id",
            "gitlab_commit_sha",
            name="uq_task_commit_mapping",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_mapping_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project_mappings.id"),
        nullable=False,
    )

    redmine_issue_id: Mapped[int] = mapped_column(BigInteger)

    gitlab_commit_sha: Mapped[str] = mapped_column(String(64))

    confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )


class TaskMergeRequestMapping(Base):
    __tablename__ = "task_merge_request_mappings"

    __table_args__ = (
        UniqueConstraint(
            "project_mapping_id",
            "redmine_issue_id",
            "gitlab_mr_iid",
            name="uq_task_mr_mapping",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_mapping_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project_mappings.id"),
        nullable=False,
    )

    redmine_issue_id: Mapped[int] = mapped_column(BigInteger)
    gitlab_mr_iid: Mapped[int] = mapped_column(Integer)

    confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )


class AnalyticsTask(Base):
    __tablename__ = "analytics_tasks"

    __table_args__ = (
        UniqueConstraint(
            "project_mapping_id",
            "redmine_issue_id",
            name="uq_analytics_task",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_mapping_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project_mappings.id"),
        nullable=False,
    )

    redmine_issue_id: Mapped[int] = mapped_column(BigInteger)

    subject: Mapped[str] = mapped_column(Text)

    assignee_redmine_user_id: Mapped[int | None] = mapped_column(
        BigInteger
    )

    status_name: Mapped[str] = mapped_column(String(255))

    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    estimated_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2)
    )

    spent_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2)
    )

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class AnalyticsCommit(Base):
    __tablename__ = "analytics_commits"

    __table_args__ = (
        UniqueConstraint(
            "project_mapping_id",
            "sha",
            name="uq_analytics_commit",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_mapping_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project_mappings.id"),
        nullable=False,
    )

    sha: Mapped[str] = mapped_column(String(64))

    author_name: Mapped[str | None] = mapped_column(String(255))

    author_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    authored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)

    is_merge: Mapped[bool] = mapped_column(Boolean, default=False)

    title: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class AnalyticsMetric(Base):
    __tablename__ = "analytics_metrics"

    __table_args__ = (
        UniqueConstraint(
            "project_mapping_id",
            "metric_name",
            "period_start",
            "period_end",
            name="uq_analytics_metric_period",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_mapping_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project_mappings.id"),
        nullable=False,
    )

    metric_name: Mapped[str] = mapped_column(String(100))

    metric_value: Mapped[Decimal] = mapped_column(Numeric(18, 4))

    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )

    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True)
    )

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class AnalyticsTimeEntry(Base):
    __tablename__ = "analytics_time_entries"

    __table_args__ = (
        UniqueConstraint(
            "project_mapping_id",
            "redmine_time_entry_id",
            name="uq_analytics_time_entry",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_mapping_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("project_mappings.id"),
        nullable=False,
    )

    redmine_time_entry_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    redmine_issue_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    redmine_user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    hours: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    activity_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    spent_on: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
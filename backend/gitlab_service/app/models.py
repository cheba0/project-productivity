
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from gitlab_service.app.database import Base


class GitLabConnection(Base):
    __tablename__ = "gitlab_connections"

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

    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    base_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    token_secret_ref: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class GitLabProject(Base):
    __tablename__ = "gitlab_projects"

    __table_args__ = (
        UniqueConstraint(
            "connection_id",
            "external_project_id",
            name="uq_gitlab_connection_project",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("gitlab_connections.id"),
        nullable=False,
    )

    external_project_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255))
    path_with_namespace: Mapped[str] = mapped_column(String(1024))
    web_url: Mapped[str] = mapped_column(String(2048))


class GitLabCommit(Base):
    __tablename__ = "gitlab_commits"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "sha",
            name="uq_gitlab_project_commit",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("gitlab_projects.id"),
        nullable=False,
    )

    sha: Mapped[str] = mapped_column(String(64), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(255))
    author_email: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(Text)

    authored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    is_merge: Mapped[bool] = mapped_column(Boolean, default=False)


class GitLabCommitFile(Base):
    __tablename__ = "gitlab_commit_files"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    commit_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("gitlab_commits.id"),
        nullable=False,
    )

    old_path: Mapped[str | None] = mapped_column(Text)
    new_path: Mapped[str | None] = mapped_column(Text)

    is_new: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_renamed: Mapped[bool] = mapped_column(Boolean, default=False)


class GitLabMergeRequest(Base):
    __tablename__ = "gitlab_merge_requests"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "iid",
            name="uq_gitlab_project_mr",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("gitlab_projects.id"),
        nullable=False,
    )

    iid: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(30))

    author_external_id: Mapped[int | None] = mapped_column(BigInteger)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    merged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    web_url: Mapped[str | None] = mapped_column(String(2048))


class GitLabSyncState(Base):
    __tablename__ = "gitlab_sync_state"

    connection_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("gitlab_connections.id"),
        primary_key=True,
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    last_error: Mapped[str | None] = mapped_column(Text)


class GitLabOutboxEvent(Base):
    __tablename__ = "gitlab_outbox_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    topic: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    event_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

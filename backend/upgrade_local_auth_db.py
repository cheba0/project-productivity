"""Safely upgrade ONLY local auth_db (127.0.0.1:5440) after verified backup.

Usage from backend/: python upgrade_local_auth_db.py --apply
Reads backend/.env, not a stale AUTH_DATABASE_URL PowerShell override.
No production/database-server URL is permitted.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent
BACKUP = Path.home() / "tpu-metrics-db-backups" / "tpu_auth_20261031_053220.dump"
BACKUP_SHA256 = "228c07e10b360028fbd212a1aef871d5b18b8e33d485cc7499121808acceda9f"
INITIAL = "c820dcf27a76"
TARGET = "f6a1c4e27b90"
OLD_TABLES = ("users", "workspaces", "workspace_members", "auth_sessions")
NEW_TABLES = (
    "projects", "project_members", "project_activity",
    "project_member_profiles", "project_metric_snapshots",
)


def database_state(engine):
    with engine.connect() as db:
        tables = set(inspect(db).get_table_names(schema="public"))
        if "alembic_version" not in tables:
            raise RuntimeError("auth_db has no Alembic version table")
        revisions = db.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalars().all()
        if len(revisions) != 1:
            raise RuntimeError(f"Unexpected Alembic version count: {len(revisions)}")
        if not set(OLD_TABLES) <= tables:
            raise RuntimeError("Existing auth tables are missing")
        counts = {
            table: db.scalar(text(f'SELECT count(*) FROM "{table}"'))
            for table in OLD_TABLES
        }
        # Verify that not just the number but also the existing user IDs
        # survive the migration. Neither IDs nor user details are printed.
        ids = sorted(str(user_id) for user_id in db.execute(
            text("SELECT id FROM users")
        ).scalars())
        user_digest = hashlib.sha256("\n".join(ids).encode()).hexdigest()
        return revisions[0], tables, counts, user_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually upgrade local auth_db; otherwise preflight only",
    )
    args = parser.parse_args()

    config = dotenv_values(ROOT / ".env")
    raw = config.get("AUTH_DATABASE_URL")
    if not raw:
        raise SystemExit("STOP: AUTH_DATABASE_URL missing from backend/.env")
    url = make_url(raw)
    if not (
        url.drivername.startswith("postgresql")
        and url.host in ("localhost", "127.0.0.1")
        and url.port == 5440
        and url.database == "auth_db"
        and url.username == "auth_user"
    ):
        raise SystemExit("STOP: expected local auth_user/auth_db on 127.0.0.1:5440")

    if not BACKUP.is_file():
        raise SystemExit(f"STOP: backup missing: {BACKUP}")
    if hashlib.sha256(BACKUP.read_bytes()).hexdigest() != BACKUP_SHA256:
        raise SystemExit("STOP: auth_db backup checksum mismatch")
    if os.environ.get("AUTH_DATABASE_URL") != raw:
        print("Using verified backend/.env auth_db (ignoring shell override).")

    engine = create_engine(raw, pool_pre_ping=True)
    try:
        before_revision, before_tables, before_counts, before_digest = database_state(engine)
        print("=== AUTH DB MIGRATION PREFLIGHT ===")
        print("Verified backup:", BACKUP.name)
        print("Current revision:", before_revision)
        for table, count in before_counts.items():
            print(f"{table}: {count}")

        if before_revision == TARGET:
            if not set(NEW_TABLES) <= before_tables:
                raise RuntimeError("Alembic is at head but required tables are missing")
            print("ALREADY UP TO DATE; no migration needed")
            return
        if before_revision != INITIAL:
            raise RuntimeError(
                f"Unexpected auth_db revision {before_revision}; stop for manual review"
            )
        if set(NEW_TABLES) & before_tables:
            raise RuntimeError(
                "New project tables already exist before migration; stop for manual review"
            )
        if not args.apply:
            print("PREFLIGHT PASSED (read-only). Run with --apply to migrate.")
            return

        print("=== APPLY AUTH DB MIGRATIONS ===")
        env = os.environ.copy()
        # The shell may still point to the isolated tpu_auth_test database.
        env["AUTH_DATABASE_URL"] = raw
        subprocess.run(
            [
                sys.executable, "-m", "alembic",
                "-c", str(ROOT / "auth_service" / "alembic.ini"),
                "upgrade", TARGET,
            ],
            env=env, cwd=ROOT, check=True,
        )

        after_revision, after_tables, after_counts, after_digest = database_state(engine)
        if after_revision != TARGET:
            raise RuntimeError("Migration did not reach the expected revision")
        if not set(NEW_TABLES) <= after_tables:
            raise RuntimeError("Migration did not create all required tables")
        if before_counts != after_counts or before_digest != after_digest:
            raise RuntimeError("Existing auth data changed unexpectedly")
        with engine.connect() as db:
            count = db.scalar(text("SELECT count(*) FROM projects"))
            snapshots = db.scalar(text("SELECT count(*) FROM project_metric_snapshots"))
            print(f"projects: {count}")
            print(f"project_metric_snapshots: {snapshots}")

        print("AUTH DB MIGRATIONS VERIFIED")
        print("Existing users, workspaces, sessions and memberships preserved.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()

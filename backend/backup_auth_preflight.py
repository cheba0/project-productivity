"""Read-only auth_db preflight + verified pg_dump backup.

Never migrates or writes application database rows.
Reads backend/.env, deliberately ignores shell AUTH_DATABASE_URL because
the isolated test DB on port 55440 may still be selected in PowerShell.

Run from backend/: python backup_auth_preflight.py
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import os
import subprocess

from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent
BACKUPS = Path.home() / "tpu-metrics-db-backups"
CONTAINER = "backend-auth_db-1"
EXPECTED_REVISIONS = {
    "4696da03a279", "c820dcf27a76", "d127c8e8a441",
    "e3281d10b152", "f6a1c4e27b90",
}
TABLES = (
    "users", "workspaces", "workspace_members", "auth_sessions",
    "projects", "project_members", "project_activity",
    "project_member_profiles", "project_metric_snapshots",
)


def run(*arguments):
    return subprocess.run(
        arguments, check=True, capture_output=True, text=True
    )


def main():
    env = dotenv_values(ROOT / ".env")
    raw = env.get("AUTH_DATABASE_URL")
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
        raise SystemExit(
            "STOP: backend/.env must point to LOCAL auth_db "
            "as auth_user on port 5440"
        )

    if os.getenv("AUTH_DATABASE_URL"):
        print("NOTE: ignoring PowerShell AUTH_DATABASE_URL override; using backend/.env")
    print("=== AUTH DB PREFLIGHT (NO DB WRITES) ===")

    engine = create_engine(raw, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            tables = set(inspect(connection).get_table_names(schema="public"))
            revisions = (
                connection.execute(text("SELECT version_num FROM alembic_version"))
                .scalars().all()
                if "alembic_version" in tables else []
            )
            if len(revisions) != 1 or revisions[0] not in EXPECTED_REVISIONS:
                raise SystemExit(
                    "STOP: unexpected auth_db Alembic state; do not migrate automatically"
                )
            print("Alembic revision:", revisions[0])
            for table in TABLES:
                if table in tables:
                    # Fixed, code-owned names (not user-provided SQL identifiers).
                    count = connection.scalar(text(f'SELECT count(*) FROM "{table}"'))
                    print(f"{table}: {count}")
                else:
                    print(f"{table}: TABLE NOT FOUND")
    finally:
        engine.dispose()

    print("\\n=== VERIFIED AUTH DB BACKUP ===")
    BACKUPS.mkdir(parents=True, exist_ok=True)
    filename = "tpu_auth_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + ".dump"
    remote = "/tmp/" + filename
    local = BACKUPS / filename
    if local.exists():
        raise SystemExit("STOP: backup filename collision")
    try:
        run(
            "docker", "exec", CONTAINER,
            "pg_dump", "-U", url.username, "-d", url.database,
            "-Fc", "-f", remote,
        )
        run("docker", "exec", CONTAINER, "pg_restore", "--list", remote)
        remote_sha = run(
            "docker", "exec", CONTAINER, "sha256sum", remote
        ).stdout.split()[0]
        run("docker", "cp", f"{CONTAINER}:{remote}", str(local))
        actual_sha = sha256(local.read_bytes()).hexdigest()
        if remote_sha != actual_sha:
            raise RuntimeError("STOP: backup SHA256 mismatch")
        print("BACKUP VERIFIED:", local)
        print("SIZE:", local.stat().st_size, "bytes")
        print("SHA256:", actual_sha)
        print("AUTH DB PREFLIGHT AND BACKUP PASSED")
    finally:
        subprocess.run(
            ["docker", "exec", CONTAINER, "rm", "-f", remote],
            capture_output=True,
        )


if __name__ == "__main__":
    main()

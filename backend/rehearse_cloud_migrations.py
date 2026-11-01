"""Stage 2 Cloud.ru migration rehearsal, LOCAL Windows Docker only.

Restores four previously SHA256-verified server dumps to a uniquely named,
disposable PostgreSQL 16 container on Docker Desktop. The only published
port is a random available 127.0.0.1 port. Runs the checked-in Alembic
upgrades for auth, analytics and redmine, and verifies row preservation.
NEVER connects to Cloud.ru or existing Docker PostgreSQL containers.
"""
from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
import time
from contextlib import closing

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url

from rehearse_cloud_db_restore import (
    ARCHIVES, BACKUP_DIR, assert_local_docker, require_success, verify_archives,
)

ROOT = os.path.dirname(os.path.abspath(__file__))

# These revisions were read directly from the running Cloud.ru databases.
MIGRATIONS = {
    "auth": ("backend-auth_db-1.dump", "restore_auth",
             "e3281d10b152", "f6a1c4e27b90",
             "auth_service/alembic.ini", "AUTH_DATABASE_URL"),
    "analytics": ("backend-analytics_db-1.dump", "restore_analytics",
                  "e82c91a4f703", "f2c48b19a6d0",
                  "analytics_service/alembic.ini", "ANALYTICS_DATABASE_URL"),
    "redmine": ("backend-redmine_db-1.dump", "restore_redmine",
                "f19b789a33b0", "c4a53d9e40f1",
                "redmine_service/alembic.ini", "REDMINE_DATABASE_URL"),
}
GITLAB_BASELINE = ("backend-gitlab_db-1.dump", "restore_gitlab", "2d1ef2e14b5e")
EXPECTED_COLUMNS = {
    "analytics": ("analytics_tasks", ("start_date", "due_date")),
    "redmine": ("redmine_issues", ("start_date", "due_date")),
}


def free_local_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def target_url(port, password, database):
    if database not in {"restore_auth", "restore_analytics",
                        "restore_redmine", "restore_gitlab"}:
        raise RuntimeError("Refusing unknown rehearsal database")
    url = URL.create(
        "postgresql+psycopg2", username="postgres", password=password,
        host="127.0.0.1", port=port, database=database,
    )
    parsed = make_url(url)
    if (parsed.username != "postgres" or parsed.host != "127.0.0.1"
            or parsed.port != port or parsed.database != database):
        raise RuntimeError("Refusing non-local migration target")
    return url


def postgres_readiness_url(port, password):
    """Use the existing default maintenance DB, NOT a not-yet-created restore DB."""
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise RuntimeError("Invalid isolated local PostgreSQL port")
    return URL.create(
        "postgresql+psycopg2", username="postgres", password=password,
        host="127.0.0.1", port=port, database="postgres",
    )


def wait_for_postgres(port, password):
    """Prove localhost host-port connectivity before creating restored databases."""
    from sqlalchemy.exc import OperationalError

    url = postgres_readiness_url(port, password)
    for _ in range(50):
        engine = create_engine(
            url, pool_pre_ping=True, connect_args={"connect_timeout": 2},
        )
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("POSTGRES READY: default postgres database", flush=True)
            return
        except OperationalError:
            time.sleep(1)
        finally:
            engine.dispose()
    raise RuntimeError("Local temporary PostgreSQL did not become ready")


def snapshot(url):
    """Inspect this RESTORED DB: exact row counts, columns and revision."""
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
    try:
        schema = inspect(engine)
        tables = schema.get_table_names(schema="public")
        if not tables or "alembic_version" not in tables:
            raise RuntimeError("Restored database has no Alembic baseline")
        counts = {}
        with engine.connect() as conn:
            revision = conn.scalar(text("SELECT version_num FROM alembic_version"))
            for table in tables:
                quoted = engine.dialect.identifier_preparer.quote(table)
                counts[table] = conn.scalar(
                    text("SELECT count(*) FROM public." + quoted)
                )
        columns = {}
        for table in tables:
            columns[table] = {col["name"] for col in schema.get_columns(table, schema="public")}
        return revision, counts, columns
    finally:
        engine.dispose()


def assert_preserved(before, after, role):
    _, initial_counts, _ = before
    _, final_counts, _ = after
    for table, count in initial_counts.items():
        if table == "alembic_version":
            continue
        if table not in final_counts or final_counts[table] != count:
            raise RuntimeError("Pre-existing rows changed in " + role + " database")
    added = set(final_counts) - set(initial_counts)
    if role == "auth":
        if added != {"project_metric_snapshots"}:
            raise RuntimeError("Unexpected auth schema table change")
        if final_counts["project_metric_snapshots"] != 0:
            raise RuntimeError("New auth snapshot table not empty")
    elif added:
        raise RuntimeError("Unexpected added tables in " + role)


def assert_upgrade(role, before, after):
    expected_before = MIGRATIONS[role][2]
    expected_after = MIGRATIONS[role][3]
    if before[0] != expected_before:
        raise RuntimeError("STOP: " + role + " source revision does not match Cloud.ru")
    if after[0] != expected_after:
        raise RuntimeError("Migration target not reached for " + role)
    assert_preserved(before, after, role)
    if role in EXPECTED_COLUMNS:
        table, fields = EXPECTED_COLUMNS[role]
        before_columns = before[2].get(table, set())
        after_columns = after[2].get(table, set())
        if any(field in before_columns for field in fields):
            raise RuntimeError("Target date columns unexpectedly exist before migration")
        if not set(fields).issubset(after_columns):
            raise RuntimeError("Task date columns not created")


def restore_into(name, filename, db):
    archive = BACKUP_DIR / filename
    require_success(
        ["docker", "cp", str(archive), name + ":/tmp/" + filename],
        "Copy verified archive to isolated container", timeout=35,
    )
    require_success(
        ["docker", "exec", name, "createdb", "-U", "postgres", db],
        "Create isolated restore database",
    )
    require_success(
        ["docker", "exec", name, "pg_restore", "--exit-on-error",
         "--no-owner", "--no-acl", "-U", "postgres", "-d", db,
         "/tmp/" + filename],
        "Restore server archive in local container", timeout=150,
    )


def run_upgrade(role, url):
    _, database, _, target, ini, key = MIGRATIONS[role]
    # The constructed URL is used ONLY by a new local Docker instance.
    local = make_url(url)
    if (local.host != "127.0.0.1" or local.database != database
            or local.username != "postgres"):
        raise RuntimeError("Migration URL fails local identity guard")
    env = os.environ.copy()
    env[key] = local.render_as_string(hide_password=False)
    env["TPU_CLIENT_ID"] = "synthetic-local-migration-only"
    env["TPU_CLIENT_SECRET"] = "synthetic-local-migration-only"
    env["TPU_API_KEY"] = "synthetic-local-migration-only"
    env["TPU_REDIRECT_URI"] = "https://example.invalid/callback"
    env["PYTHONPATH"] = ROOT
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", os.path.join(ROOT, ini),
             "upgrade", target],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("Local Alembic migration process unavailable") from None
    if result.returncode != 0:
        raise RuntimeError("Alembic migration failed for " + role +
                           " (details suppressed; no secrets printed)")


def main():
    print("=== CLOUD.RU MIGRATION REHEARSAL / LOCAL ONLY ===", flush=True)
    print("No Cloud.ru access; production, local auth_db and analytics_db untouched", flush=True)
    verify_archives()
    assert_local_docker()
    if any(name not in ARCHIVES for name, *_ in MIGRATIONS.values()):
        raise RuntimeError("Migration rehearsal archive missing from verified manifest")
    name = "tpu-migration-check-" + secrets.token_hex(6)
    password = secrets.token_urlsafe(28)
    port = free_local_port()
    started = False
    try:
        require_success([
            "docker", "run", "--rm", "--detach", "--network", "bridge",
            "--name", name,
            "--publish", "127.0.0.1:" + str(port) + ":5432",
            "--env", "POSTGRES_PASSWORD=" + password,
            "postgres:16",
        ], "Start isolated local PostgreSQL", timeout=60)
        started = True
        print("EPHEMERAL POSTGRES: 127.0.0.1 LOOPBACK ONLY; RANDOM PORT", flush=True)
        wait_for_postgres(port, password)
        for role, (filename, db, before_rev, _, _, _) in MIGRATIONS.items():
            restore_into(name, filename, db)
            url = target_url(port, password, db)
            before = snapshot(url)
            if before[0] != before_rev:
                raise RuntimeError("STOP: " + role + " archive has unexpected revision")
            print(role.upper() + " BEFORE:", before[0], flush=True)
            run_upgrade(role, url)
            after = snapshot(url)
            assert_upgrade(role, before, after)
            print(role.upper() + " AFTER:", after[0],
                  "| EXISTING ROWS PRESERVED: YES", flush=True)
        filename, db, expected = GITLAB_BASELINE
        restore_into(name, filename, db)
        gitlab_url = target_url(port, password, db)
        revision, counts, _ = snapshot(gitlab_url)
        if revision != expected:
            raise RuntimeError("STOP: GitLab archive unexpected revision")
        print("GITLAB UNCHANGED:", revision,
              "| PUBLIC TABLES:", len(counts), flush=True)
        print("ALL 3 CLOUD MIGRATIONS PASSED ON LOCAL RESTORED COPIES", flush=True)
    finally:
        if started:
            try:
                result = subprocess.run(
                    ["docker", "rm", "--force", name],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=45, check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                result = None
            if result is None or result.returncode != 0:
                raise RuntimeError(
                    "Temporary migration container cleanup not confirmed; "
                    "only inspect temporary container " + name
                )
            print("TEMPORARY MIGRATION CONTAINER REMOVED", flush=True)
            print("NO EXISTING DATABASES OR CLOUD.RU CHANGED", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        print("STOP:", str(exc), flush=True)
        raise SystemExit(1) from None

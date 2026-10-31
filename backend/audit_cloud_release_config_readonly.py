"""Read-only release configuration inventory, intended for Linux Cloud.ru VM.

Run over SSH stdin: Get-Content -Raw .\audit_cloud_release_config_readonly.py |
    ssh -T -i $sshKey $sshTarget "python3 -"

Never prints Docker environment values, tokens, passwords, DB connection
strings, container IDs or arbitrary filenames. Does not edit server state.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

CONTAINERS = {
    "auth": "backend-auth_service-1",
    "analytics": "backend-analytics_service-1",
    "gitlab": "backend-gitlab_service-1",
    "redmine": "backend-redmine_service-1",
    "consumer": "backend-analytics_consumer-1",
    "worker": "backend-project_sync_worker-1",
}
DBS = {
    "auth": ("backend-auth_db-1", "f6a1c4e27b90"),
    "analytics": ("backend-analytics_db-1", "f2c48b19a6d0"),
    "redmine": ("backend-redmine_db-1", "c4a53d9e40f1"),
}
BACKUP = (
    Path.home() / "tpu-metrics-db-backups" / "20261031_064618"
    / "redmine-test-files.tar"
)
REDMINE_LOCAL_SHA256 = "c190cd1f9704943c33988ff5224650ba71fbb4fd4291d735c3276522dc731edc"
DB_URLS = {
    "AUTH_DATABASE_URL": "auth_db",
    "GITLAB_DATABASE_URL": "gitlab_db",
    "REDMINE_DATABASE_URL": "redmine_db",
    "ANALYTICS_DATABASE_URL": "analytics_db",
}


def run(argv, timeout=15):
    try:
        result = subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def get_env(name):
    # Docker inspect returns secret values in-process; never display raw output.
    raw = run(["docker", "inspect", "--format", "{{json .Config.Env}}", name])
    if raw is None:
        return None
    try:
        values = json.loads(raw)
        if not isinstance(values, list):
            return None
        return dict(item.split("=", 1) for item in values
                    if isinstance(item, str) and "=" in item)
    except (ValueError, TypeError):
        return None


def classify_db_url(value, expected_host):
    if not value:
        return "MISSING"
    try:
        target = urlsplit(value)
        if target.scheme not in ("postgresql", "postgresql+psycopg2"):
            return "UNEXPECTED DRIVER"
        host, port = target.hostname, target.port
        if host == expected_host and port == 5432:
            return "DOCKER DNS OK"
        if host in ("localhost", "127.0.0.1"):
            return "LOOPBACK HOST (REVIEW)"
        return "OTHER DESTINATION (REVIEW)"
    except ValueError:
        return "INVALID URL"


def present(value):
    return "PRESENT" if value and not value.strip().upper().startswith(
        ("REPLACE_", "CHANGEME", "TODO_")
    ) else "MISSING OR PLACEHOLDER"


def safe_env_report(name, env):
    print("\nSERVICE:", name, flush=True)
    if env is None:
        print("CONTAINER ENV: UNAVAILABLE", flush=True)
        return
    print("CONTAINER ENV: READ (VALUES REDACTED)", flush=True)
    if name == "auth":
        for key in ("TPU_CLIENT_ID", "TPU_CLIENT_SECRET",
                    "TPU_API_KEY", "PROJECT_TOKEN_ENCRYPTION_KEY",
                    "PROJECT_API_ALLOWED_HOSTS"):
            print(key + ":", present(env.get(key)), flush=True)
        print("TPU_COOKIE_SECURE:",
              "ENABLED" if env.get("TPU_COOKIE_SECURE", "").lower() == "true"
              else "NOT CONFIRMED", flush=True)
        print("TPU_FRONTEND_URL:",
              "EXPECTED HTTPS ORIGIN" if
              env.get("TPU_FRONTEND_URL", "").rstrip("/") ==
              "https://tpu-metrics.duckdns.org" else "OTHER / MISSING",
              flush=True)
        print("TPU_REDIRECT_URI:",
              "EXPECTED CALLBACK" if
              env.get("TPU_REDIRECT_URI") ==
              "https://tpu-metrics.duckdns.org/auth/tpu/callback"
              else "OTHER / MISSING", flush=True)
    for key, expected in DB_URLS.items():
        if key in env:
            print(key + ":", classify_db_url(env.get(key), expected), flush=True)
    if name in ("consumer", "worker"):
        print("KAFKA_BOOTSTRAP_SERVERS:",
              "CONTAINER DNS OK" if env.get("KAFKA_BOOTSTRAP_SERVERS") == "kafka:9094"
              else "NOT CONFIRMED", flush=True)
    if name == "redmine":
        redmine = env.get("REDMINE_URL", "")
        try:
            host = urlsplit(redmine).hostname
        except ValueError:
            host = None
        print("REDMINE_URL:",
              "LOCAL TEST / REVIEW" if host in ("localhost", "127.0.0.1", "redmine-test-redmine-1")
              or (host or "").endswith(".local")
              else "PRESENT / REVIEW HOST" if host else "MISSING",
              flush=True)


def check_db_revision(name, container, target):
    sql = 'SELECT version_num FROM alembic_version'
    expression = (
        'export PGPASSWORD="$POSTGRES_PASSWORD"; '
        'exec psql -X -w -U "$POSTGRES_USER" -d "$POSTGRES_DB" '
        '-Atqc "' + sql + '"'
    )
    value = run(["docker", "exec", container, "sh", "-c", expression], timeout=20)
    if value is None or not re.fullmatch("[a-f0-9]{12}", value):
        state = "UNKNOWN"
    elif value == target:
        state = "AT FEATURE MIGRATION"
    else:
        state = "NOT AT FEATURE MIGRATION"
    print(name + " DB revision:", state, flush=True)


def inspect_redmine_backup():
    print("\n=== REDMINE ATTACHMENT RECONCILIATION ===", flush=True)
    if not BACKUP.is_file():
        print("SERVER ARCHIVE: NOT FOUND", flush=True)
    else:
        digest = hashlib.sha256()
        with BACKUP.open("rb") as source:
            for part in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(part)
        print("SERVER VS WINDOWS ARCHIVE SHA256:",
              "MATCH" if digest.hexdigest() == REDMINE_LOCAL_SHA256 else "MISMATCH",
              flush=True)
    files = run([
        "docker", "exec", "redmine-test-redmine-1", "sh", "-c",
        'find /usr/src/redmine/files -type f | wc -l',
    ])
    if files is not None and files.isdigit():
        print("CURRENT REDMINE ATTACHMENT FILE COUNT:", int(files), flush=True)
        print("ARCHIVE FILE COUNT ON WINDOWS: 0", flush=True)
        print("CURRENT VS ARCHIVE:",
              "BOTH EMPTY" if int(files) == 0 else "DO NOT MATCH",
              flush=True)
    else:
        print("CURRENT REDMINE ATTACHMENT FILE COUNT: UNAVAILABLE", flush=True)


def main():
    print("=== CLOUD.RU LIVE CONFIG READ-ONLY REVIEW ===", flush=True)
    print("No secrets or Docker environment values printed", flush=True)
    print("No service restarts, database changes, or filesystem writes", flush=True)

    for role, container in CONTAINERS.items():
        safe_env_report(role, get_env(container))

    print("\n=== DATABASE SCHEMA MIGRATION BASELINE ===", flush=True)
    for name, (container, target) in DBS.items():
        check_db_revision(name, container, target)

    inspect_redmine_backup()
    print("\nRELEASE CONFIG AUDIT COMPLETE; PRODUCTION UNCHANGED", flush=True)
    print("THIS IS NOT DEPLOYMENT APPROVAL", flush=True)


if __name__ == "__main__":
    main()

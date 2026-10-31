"""Preview LOCAL Docker DNS overrides without modifying .env or starting Docker.

Uses the existing production readiness checker on the merged Compose output.
Only prints nonsecret checks. It does not deploy, start, build or restart.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

import preflight_compose_deployment as audit

ROOT = Path(__file__).resolve().parent

DATABASES = {
    "AUTH_DATABASE_URL": ("auth_db", 5440, "auth_user"),
    "GITLAB_DATABASE_URL": ("gitlab_db", 5434, "gitlab_user"),
    "REDMINE_DATABASE_URL": ("redmine_db", 5435, "redmine_user"),
    "ANALYTICS_DATABASE_URL": ("analytics_db", 5436, "analytics_user"),
}

# Only these three existing deployment blockers are expected to remain.
EXPECTED_BLOCKERS = {
    "PROJECT_TOKEN_ENCRYPTION_KEY is missing",
    ("PROJECT_API_ALLOWED_HOSTS is empty: arbitrary public provider "
     "domains and DNS-rebinding risks require egress/SSRF review"),
    "redmine_service points to local test Redmine; never use that in Cloud.ru",
}


def container_variables():
    source = dotenv_values(ROOT / ".env")
    result = {}
    for key, (hostname, port, username) in DATABASES.items():
        value = source.get(key)
        if not value:
            raise RuntimeError(f"STOP: {key} is missing from backend/.env")
        url = make_url(value)
        if not (
            url.drivername.startswith("postgresql")
            and url.host in {"localhost", "127.0.0.1"}
            and url.port == port
            and url.database == hostname
            and url.username == username
        ):
            raise RuntimeError(
                f"STOP: {key} is not the expected local PostgreSQL URL "
                "(no credentials shown)"
            )
        # URL.set() preserves encoded database passwords, including symbols.
        result["TPU_DOCKER_" + key] = url.set(
            host=hostname, port=5432
        ).render_as_string(hide_password=False)
    return result


def main():
    print("=== LOCAL DOCKER COMPOSE CONFIG PREVIEW ===")
    print("Mode: read-only, no changes to .env or running containers")
    variables = container_variables()
    files = (
        "docker-compose.yml",
        "compose.services.yml",
        "compose.local-runtime.yml",
    )
    audit.COMPOSE_FILES = files
    audit.BLOCKERS.clear()
    audit.NOTES.clear()

    # The secrets are passed only to the child docker compose config command
    # through its process environment, not saved to a generated env file.
    # Existing PowerShell variables are preserved.
    with patch.dict(os.environ, variables):
        audit.main()

    remaining = set(audit.BLOCKERS)
    unexpected = remaining - EXPECTED_BLOCKERS
    if unexpected:
        print("LOCAL DOCKER CONFIG PREVIEW FAILED: unexpected blocker(s) remain")
        raise SystemExit(1)
    if len(audit.BLOCKERS) != len(remaining):
        print("LOCAL DOCKER CONFIG PREVIEW FAILED: repeated blocker(s)")
        raise SystemExit(1)
    print("LOCAL CONTAINER DB AND KAFKA DNS CHECKS PASSED")
    print("Remaining production blockers:", len(remaining))
    print("NO CONTAINERS STARTED; NO ENV FILES MODIFIED")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never echo connection strings, child-process stderr or secret values.
        print("LOCAL PREVIEW STOPPED:", type(exc).__name__)
        raise SystemExit(1) from None

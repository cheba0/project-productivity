"""Step 31: final SAFE local backend regression suite before PR review.

Verifies local auth_db and analytics_db identities before any subtests.
All selected tests are read-only and must not contact real GitLab, Redmine,
TPU OAuth, or Cloud.ru. No Docker containers are started or restarted.
The isolated auth_test DB mutating tests are intentionally NOT run.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent
DBS = {
    "AUTH_DATABASE_URL": ("auth_db", 5440, "auth_user"),
    "ANALYTICS_DATABASE_URL": ("analytics_db", 5436, "analytics_user"),
}
TABLES = {
    "AUTH_DATABASE_URL": (
        "users", "workspaces", "workspace_members", "auth_sessions",
        "projects", "project_members", "project_activity",
        "project_member_profiles", "project_metric_snapshots",
    ),
    "ANALYTICS_DATABASE_URL": (
        "project_mappings", "analytics_tasks",
        "analytics_commits", "analytics_time_entries",
    ),
}
UNIT_TESTS = (
    "test_browser_security",
    "test_provider_token_contracts",
    "test_cloud_env_preflight",
    "test_dashboard_extras",
    "test_dashboard_student_metrics",
    "test_project_snapshot_selection",
)
CHECKS = (
    ("Python source compiles", ["-m", "compileall", "-q",
                                 "auth_service", "test_browser_security.py",
                                 "test_provider_token_contracts.py",
                                 "test_cloud_env_preflight.py",
                                 "test_linked_project_read_api.py"]),
    ("Offline unit regression suite",
     ["-m", "unittest", "-v", *UNIT_TESTS]),
    ("Cloud deployment template (placeholders only)",
     ["preflight_cloud_env.py", "--template"]),
    ("Linked project API (local read-only)",
     ["test_linked_project_read_api.py"]),
    ("Actual localhost HTTP service startup", ["smoke_local_auth_http.py"]),
    ("Merged Docker Compose DNS preview (no startup)",
     ["preview_local_compose_config.py"]),
)


def local_urls():
    settings = dotenv_values(ROOT / ".env")
    urls = {}
    for key, (name, port, username) in DBS.items():
        raw = settings.get(key)
        if not raw:
            raise RuntimeError(f"STOP: {key} is absent in backend/.env")
        parsed = make_url(raw)
        if not (
            parsed.drivername.startswith("postgresql")
            and parsed.host in ("127.0.0.1", "localhost")
            and parsed.port == port
            and parsed.database == name and parsed.username == username
        ):
            raise RuntimeError(f"STOP: {key} does not match the expected LOCAL database")
        urls[key] = raw
    return urls


def snapshot_counts(urls):
    """Read table counts only; do not show connection URLs or identities."""
    counts = {}
    for key, tables in TABLES.items():
        engine = create_engine(urls[key], pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                counts[key] = {}
                for name in tables:
                    # Table names are compile-time constants, not user input.
                    counts[key][name] = conn.scalar(
                        text(f'SELECT count(*) FROM "{name}"')
                    )
        finally:
            engine.dispose()
    return counts


def check_schema(urls):
    expected = {
        "AUTH_DATABASE_URL": "f6a1c4e27b90",
        "ANALYTICS_DATABASE_URL": "f2c48b19a6d0",
    }
    for key, revision in expected.items():
        engine = create_engine(urls[key], pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                found = conn.scalar(text("SELECT version_num FROM alembic_version"))
                if found != revision:
                    raise RuntimeError(f"STOP: unexpected {key} Alembic revision")
        finally:
            engine.dispose()


def main():
    print("=== STEP 31 / LOCAL RELEASE ACCEPTANCE ===", flush=True)
    print("No production access, provider calls or database migrations", flush=True)
    print("No isolated auth_test DB mutations", flush=True)
    urls = local_urls()
    check_schema(urls)
    baseline = snapshot_counts(urls)
    print("Local database targets/revisions: VERIFIED", flush=True)
    print("Table row-count baselines: RECORDED", flush=True)

    env = os.environ.copy()
    env.update(urls)
    env["PYTHONPATH"] = str(ROOT)
    env["TPU_FRONTEND_URL"] = "https://tpu-metrics.duckdns.org"
    env["TPU_COOKIE_SECURE"] = "true"
    env.pop("PROJECT_GITLAB_API_BASE", None)

    completed = 0
    failure = None
    try:
        for label, args in CHECKS:
            print("\n--- " + label + " ---", flush=True)
            # Env values are never printed; tests use fake API responses.
            finished = subprocess.run(
                [sys.executable, *args], cwd=ROOT, env=env,
                timeout=150, check=False,
            )
            if finished.returncode != 0:
                failure = label
                print("FAILED CHECK: " + label, flush=True)
                break
            completed += 1
            print("PASSED: " + label, flush=True)
    except subprocess.TimeoutExpired:
        failure = "Test subprocess timed out"
        print("FAILED: test subprocess timeout", flush=True)
    except OSError:
        failure = "Test subprocess could not be started"
        print("FAILED: failed to start test subprocess", flush=True)
    finally:
        after = snapshot_counts(urls)
        unchanged = baseline == after
        print("\n=== FINAL ACCEPTANCE REPORT ===", flush=True)
        print(f"Checks passed: {completed}/{len(CHECKS)}", flush=True)
        print("Local database table counts unchanged:",
              "YES" if unchanged else "NO", flush=True)
        print("Real TPU OAuth and real provider connectivity: NOT TESTED", flush=True)
        print("Cloud.ru HTTPS proxy and outbound firewall: NOT TESTED", flush=True)
        print("Frontend integration, staging deployment/rollback: NOT TESTED", flush=True)
        if not unchanged:
            print("STOP: unexpected DB row-count changes detected", flush=True)
        elif failure:
            print("LOCAL RELEASE ACCEPTANCE: FAILED (" + failure + ")", flush=True)
        else:
            print("LOCAL RELEASE ACCEPTANCE PASSED", flush=True)
            print("READY FOR PR REVIEW, NOT YET APPROVED FOR PRODUCTION", flush=True)
        if not unchanged or failure:
            raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as exc:
        # None of these diagnostic messages includes a database URL.
        print(str(exc), flush=True)
        raise SystemExit(1) from None

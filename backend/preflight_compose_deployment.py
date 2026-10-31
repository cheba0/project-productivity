"""Read-only deployment readiness audit of the merged Docker Compose stack.

No database connections, no containers started, no secrets printed.
Run from backend/: .\\.venv\\Scripts\\python.exe .\\preflight_compose_deployment.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent
COMPOSE_FILES = ("docker-compose.yml", "compose.services.yml")
EXPECTED_SERVICES = {
    "auth_db", "gitlab_db", "redmine_db", "analytics_db", "kafka",
    "auth_service", "gitlab_service", "redmine_service",
    "analytics_service", "analytics_consumer", "project_sync_worker",
}
DB_URLS = {
    "AUTH_DATABASE_URL": "auth_db",
    "GITLAB_DATABASE_URL": "gitlab_db",
    "REDMINE_DATABASE_URL": "redmine_db",
    "ANALYTICS_DATABASE_URL": "analytics_db",
}
BLOCKERS = []
NOTES = []


def block(description):
    BLOCKERS.append(description)
    print("BLOCKER:", description)


def note(description):
    NOTES.append(description)
    print("NOTE:", description)


def compose_config():
    command = ["docker", "compose"]
    for name in COMPOSE_FILES:
        if not (ROOT / name).is_file():
            raise RuntimeError(f"Missing Compose file: {name}")
        command.extend(["-f", name])
    command.extend(["config", "--format", "json"])
    try:
        proc = subprocess.run(
            command, cwd=ROOT, text=True, encoding="utf-8",
            capture_output=True, timeout=35, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(
            "Docker Compose config command unavailable or timed out; no stack was started"
        ) from None
    # IMPORTANT: don't print stdout/stderr; 'config' expands .env secrets.
    if proc.returncode != 0:
        raise RuntimeError(
            "Merged Docker Compose config failed. Resolve using the two Compose files; "
            "do not share raw 'docker compose config' output (it contains secrets)."
        )
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        raise RuntimeError("Docker Compose returned invalid JSON") from None
    if not isinstance(data, dict) or not isinstance(data.get("services"), dict):
        raise RuntimeError("Docker Compose returned an unexpected structure")
    return data["services"]


def container_database_url(services, key, hostname):
    # Require the backend service to use the database's Docker DNS hostname,
    # not the Windows host-port mapping (127.0.0.1:5440 etc).
    service = services.get("auth_service") or {}
    environment = service.get("environment") or {}
    raw = environment.get(key) if isinstance(environment, dict) else None
    if not raw:
        block(f"auth_service: {key} is not configured")
        return
    try:
        url = make_url(raw)
    except Exception:
        block(f"auth_service: {key} is not a valid SQLAlchemy database URL")
        return
    if (
        not url.drivername.startswith("postgresql")
        or url.host != hostname
        or url.port not in (None, 5432)
        or url.database != hostname
    ):
        block(
            f"{key}: container needs '{hostname}:5432/{hostname}', "
            "not a Windows localhost/host-port address"
        )
    else:
        print(f"{key}: container DNS and port OK")


def app_database(service, services, key, hostname):
    env = services.get(service, {}).get("environment") or {}
    if not isinstance(env, dict):
        block(f"{service}: invalid environment")
        return
    raw = env.get(key)
    if not raw:
        block(f"{service}: {key} missing")
        return
    try:
        url = make_url(raw)
        if url.host != hostname or url.port not in (None, 5432):
            block(f"{service}: {key} must use Docker DNS '{hostname}:5432'")
        else:
            print(f"{service}: {key} Docker DNS OK")
    except Exception:
        block(f"{service}: {key} is invalid")


def require_kafka(service, services):
    env = services.get(service, {}).get("environment") or {}
    raw = env.get("KAFKA_BOOTSTRAP_SERVERS") if isinstance(env, dict) else None
    if raw != "kafka:9094":
        block(
            f"{service}: KAFKA_BOOTSTRAP_SERVERS must be kafka:9094 "
            "(localhost:9092 is host-only)"
        )
    else:
        print(f"{service}: Kafka Docker DNS OK")


def check_ports(services):
    published = 0
    for name, service in services.items():
        for port in service.get("ports") or []:
            if not isinstance(port, dict):
                block(f"{name}: unexpected Compose port definition")
                continue
            published += 1
            ip = port.get("host_ip") or "0.0.0.0"
            if ip not in ("127.0.0.1", "::1"):
                block(f"{name}: published port has a non-loopback bind")
    if published:
        print(f"Published port bindings examined: {published}")
        print("Compose published ports: all loopback" if not any(
            "port" in msg for msg in BLOCKERS
        ) else "Compose port bindings require review")


def check_frontend_and_secrets(services):
    env = services["auth_service"].get("environment") or {}
    frontend = env.get("TPU_FRONTEND_URL") or "https://tpu-metrics.duckdns.org"
    parsed = urlparse(frontend)
    if parsed.scheme != "https" or not parsed.hostname:
        block("Production TPU_FRONTEND_URL must be an HTTPS origin")
    else:
        print("Frontend origin: HTTPS")
    value = str(env.get("TPU_COOKIE_SECURE") or "true").lower()
    if value not in ("true", "1", "yes", "on"):
        block("TPU_COOKIE_SECURE must be true for HTTPS deployment")
    else:
        print("Secure session cookies: enabled")
    # Never print values or even their length.
    if not env.get("PROJECT_TOKEN_ENCRYPTION_KEY"):
        block("PROJECT_TOKEN_ENCRYPTION_KEY is missing")
    else:
        print("Project-token encryption key: configured (not validated)")
    if not env.get("TPU_CLIENT_ID") or not env.get("TPU_CLIENT_SECRET"):
        block("TPU OAuth client credentials are missing")
    else:
        print("TPU OAuth client credentials: configured (not validated)")

    allowed = str(env.get("PROJECT_API_ALLOWED_HOSTS") or "").strip()
    if not allowed:
        block(
            "PROJECT_API_ALLOWED_HOSTS is empty: arbitrary public provider "
            "domains and DNS-rebinding risks require egress/SSRF review"
        )
    else:
        note(
            "Provider allowlist exists, but the current code also permits arbitrary "
            "public DNS; this is NOT a complete SSRF safeguard"
        )


def main():
    print("=== DOCKER COMPOSE / PRODUCTION READINESS AUDIT ===")
    print("Mode: read-only, no containers started, no secrets displayed")
    config = compose_config()
    missing = sorted(EXPECTED_SERVICES - set(config))
    extra = sorted(set(config) - EXPECTED_SERVICES)
    if missing:
        block("Missing Compose services: " + ", ".join(missing))
    if extra:
        note("Additional Compose services found (review separately)")
    print("Services found:", len(config))
    check_ports(config)
    if "auth_service" in config:
        for key, host in DB_URLS.items():
            container_database_url(config, key, host)
        check_frontend_and_secrets(config)
    for name, key, host in (
        ("gitlab_service", "GITLAB_DATABASE_URL", "gitlab_db"),
        ("redmine_service", "REDMINE_DATABASE_URL", "redmine_db"),
        ("analytics_service", "ANALYTICS_DATABASE_URL", "analytics_db"),
        ("analytics_consumer", "ANALYTICS_DATABASE_URL", "analytics_db"),
    ):
        if name in config:
            app_database(name, config, key, host)
    for name in ("analytics_consumer",):
        if name in config:
            require_kafka(name, config)

    if "project_sync_worker" in config:
        app_database("project_sync_worker", config, "AUTH_DATABASE_URL", "auth_db")
        app_database("project_sync_worker", config, "ANALYTICS_DATABASE_URL", "analytics_db")
        worker = config["project_sync_worker"]
        replicas = (worker.get("deploy") or {}).get("replicas", 1)
        if replicas != 1:
            block("Run exactly one project_sync_worker replica")
        else:
            print("Project sync worker: single replica in Compose definition")

    redmine_env = config.get("redmine_service", {}).get("environment") or {}
    raw_redmine = redmine_env.get("REDMINE_URL") if isinstance(redmine_env, dict) else None
    if raw_redmine and urlparse(raw_redmine).hostname in ("localhost", "127.0.0.1"):
        block("redmine_service points to local test Redmine; never use that in Cloud.ru")

    note("Cloud reverse proxy/TLS, TPU OAuth callbacks and live browser flow not validated here")
    note("DNS rebinding/SSRF must be addressed with network egress controls before deployment")
    note("Do not deploy the local test Redmine or copy Windows .env to Cloud.ru")
    print("=== AUDIT RESULT ===")
    print("Blockers:", len(BLOCKERS))
    print("Notes:", len(NOTES))
    if BLOCKERS:
        print("PRODUCTION READINESS: BLOCKED (expected for local development .env)")
    else:
        print("PRODUCTION READINESS: CONFIG CHECK PASSED; runtime/security review still required")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never forward subprocess output or connection URLs to the console.
        print("AUDIT STOPPED:", str(exc))
        raise SystemExit(1) from None

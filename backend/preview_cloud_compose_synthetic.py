"""Synthetic Cloud Compose dry-run: no real secrets, services or containers changed."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import dotenv_values
from sqlalchemy.engine import URL
from preflight_cloud_env import DATABASES, TEMPLATE, validate

ROOT = Path(__file__).resolve().parent
APP_SERVICES = (
    "auth_service", "gitlab_service", "redmine_service",
    "analytics_service", "analytics_consumer", "project_sync_worker",
)
ALL_SERVICES = set(APP_SERVICES) | {
    "auth_db", "gitlab_db", "redmine_db", "analytics_db", "kafka",
}
ENV_SWITCH = "env_file: " + chr(36) + "{TPU_SERVICE_ENV_FILE:-.env}"


def synthetic_values():
    values = dict(dotenv_values(TEMPLATE, interpolate=False))
    for prefix, host, user in DATABASES:
        password = "synthetic-only-" + prefix.lower()
        values[prefix + "_DB_PASSWORD"] = password
        values[prefix + "_DATABASE_URL"] = URL.create(
            "postgresql+psycopg2", username=user, password=password,
            host=host, port=5432, database=host,
        ).render_as_string(hide_password=False)
    values.update({
        "TPU_CLIENT_ID": "synthetic-client",
        "TPU_CLIENT_SECRET": "synthetic-client-secret",
        "TPU_API_KEY": "synthetic-api-key",
        "TPU_REDIRECT_URI": "https://tpu-metrics.duckdns.org/auth/tpu/callback",
        "TPU_FRONTEND_URL": "https://tpu-metrics.duckdns.org",
        "TPU_COOKIE_SECURE": "true",
        "PROJECT_TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode("ascii"),
        "PROJECT_API_ALLOWED_HOSTS": "gitlab.com",
        "KAFKA_BOOTSTRAP_SERVERS": "kafka:9094",
        "REDMINE_URL": "",
        "REDMINE_API_KEY": "",
        "GITLAB_URL": "https://gitlab.com",
        "GITLAB_ACCESS_TOKEN": "",
        "PROJECT_GITLAB_API_BASE": "",
    })
    if validate(values):
        raise RuntimeError("Synthetic cloud settings do not validate")
    return values


def check_service_selector():
    source = (ROOT / "compose.services.yml").read_text(encoding="utf-8")
    if source.count(ENV_SWITCH) != len(APP_SERVICES):
        raise RuntimeError("Every app service must select the intended env file")
    if "env_file: .env" in source:
        raise RuntimeError("Unconditional .env remains")


def docker_compose_config(values, env_file):
    if not env_file.is_absolute():
        raise RuntimeError("Synthetic env file must be an absolute path")
    args = [
        "docker", "compose", "-f", str(ROOT / "docker-compose.yml"),
        "-f", str(ROOT / "compose.services.yml"),
        "--env-file", str(env_file), "config", "--format", "json",
    ]
    environment = os.environ.copy()
    environment.update(values)
    environment["TPU_SERVICE_ENV_FILE"] = str(env_file)
    try:
        result = subprocess.run(
            args, cwd=ROOT, env=environment, text=True, encoding="utf-8",
            errors="replace", capture_output=True, timeout=45, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("Docker Compose config preview unavailable") from None
    if result.returncode:
        raise RuntimeError("Docker Compose configuration rejected synthetic env")
    try:
        return json.loads(result.stdout)["services"]
    except (ValueError, KeyError, TypeError):
        raise RuntimeError("Invalid merged Compose JSON") from None


def check_merged(services, values):
    if set(services) != ALL_SERVICES:
        raise RuntimeError("Unexpected number or identity of Compose services")
    for name in APP_SERVICES:
        env = services[name].get("environment") or {}
        if not isinstance(env, dict):
            raise RuntimeError("Invalid application service env")
        for key, expected in values.items():
            if env.get(key) != expected:
                raise RuntimeError("App service env differs from synthetic input: " + key)
        if env.get("REDMINE_URL"):
            raise RuntimeError("Test Redmine unexpectedly enabled")
    for prefix, hostname, _ in DATABASES:
        db_env = services[hostname].get("environment") or {}
        if db_env.get("POSTGRES_PASSWORD") != values[prefix + "_DB_PASSWORD"]:
            raise RuntimeError("DB password interpolation mismatch")
    for service in services.values():
        for port in service.get("ports") or []:
            if not isinstance(port, dict) or port.get("host_ip") not in ("127.0.0.1", "::1"):
                raise RuntimeError("Unsafe Docker port binding")
    replicas = (services["project_sync_worker"].get("deploy") or {}).get("replicas", 1)
    if replicas != 1:
        raise RuntimeError("Worker must have one replica")


def main():
    print("=== SYNTHETIC CLOUD COMPOSE CONFIG PREVIEW ===", flush=True)
    print("No Cloud.ru access, real secrets, or containers started", flush=True)
    check_service_selector()
    values = synthetic_values()
    with tempfile.TemporaryDirectory(prefix="tpu-cloud-synthetic-") as tmp:
        path = Path(tmp) / "synthetic.env"
        with path.open("x", encoding="utf-8") as out:
            for key, value in values.items():
                if value is not None:
                    if "\n" in value or "\r" in value:
                        raise RuntimeError("Invalid synthetic fixture")
                    out.write(key + "=" + value + "\n")
        services = docker_compose_config(values, path)
        check_merged(services, values)
    print("Compose services:", len(services), flush=True)
    print("Six application env files: SYNTHETIC CLOUD VALUES CONFIRMED", flush=True)
    print("Database URLs/passwords: CONSISTENT; Kafka: INTERNAL DNS", flush=True)
    print("Published ports: LOOPBACK ONLY; worker: SINGLE REPLICA", flush=True)
    print("TEMPORARY SYNTHETIC ENV REMOVED", flush=True)
    print("NO CONTAINERS STARTED; EXISTING ENV FILES UNMODIFIED", flush=True)
    print("SYNTHETIC CLOUD COMPOSE PREVIEW PASSED", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError) as exc:
        print("SYNTHETIC CLOUD COMPOSE PREVIEW FAILED:", type(exc).__name__)
        raise SystemExit(1) from None

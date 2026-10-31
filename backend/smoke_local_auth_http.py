"""Local HTTP process smoke test for the real auth service entrypoint.

Binds 127.0.0.1:18765 temporarily. Starts no cloud workers, makes no
external API requests and does not create/modify any DB records.
"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent
PORT = 18765


def local_db(config, key, expected_port, expected_db, expected_user):
    value = config.get(key)
    if not value:
        raise RuntimeError(f"STOP: missing {key} from backend/.env")
    url = make_url(value)
    if not (
        url.drivername.startswith("postgresql")
        and url.host in {"127.0.0.1", "localhost"}
        and url.port == expected_port
        and url.database == expected_db
        and url.username == expected_user
    ):
        raise RuntimeError(f"STOP: {key} must point to the local test setup")
    return value


def main():
    config = dotenv_values(ROOT / ".env")
    auth_db = local_db(config, "AUTH_DATABASE_URL", 5440, "auth_db", "auth_user")
    analytics_db = local_db(config, "ANALYTICS_DATABASE_URL",
                         5436, "analytics_db", "analytics_user")
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", PORT)) == 0:
            raise RuntimeError(f"STOP: local port {PORT} is already occupied")

    env = os.environ.copy()
    env["AUTH_DATABASE_URL"] = auth_db
    env["ANALYTICS_DATABASE_URL"] = analytics_db
    env["PYTHONPATH"] = str(ROOT)
    env["TPU_FRONTEND_URL"] = "https://tpu-metrics.duckdns.org"
    env["TPU_COOKIE_SECURE"] = "true"

    print("=== LOCAL HTTP SERVICE SMOKE ===")
    print("Binding: 127.0.0.1:" + str(PORT))
    print("Database mode: LOCAL; no credentials printed")
    command = [
        sys.executable, "-m", "uvicorn", "auth_service.app.main:app",
        "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "error",
    ]
    server = subprocess.Popen(
        command, cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(
            base_url=f"http://127.0.0.1:{PORT}", timeout=1.5,
            follow_redirects=False, trust_env=False,
        ) as client:
            ready = False
            for _ in range(40):
                if server.poll() is not None:
                    raise RuntimeError("Local auth_service failed to start")
                try:
                    response = client.get("/health")
                    if response.status_code == 200:
                        ready = True
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.2)
            if not ready:
                raise RuntimeError("Local auth_service did not become ready")

            health = client.get("/health")
            print("GET /health:", health.status_code)
            assert health.json() == {"status": "ok", "service": "auth_service"}

            schema = client.get("/openapi.json")
            print("GET /openapi.json:", schema.status_code)
            assert schema.status_code == 200
            assert "/api/projects/{project_id}/dashboard" in schema.json()["paths"]
            assert "/api/projects/{project_id}/sync-status" in schema.json()["paths"]

            denied = client.get("/api/projects")
            print("GET /api/projects (no cookie):", denied.status_code)
            assert denied.status_code == 401
            print("LOCAL HTTP SERVICE SMOKE PASSED")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
        print("LOCAL HTTP PROCESS STOPPED")


if __name__ == "__main__":
    main()

"""Restore rehearsal for 5 Cloud.ru DB backups in an ISOLATED LOCAL Docker container.

Run from Windows backend/: python rehearse_cloud_db_restore.py
Never connects to Cloud.ru, runs against remote Docker, or modifies local
project DB containers. Requires a cached postgres:16 image on Docker Desktop.
A randomly named --rm container gets --network none, no ports and no bind
mounts; its anonymous PGDATA volume is deleted on completion.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
import sys
import tarfile
import time
from pathlib import Path

BACKUP_DIR = (
    Path.home() / "tpu-metrics-db-backups" / "cloudru" / "20261031_064618"
)
ARCHIVES = {
    "backend-auth_db-1.dump": (
        "1677a5df3a533e7ddde02b1ba4e53ad8c4fa329c5cd6604db5c888c6b11f6289",
        "restore_auth",
    ),
    "backend-analytics_db-1.dump": (
        "bccb70569275edadae3cde3afbbb82f2fe8f0b8ae9d9a5c0fb2262291a2f3be5",
        "restore_analytics",
    ),
    "backend-gitlab_db-1.dump": (
        "fcd43b6d11585779b42bd077f2775c33cbf6c256f09f06aefb8d73044a137aea",
        "restore_gitlab",
    ),
    "backend-redmine_db-1.dump": (
        "649d9ee17eb6c51d687eecd01ec470347e299857ec6192fa0aff8482e249238d",
        "restore_redmine",
    ),
    "redmine-test-db-1.dump": (
        "8f66e7907b52047653bcc71a6b339aa9d30291766cd2c7b8fe3f05149e6f98d2",
        "restore_redmine_test",
    ),
}


def command(args, timeout=35):
    """Capture output to avoid displaying Docker paths, SQL or environment."""
    try:
        return subprocess.run(
            args, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Local Docker command unavailable or timed out") from exc


def require_success(args, label, timeout=35):
    result = command(args, timeout=timeout)
    if result.returncode:
        raise RuntimeError(label + " failed (details suppressed)")
    return result.stdout.strip()


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archives():
    if not BACKUP_DIR.is_dir():
        raise RuntimeError("Backups not found in expected Windows folder")
    for filename, (expected_hash, _) in ARCHIVES.items():
        path = BACKUP_DIR / filename
        if not path.is_file():
            raise RuntimeError("Missing archive: " + filename)
        if file_hash(path) != expected_hash:
            raise RuntimeError("SHA256 mismatch: " + filename)
        print("SHA256 VERIFIED:", filename, flush=True)
    files_tar = BACKUP_DIR / "redmine-test-files.tar"
    if files_tar.exists():
        if not files_tar.is_file():
            raise RuntimeError("Redmine attachment archive is not a file")
        try:
            with tarfile.open(files_tar, "r:") as archive:
                count = 0
                for member in archive:
                    if member.isfile():
                        count += 1
                        stream = archive.extractfile(member)
                        if stream is None:
                            raise RuntimeError("Cannot read Redmine file archive")
                        with stream:
                            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                                pass
            print("REDMINE FILE TAR READABLE; FILE COUNT:", count, flush=True)
            print("REDMINE FILE TAR LOCAL SHA256:", file_hash(files_tar), flush=True)
            print("Compare this SHA256 with the SERVER archive before release", flush=True)
        except (OSError, ValueError, tarfile.TarError) as exc:
            raise RuntimeError("Redmine attachment tar unreadable") from exc
    else:
        print("REDMINE ATTACHMENT BACKUP: NOT FOUND ON WINDOWS", flush=True)
        print("Complete the separate Redmine files backup before release", flush=True)


def assert_local_docker():
    if os.name != "nt":
        raise RuntimeError("STOP: restore rehearsal is restricted to Windows")
    for key in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY",
                "DOCKER_CERT_PATH"):
        if os.environ.get(key):
            raise RuntimeError("STOP: Docker override detected: " + key)
    context = require_success(["docker", "context", "show"], "Docker context")
    endpoint = require_success(
        ["docker", "context", "inspect", context,
         "--format", "{{.Endpoints.docker.Host}}"],
        "Docker endpoint",
    )
    if not endpoint.startswith("npipe:////./pipe/"):
        raise RuntimeError("STOP: Docker endpoint is not the local Windows named pipe")
    if command(["docker", "image", "inspect", "postgres:16"]).returncode:
        raise RuntimeError("STOP: postgres:16 not cached locally; no image pull attempted")
    print("LOCAL DOCKER DESKTOP PIPE: VERIFIED", flush=True)
    print("POSTGRES:16 IMAGE: ALREADY CACHED", flush=True)


def restore_rehearsal():
    name = "tpu-restore-check-" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    started = False
    passed = False
    try:
        require_success(
            ["docker", "run", "--rm", "--detach", "--network", "none",
             "--name", name,
             "--env", "POSTGRES_PASSWORD=" + password,
             "postgres:16"],
            "Temporary isolated PostgreSQL startup", timeout=60,
        )
        started = True
        print("ISOLATED POSTGRES CONTAINER STARTED (NO NETWORK/PORTS)", flush=True)
        for attempt in range(45):
            ready = command(
                ["docker", "exec", name, "pg_isready",
                 "-U", "postgres", "-d", "postgres"], timeout=8
            )
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise RuntimeError("Temporary PostgreSQL did not become ready")

        for filename, (_, database) in ARCHIVES.items():
            path = BACKUP_DIR / filename
            require_success(
                ["docker", "cp", str(path), name + ":/tmp/" + filename],
                "Copy archive into isolated container", timeout=40,
            )
            require_success(
                ["docker", "exec", name, "createdb", "-U", "postgres", database],
                "Create temporary test database",
            )
            require_success(
                ["docker", "exec", name, "pg_restore", "--exit-on-error",
                 "--no-owner", "--no-acl", "-U", "postgres",
                 "-d", database, "/tmp/" + filename],
                "Restore " + filename, timeout=150,
            )
            count = require_success(
                ["docker", "exec", name, "psql", "-X", "-w", "-U", "postgres",
                 "-d", database, "-Atqc",
                 "SELECT count(*) FROM pg_tables WHERE schemaname = 'public'"],
                "Verify restored schema",
            )
            if not count.isdigit() or int(count) == 0:
                raise RuntimeError("Restored public tables missing: " + filename)
            print("RESTORE VERIFIED:", filename, "| public tables:", count, flush=True)
        passed = True
    finally:
        if started:
            cleanup = command(["docker", "rm", "--force", name], timeout=45)
            if cleanup.returncode:
                raise RuntimeError(
                    "STOP: temporary container cleanup not confirmed; "
                    "inspect ONLY container " + name
                )
            print("TEMPORARY RESTORE CONTAINER REMOVED", flush=True)
        if passed:
            print("ALL 5 DATABASE RESTORES PASSED", flush=True)
            print("NO CLOUD.RU OR EXISTING DATABASE CONTAINERS TOUCHED", flush=True)


def main():
    print("=== SAFE LOCAL RESTORE REHEARSAL ===", flush=True)
    verify_archives()
    assert_local_docker()
    restore_rehearsal()


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError) as exc:
        print("STOP:", str(exc), flush=True)
        raise SystemExit(1) from None

"""Non-destructive Cloud.ru inspection. Python standard library only.

Windows: python audit_cloud_server_readonly.py --public-only
On existing Linux server via SSH stdin: python3 - --server
No secrets, credentials, Docker inspect, docker exec, DB, migrations, writes,
container lifecycle actions, or OAuth login requests. The HTTP probes are
unauthenticated GETs to fixed paths on the known public TPU Metrics host.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

ORIGIN = "https://tpu-metrics.duckdns.org"
SENSITIVE_PORTS = frozenset({
    5432, 5434, 5435, 5436, 5440, 55440,
    8000, 8001, 8002, 8003, 8080, 9092, 9094,
})
EXPECTED_SERVICES = frozenset({
    "auth_service", "analytics_service", "gitlab_service", "redmine_service",
    "analytics_consumer", "project_sync_worker", "auth_db", "gitlab_db",
    "redmine_db", "analytics_db", "kafka",
})


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def run_command(argv, *, timeout=12):
    """Return only stdout on success; never display subprocess stderr."""
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8",
            timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def exposed_port(binding):
    """Classify a PUBLIC listen/bind, but never print any remote address."""
    match = re.search(r"(?P<addr>0\.0\.0\.0|\[::\]|::|\*):(?P<port>\d+)(?:->|$)", binding)
    if not match:
        return None
    port = int(match.group("port"))
    return port if port in SENSITIVE_PORTS else None


def public_probe(path):
    context = ssl.create_default_context()
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=context), NoRedirect()
    )
    request = urllib.request.Request(
        ORIGIN + path, method="GET",
        headers={"User-Agent": "TPU-Metrika-ReadOnly-Audit/1.0"},
    )
    try:
        with opener.open(request, timeout=8) as response:
            response.read(1)
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def inspect_public():
    print("=== PUBLIC HTTPS / ANONYMOUS API ===", flush=True)
    print("Origin: " + ORIGIN, flush=True)
    issues = []
    for path in ("/", "/api/projects", "/health"):
        status = public_probe(path)
        print(f"GET {path}: " + (str(status) if status is not None else "UNREACHABLE"), flush=True)
        if path == "/" and status not in (200, 301, 302, 307, 308):
            issues.append("Public HTTPS homepage unreachable or unexpected")
        if path == "/api/projects" and status != 401:
            issues.append("Anonymous project API is not confirmed to deny with HTTP 401")
        if status is None:
            issues.append("Verified TLS connection failed for " + path)
    print("TLS: verified using the system trust store for successful HTTPS requests", flush=True)
    print("No OAuth login performed; no cookies or credentials sent", flush=True)
    return sorted(set(issues))


def inspect_docker():
    print("\n=== DOCKER INVENTORY (NO INSPECT/EXEC) ===", flush=True)
    output = run_command([
        "docker", "ps", "--format",
        '{{json .}}',
    ])
    if output is None:
        print("Docker inventory: UNAVAILABLE (missing CLI or insufficient permission)", flush=True)
        return ["Docker inventory could not be read"]
    containers = 0
    compose_services = set()
    unsafe = set()
    for line in output.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            return ["Docker inventory returned unexpected format"]
        containers += 1
        # Never echo container name, ID, image, environment, labels or paths.
        label_text = str(row.get("Labels") or "")
        labels = dict(
            item.split("=", 1) for item in label_text.split(",")
            if "=" in item
        )
        service = labels.get("com.docker.compose.service")
        if service in EXPECTED_SERVICES:
            compose_services.add(service)
        for binding in str(row.get("Ports") or "").split(","):
            port = exposed_port(binding.strip())
            if port is not None:
                unsafe.add(port)
    print(f"Running Docker containers: {containers}", flush=True)
    print("Recognized Compose services: " +
          (", ".join(sorted(compose_services)) if compose_services else "NOT IDENTIFIED"),
          flush=True)
    print("Publicly published sensitive ports: " +
          (", ".join(str(p) for p in sorted(unsafe)) if unsafe else "none detected"),
          flush=True)
    issues = []
    if not containers:
        issues.append("No Docker containers running; check deployment architecture")
    if not compose_services:
        issues.append("Compose service identity not verified (could be a different deployment)")
    if unsafe:
        issues.append("Sensitive Docker ports are published on public interfaces")
    return issues


def inspect_listeners():
    print("\n=== HOST LISTENING SOCKETS (READ ONLY) ===", flush=True)
    output = run_command(["ss", "-ltnH"])
    if output is None:
        print("Host sockets: UNAVAILABLE (ss command or permission)", flush=True)
        return ["Host listening sockets could not be inspected"]
    unsafe = set()
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 4:
            port = exposed_port(fields[3])
            if port is not None:
                unsafe.add(port)
    print("Publicly bound sensitive host ports: " +
          (", ".join(str(p) for p in sorted(unsafe)) if unsafe else "none detected"),
          flush=True)
    return ["Sensitive services listen on public host interfaces"] if unsafe else []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--public-only", action="store_true")
    mode.add_argument("--server", action="store_true")
    args = parser.parse_args()
    if args.server and platform.system() != "Linux":
        raise SystemExit("STOP: --server must run on the Linux Cloud.ru host")
    print("=== CLOUD.RU READ-ONLY DEPLOYMENT AUDIT ===", flush=True)
    print("No service/container/database modifications; no secrets printed", flush=True)
    findings = inspect_public()
    if args.server:
        findings.extend(inspect_docker())
        findings.extend(inspect_listeners())
        print("\n=== UNVERIFIED DEPLOYMENT GATES ===", flush=True)
        print("Server environment key/DB integrity: NOT CHECKED", flush=True)
        print("Real TPU login and provider token access: NOT CHECKED", flush=True)
        print("Backup restoration, migration and rollback: NOT CHECKED", flush=True)
    else:
        print("Docker and sockets: NOT CHECKED (run --server via SSH)", flush=True)
    print("\n=== AUDIT CONCLUSION ===", flush=True)
    for finding in sorted(set(findings)):
        print("REVIEW:", finding, flush=True)
    print("Findings requiring review:", len(set(findings)), flush=True)
    print("PRODUCTION RELEASE: NOT AUTHORIZED BY THIS AUDIT", flush=True)
    if findings:
        raise SystemExit(1)
    print("READ-ONLY OBSERVATIONS PASSED (NOT DEPLOYMENT APPROVAL)", flush=True)


if __name__ == "__main__":
    main()

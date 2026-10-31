"""Read-only, secret-safe config checks for a future Cloud.ru deployment.

From backend/: python preflight_cloud_env.py --template
On server only: python preflight_cloud_env.py --env-file /secure/path/.env.cloud

No connection, deployment, migration or file writes. Never prints secret values.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import re
import stat
from pathlib import Path
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / ".env.cloud.example"
DATABASES = (
    ("AUTH", "auth_db", "auth_user"),
    ("GITLAB", "gitlab_db", "gitlab_user"),
    ("REDMINE", "redmine_db", "redmine_user"),
    ("ANALYTICS", "analytics_db", "analytics_user"),
)
REQUIRED = (
    "TPU_CLIENT_ID", "TPU_CLIENT_SECRET", "TPU_API_KEY",
    "TPU_REDIRECT_URI", "TPU_FRONTEND_URL", "TPU_COOKIE_SECURE",
    "PROJECT_TOKEN_ENCRYPTION_KEY", "PROJECT_API_ALLOWED_HOSTS",
    "KAFKA_BOOTSTRAP_SERVERS",
) + tuple(k for prefix, _, _ in DATABASES
          for k in (prefix + "_DB_PASSWORD", prefix + "_DATABASE_URL"))


def placeholder(value):
    return not value or value.strip().upper().startswith(
        ("REPLACE_", "CHANGEME", "YOUR_", "EXAMPLE_", "TODO_")
    )


def load(path):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {}, ["File could not be read"]
    errors = []
    seen = set()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"^(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=", line)
        if not match:
            errors.append("Unsupported environment file syntax")
            continue
        name = match.group(1)
        if name in seen:
            errors.append("Duplicate environment key")
        seen.add(name)
    try:
        values = dict(dotenv_values(path, interpolate=False))
    except Exception:
        return {}, ["Could not parse file"]
    return values, errors


def public_host(host):
    if not host or not re.fullmatch(r"[A-Za-z0-9.-]{1,253}", host):
        return False
    host = host.lower()
    if (host.endswith(".") or "." not in host
            or host.endswith((".local", ".localhost", ".internal", ".invalid", ".test"))):
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return all(
        0 < len(label) <= 63 and not label.startswith("-")
        and not label.endswith("-") for label in host.split(".")
    )


def validate(values):
    problems = []
    for key in REQUIRED:
        if placeholder(values.get(key)):
            problems.append(f"{key}: missing or placeholder")
    for prefix, database, username in DATABASES:
        key = prefix + "_DATABASE_URL"
        try:
            url = make_url(values.get(key) or "")
            valid = (
                url.drivername in ("postgresql", "postgresql+psycopg2")
                and url.host == database and url.port == 5432
                and url.database == database and url.username == username
                and url.password == values.get(prefix + "_DB_PASSWORD")
                and not placeholder(url.password)
            )
        except Exception:
            valid = False
        if not valid:
            problems.append(f"{key}: invalid Docker DNS/port or credentials")

    front_text = values.get("TPU_FRONTEND_URL") or ""
    callback_text = values.get("TPU_REDIRECT_URI") or ""
    try:
        f = urlparse(front_text)
        c = urlparse(callback_text)
        origin_ok = (
            f.scheme == "https" and f.hostname == "tpu-metrics.duckdns.org"
            and f.port in (None, 443) and f.path in ("", "/")
            and not f.query and not f.fragment and not f.username
            and not f.password
        )
        callback_ok = (
            c.scheme == "https" and c.hostname == f.hostname
            and c.port in (None, 443) and c.path == "/auth/tpu/callback"
            and not c.query and not c.fragment and not c.username
            and not c.password
        )
    except ValueError:
        origin_ok = callback_ok = False
    if not origin_ok:
        problems.append("TPU_FRONTEND_URL: expected HTTPS application origin")
    if not callback_ok:
        problems.append("TPU_REDIRECT_URI: unexpected OAuth callback")
    if (values.get("TPU_COOKIE_SECURE") or "").lower() not in ("true", "1", "on", "yes"):
        problems.append("TPU_COOKIE_SECURE: must be enabled")

    token_key = values.get("PROJECT_TOKEN_ENCRYPTION_KEY")
    if not placeholder(token_key):
        try:
            cipher = Fernet(token_key.encode("ascii"))
            sample = b"preflight-check"
            if cipher.decrypt(cipher.encrypt(sample)) != sample:
                raise ValueError()
        except Exception:
            problems.append("PROJECT_TOKEN_ENCRYPTION_KEY: invalid Fernet key")
    allowed = [part.strip().lower() for part in
               (values.get("PROJECT_API_ALLOWED_HOSTS") or "").split(",")]
    if not allowed or not all(public_host(x) for x in allowed) or len(set(allowed)) != len(allowed):
        problems.append("PROJECT_API_ALLOWED_HOSTS: invalid or unsafe host")
    if values.get("KAFKA_BOOTSTRAP_SERVERS") != "kafka:9094":
        problems.append("KAFKA_BOOTSTRAP_SERVERS: must be kafka:9094")

    legacy_redmine = (values.get("REDMINE_URL") or "").strip()
    if legacy_redmine:
        try:
            u = urlparse(legacy_redmine)
            safe = (u.scheme == "https" and public_host(u.hostname)
                    and u.hostname in allowed and u.port in (None, 443)
                    and not u.username and not u.password
                    and not u.query and not u.fragment)
        except ValueError:
            safe = False
        if not safe:
            problems.append("REDMINE_URL: test/local or unapproved Redmine is forbidden")
    elif values.get("REDMINE_API_KEY"):
        problems.append("REDMINE_API_KEY: remove when REDMINE_URL is disabled")

    gitlab_url = (values.get("GITLAB_URL") or "https://gitlab.com").strip()
    try:
        u = urlparse(gitlab_url)
        valid = (u.scheme == "https" and public_host(u.hostname)
                 and (u.hostname == "gitlab.com" or u.hostname in allowed)
                 and u.port in (None, 443) and not u.username
                 and not u.password and not u.query and not u.fragment)
    except ValueError:
        valid = False
    if not valid:
        problems.append("GITLAB_URL: unapproved/insecure GitLab URL")

    if values.get("PROJECT_GITLAB_API_BASE"):
        problems.append("PROJECT_GITLAB_API_BASE: requires separate trusted-host review")
    if any("$" + "{" in (v or "") for v in values.values()):
        problems.append("Environment interpolation is not supported")
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--template", action="store_true")
    group.add_argument("--env-file", type=Path)
    args = parser.parse_args()

    if args.template:
        values, errors = load(TEMPLATE)
        if any(k not in values for k in REQUIRED):
            errors.append("Required template keys missing")
        example_secrets = (
            "PROJECT_TOKEN_ENCRYPTION_KEY", "TPU_CLIENT_SECRET",
            "TPU_CLIENT_ID", "TPU_API_KEY",
            "AUTH_DB_PASSWORD", "GITLAB_DB_PASSWORD",
            "REDMINE_DB_PASSWORD", "ANALYTICS_DB_PASSWORD",
        )
        if any(not placeholder(values.get(key)) for key in example_secrets):
            errors.append("Example secrets must all remain placeholders")
        if any("REPLACE_" not in (values.get(prefix + "_DATABASE_URL") or "")
               for prefix, _, _ in DATABASES):
            errors.append("Example database URLs may not embed real passwords")
        print("=== CLOUD SERVER CONFIG TEMPLATE (NO SECRETS) ===")
        for error in sorted(set(errors)):
            print("BLOCKER:", error)
        if errors:
            raise SystemExit(1)
        print("Required configuration keys: PRESENT")
        print("Sample secrets: PLACEHOLDERS ONLY")
        print("CLOUD ENV TEMPLATE PASSED")
        print("NO PRODUCTION CHANGES")
        return

    path = args.env_file.resolve()
    if path in ((ROOT / ".env").resolve(), TEMPLATE.resolve()):
        raise SystemExit("STOP: local Windows .env/example may not be used as cloud config")
    if not path.is_file():
        raise SystemExit("STOP: no private server environment file at supplied path")
    if os.name != "nt":
        try:
            permissions = stat.S_IMODE(path.stat().st_mode)
        except OSError:
            raise SystemExit("STOP: cannot verify file permissions")
        if permissions & 0o077:
            raise SystemExit("STOP: restrict environment file access with chmod 600")
    values, errors = load(path)
    errors.extend(validate(values))
    print("=== CLOUD ENV PREFLIGHT (NO SECRETS) ===")
    for error in sorted(set(errors)):
        print("BLOCKER:", error)
    if errors:
        print("CLOUD ENV PREFLIGHT BLOCKED")
        raise SystemExit(1)
    print("PostgreSQL and Kafka internal DNS: FORMAT VERIFIED")
    print("OAuth/HTTPS and Fernet configuration: FORMAT VERIFIED")
    print("CLOUD ENV PREFLIGHT PASSED")
    print("NETWORK, REVERSE PROXY AND REAL OAUTH STILL UNVERIFIED")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# Runs on the Cloud.ru VM. Called only after successful GitHub Actions CI.
# Requires staged Compose files and a privately managed runtime env.
set -euo pipefail
umask 077

if [[ $# -ne 4 ]]; then
  echo "usage: remote_deploy.sh <full-commit-sha> <immutable-image> <runtime-env> <redmine-env>" >&2
  exit 2
fi

sha="$1"
image="$2"
runtime_env="$3"
redmine_env="$4"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid commit SHA" >&2; exit 2; }
[[ "$image" == "ghcr.io/cheba0/project-productivity-backend:$sha" ]] || {
  echo "Image tag must match the exact commit SHA" >&2
  exit 2
}
[[ "$runtime_env" = /* && -f "$runtime_env" ]] || {
  echo "Cloud runtime env file not found" >&2; exit 2;
}
[[ "$redmine_env" = /* && -f "$redmine_env" ]] || {
  echo "Cloud legacy Redmine env file not found" >&2; exit 2;
}

release_root="$HOME/.tpu-metrics-release"
stage="$release_root/ci-cd/$sha"
[[ -d "$stage" ]] || { echo "Staged release missing" >&2; exit 2; }
cd "$stage"

export TPU_SERVICE_ENV_FILE="$runtime_env"
export TPU_REDMINE_SERVICE_ENV_FILE="$redmine_env"
export TPU_BACKEND_IMAGE="$image"

compose=(
  docker compose
  --project-name backend
  --env-file "$runtime_env"
  -f "$stage/docker-compose.yml"
  -f "$stage/compose.services.yml"
  -f "$stage/compose.cloud-redmine.yml"
  -f "$stage/compose.ghcr.yml"
)

echo "Validating compose configuration"
"${compose[@]}" config -q
docker network inspect backend_default >/dev/null

backup="$release_root/backup-ci-$(date -u +%Y%m%dT%H%M%SZ)-${sha:0:12}"
mkdir -m 700 "$backup"
echo "Backing up the four databases before migrations"
for spec in \
    "auth_db auth_user auth_db" \
    "gitlab_db gitlab_user gitlab_db" \
    "redmine_db redmine_user redmine_db" \
    "analytics_db analytics_user analytics_db"; do
  read -r service db_user db_name <<< "$spec"
  "${compose[@]}" exec -T "$service" pg_dump -U "$db_user" -d "$db_name" -Fc \
  </dev/null > "$backup/${db_name}.dump"
  test -s "$backup/${db_name}.dump"
done
(cd "$backup" && sha256sum ./*.dump > SHA256SUMS)
echo "Database archives and SHA256 sums saved in $backup"

echo "Pulling immutable backend image"
docker pull "$image"

echo "Applying reviewed Alembic migrations"
for service in auth_service gitlab_service redmine_service analytics_service; do
  docker run --rm \
    --network backend_default \
    --env-file "$runtime_env" \
    "$image" \
    python -m alembic -c "$service/alembic.ini" upgrade head
done

echo "Recreating application services only (database and Kafka containers unchanged)"
for service in gitlab_service analytics_service redmine_service auth_service \
               analytics_consumer project_sync_worker; do
  "${compose[@]}" up -d --no-deps --no-build --pull never "$service"
done

echo "Checking all four HTTP health endpoints"
for port in 8000 8001 8002 8003; do
  ok=0
  for attempt in {1..10}; do
    if curl --noproxy '*' --silent --fail --max-time 5 \
      "http://127.0.0.1:$port/health" >/dev/null; then
      ok=1
      break
    fi
    sleep 2
  done
  if [[ "$ok" != "1" ]]; then
    echo "HTTP health check failed on port $port; inspect containers and use backups" >&2
    exit 1
  fi
done

echo "DEPLOY OK: $sha"
echo "Backups: $backup"

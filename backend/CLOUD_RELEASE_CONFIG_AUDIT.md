# Cloud.ru: stage 2/4, read-only production configuration baseline

Local database restores already passed for all five backup archives. No
`main` merge or deployment is authorized. The host currently runs
10 services in the `backend` Compose project, plus two in
`redmine-test`. `project_sync_worker` has not been started.

Run from **Windows PowerShell** in `backend/`:

```powershell
git pull --ff-only origin feature/backend-cached-metrics-sync
$env:PYTHONPATH = (Get-Location).Path
.\\.venv\\Scripts\\python.exe -m unittest -v test_cloud_release_config_readonly
if ($LASTEXITCODE -ne 0) { throw "Config auditor tests failed" }

$sshKey = "$env:USERPROFILE\\.ssh\\cloudru_productivity"
$sshTarget = "user1@82.202.156.89"
Get-Content -Raw -Encoding UTF8 .\\audit_cloud_release_config_readonly.py |
    ssh -T -i "$sshKey" -o IdentitiesOnly=yes $sshTarget "python3 -"
```

The script reads the **running container** configuration with
`docker inspect --format '{{json .Config.Env}}'`, but **never prints
the original JSON, credentials, Docker paths, tokens or URLs**.
It classifies only known key presence, container DB DNS, secure cookie
flags and callback origin. It queries the current auth, analytics and
Redmine Alembic versions with fixed read-only SQL, and compares the
Redmine attachment tar SHA256 to the local Windows reported hash.
It also counts the files currently present in the Redmine attachment
directory, without printing filenames. No production files are written.

The checks deliberately report "NOT AT FEATURE MIGRATION" for older
revisions; **do not run migrations in response**. The planned migration
upgrade must be rehearsed on a staging copy after confirming real
server DB state and a tested rollback.

A match between the archive SHA256 and the Windows archive, together
with zero current Redmine attachments, closes the *archive consistency*
question only. It is not a full backup of the Redmine container, its
configuration, or any other uploads. No actual Redmine file restore is
done during this audit.

Important existing deployment blocker: `compose.services.yml`
explicitly uses `env_file: .env`. Providing a new environment file
to Docker Compose with only `--env-file` does not replace that
service-level env file. A reviewed merged override and staged
real-provider / TPU OAuth test remain required.

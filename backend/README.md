# ТПУ.Метрика — запуск backend и подключение реальных данных

Проект состоит из React frontend (`frontend/`, отдельный разработчик) и Python/FastAPI backend (`backend/`). **Frontend в этой backend-ветке не меняется.**

## Как проходят данные

1. Пользователь входит через ТПУ и создаёт проект запросом `POST /api/projects` с HTTPS-ссылками на проекты GitLab/Redmine и токенами. Источники независимы: можно подключить один или оба.
2. Backend проверяет, что адрес каждого источника — одобренный публичный HTTPS-хост, и **сохраняет токены только в зашифрованном виде** в `auth_db.projects`.
3. Сразу после ответа `201 Created` запускается первая синхронизация; отдельный `project_sync_worker` проверяет новые подключения каждые 10 секунд, повторяет неудачные попытки и обновляет существующие данные раз в 15 минут.
4. GitLab API v4 отдаёт коммиты и Merge Requests, Redmine REST API — задачи, их статусы и затраченное время. Запросы к внешним системам делает только backend, не браузер.
5. `auth_db.project_metric_snapshots` содержит актуальный снимок данных для вычисления аналитики и всех endpoint-ов дашборда. `analytics_db.project_source_snapshots` получает идемпотентную копию данных для дальнейших аналитических задач. Старые нормализованные таблицы `analytics_db` **не перезаписываются**.
6. Frontend получает готовую аналитику через `GET /api/projects/{id}/dashboard`, `/workload`, `/sprint-hours`, `/deadlines`, `/merge-requests` и др.

**Важно:** существующий модуль `analytics_service` для старых Kafka-событий и новые снимки источников — два независимых канала. Новый API дашборда вычисляет результаты из `auth_db`, а не из старого API `/analytics/projects`. Фронтендеру нужно использовать новые endpoint-ы.

## Локальный запуск (Windows PowerShell)

Нужны Docker Desktop с Compose V2, Git и Python 3.12 для локальных тестов. Команды ниже выполнять из `backend/`.

```powershell
git clone https://github.com/cheba0/project-productivity.git
cd project-productivity/backend
Copy-Item .env.example .env
```

Откройте `backend/.env` и **замените все** `REPLACE_...` (пароли, TPU OAuth). Строки `AUTH_DATABASE_URL`, `GITLAB_DATABASE_URL`, `REDMINE_DATABASE_URL`, `ANALYTICS_DATABASE_URL` должны содержать **те же пароли**, что соответствующие `*_DB_PASSWORD`. Внутри Docker используются `auth_db`, `gitlab_db`, `redmine_db`, `analytics_db`, а не `localhost`. Особые символы в паролях внутри URL необходимо URL-кодировать.

Создайте **один постоянный Fernet-ключ**, скопируйте его в `PROJECT_TOKEN_ENCRYPTION_KEY` файла `.env`; не добавляйте значение в GitHub:

```powershell
py -3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Если зависимости ещё не установлены, можно получить ключ с помощью:

```powershell
py -3 -m pip install cryptography
```

Для локального frontend по адресу `http://localhost:5173` задайте `TPU_FRONTEND_URL=http://localhost:5173` и `TPU_COOKIE_SECURE=false`. Для любого публичного HTTPS-сервера используйте **`TPU_COOKIE_SECURE=true`** и зарегистрированный HTTPS OAuth callback. Без реальных параметров TPU OAuth вход через ТПУ **не заработает**, хотя `/health` и тесты могут работать.

Поднимите инфраструктуру, соберите backend, затем **до запуска приложений** примените миграции:

```powershell
$composeArgs = @("--env-file",".env","-f","docker-compose.yml","-f","compose.services.yml")
docker compose @composeArgs up -d auth_db gitlab_db redmine_db analytics_db kafka
docker compose @composeArgs build auth_service

foreach ($service in @("auth_service","gitlab_service","redmine_service","analytics_service")) {
    docker compose @composeArgs run --rm --no-deps auth_service python -m alembic -c "$service/alembic.ini" upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Migration failed: $service" }
}

docker compose @composeArgs up -d --no-build
docker compose @composeArgs ps
curl.exe http://127.0.0.1:8000/health
```

По умолчанию API работают на `127.0.0.1:8000` (auth и проекты), `8001` (старый GitLab-сервис), `8002` (старый Redmine-сервис), `8003` (analytics). Сервисы PostgreSQL и Kafka также публикуют **только localhost**. Frontend разрабатывается и запускается отдельно (папка `frontend/`, `npm ci`, `npm run dev`).

Логи синхронизации:

```powershell
docker compose @composeArgs logs --tail=50 project_sync_worker
docker compose @composeArgs logs --tail=50 auth_service
```

## Подключение реального GitLab и Redmine

Форма создания проекта должна отправлять JSON в **`POST /api/projects`** с cookie-сессией ТПУ. Пример тела (не подставлять настоящие секреты в документацию):

```json
{
  "name": "Мой проект",
  "gitlab_url": "https://gitlab.com/my-group/my-repository",
  "gitlab_token": "GITLAB_READ_ONLY_TOKEN",
  "redmine_url": "https://redmine.example.org/projects/my-project",
  "redmine_token": "REDMINE_READ_ONLY_API_KEY",
  "sprint_weeks": 2,
  "start_date": "2026-11-01",
  "active_after_days": 3,
  "delayed_after_days": 7
}
```

Для GitLab используйте токен с минимальными правами чтения API (например, `read_api` при наличии доступа к проекту). Redmine API должен быть включён; ключ должен иметь доступ к указанному проекту. Не храните эти токены во frontend, localStorage или репозитории: передавайте только в HTTPS-запросе к backend. API никогда не возвращает исходные токены, только флаги `gitlab_token_configured` и `redmine_token_configured`.

**Ссылки имеют строгий формат:**
- GitLab: `https://gitlab.com/group/repository` (или доверенный свой GitLab-хост).
- Redmine: `https://redmine.example.org/projects/project-identifier`.
- Сервер должен иметь публичный HTTPS/DNS и быть доступным **со стороны backend**. `localhost`, внутренние IP, HTTP и неподтверждённые хосты запрещены.

При размещении своего GitLab/Redmine серверный администратор должен добавить **точный hostname** в `PROJECT_API_ALLOWED_HOSTS` (например, `gitlab.com,redmine.example.org`), обновить секретный env сервера и перезапустить соответствующие app-контейнеры. `gitlab.com` разрешён встроенной политикой. Это защита от SSRF, поэтому backend не принимает произвольные адреса из формы без предварительного разрешения.

При создании проекта URL проходят раннюю проверку; синхронизация с внешними API запускается **после сохранения**, без ожидания полной загрузки всех коммитов и задач в HTTP-запросе. Ошибка доступа/токена отобразится через `sync-status`, а не затеряется как нулевые метрики. Для явной предварительной проверки есть `POST /api/projects/integrations/verify` (тело: `service`, `url`, `token`; ответ: `connected`, `project_id`, `project_name`). Она не сохраняет токен.

## API для frontend-разработчика

Каждый запрос выполняется с `credentials: "include"` и действующей сессией TPU. Для POST/PATCH браузер отправляет `Origin` текущего frontend сайта; CSRF-проверка блокирует чужие источники.

| Метод | URL | Для чего |
| --- | --- | --- |
| POST | `/api/projects` | создать проект со ссылками и токенами, вернуть `201` и UUID |
| POST | `/api/projects/integrations/verify` | проверить доступ к внешнему проекту до сохранения |
| PATCH | `/api/projects/{id}` | добавить/обновить интеграции, повторно поставить на синхронизацию |
| GET | `/api/projects` | список и статусы карточек |
| GET | `/api/projects/{id}/sync-status` | `configured`, `state`, `providers`, `last_error`, `has_cached_data` |
| POST | `/api/projects/{id}/sync` | запросить ручную синхронизацию (только владелец) |
| GET | `/api/projects/{id}/dashboard` | общая аналитика: метрики, задачи, участники, графики |
| GET | `/api/projects/{id}/workload` | загруженность участников |
| GET | `/api/projects/{id}/merge-requests` | GitLab MR из кэша |
| GET | `/api/projects/{id}/sprint-hours` | план/факт часов |
| GET | `/api/projects/{id}/deadlines` | сроки задач |
| GET | `/api/projects/{id}/members/{member_id}/dashboard` | личные метрики |

После `201 Created` показывайте состояние загрузки, опрашивая `sync-status`; `ready` означает, что кэш можно читать. Пока данных нет, `GET /dashboard` может ответить `409` (`metrics_not_synced`) — это ожидаемо. При `error` отображайте `last_error` и кнопку повтора. Когда дата начала проекта не задана, дашборд по умолчанию показывает **последние 30 дней**, а график спринтов возвращает `available: false` до настройки даты начала.

**Ограничения:** данные GitLab и Redmine сами по себе не определяют соответствие задачи конкретному коммиту и не позволяют делать выводы о качестве кода по количеству коммитов. Для личных показателей требуется связать email разработчика и ID Redmine в профиле участника. Просмотр чужих проектов требует членства в проекте.

## CI/CD в GitHub Actions

Workflow `.github/workflows/backend-ci-cd.yml`:

1. Для Pull Request в `main` и push в `main` запускает offline-тесты, проверку Python-синтаксиса. Тестовые токены фиктивные, внешние провайдеры и рабочие базы не используются.
2. После успешных тестов на `main` собирает Docker-образ `linux/amd64`, публикует **неизменяемый тег по SHA коммита** в `ghcr.io/cheba0/project-productivity-backend:<full-sha>`.
3. Деплой Cloud.ru по умолчанию **отключён**, чтобы изменения не затрагивали рабочий сервер без настройки доступа. Его можно запустить вручную через `Actions → Backend CI/CD → Run workflow` на `main`. Позже для автоматического деплоя добавьте GitHub Actions Variable `BACKEND_AUTO_DEPLOY=true`.
4. Деплой использует GitHub Environment `production` (рекомендуются required reviewers), SSH с проверкой `known_hosts`, предварительный backup четырёх PostgreSQL БД и проверку SHA256, Alembic миграции, последовательное обновление только шести app-контейнеров и HTTP health-check. Kafka и БД **не пересоздаются**. Автоматического rollback БД нет — резервные копии сохраняются на сервере.

Настройте через **GitHub → Settings → Secrets and variables → Actions** следующие значения, не добавляя их в код:

| Тип | Имя | Значение |
| --- | --- | --- |
| Secret | `CLOUD_SSH_PRIVATE_KEY` | отдельный приватный ключ деплоя, без passphrase; публичная часть — в `authorized_keys` Cloud.ru |
| Secret | `CLOUD_SSH_KNOWN_HOSTS` | запись `known_hosts` с **проверенным** отпечатком SSH-ключа Cloud.ru |
| Variable | `CLOUD_SSH_HOST` | адрес Cloud.ru, например `82.202.156.89` |
| Variable | `CLOUD_SSH_USER` | пользователь SSH, например `user1` |
| Variable | `CLOUD_RUNTIME_ENV_PATH` | абсолютный путь к приватному production env, например `/home/user1/.tpu-metrics-release/cloud-release.env` |
| Variable | `CLOUD_REDMINE_ENV_PATH` | абсолютный путь к старому рабочему env Redmine (не теряем существующие параметры интеграции) |
| Variable | `BACKEND_AUTO_DEPLOY` | `true` — только после проверки CI, SSH, резервных копий и рабочей конфигурации |

Не нужно переносить API-токены из локального `.env` в GitHub Secrets для каждой новой интеграции: токены пользователей сохраняются через API в БД, зашифрованными с помощью постоянного серверного `PROJECT_TOKEN_ENCRYPTION_KEY`. Этот ключ **не менять при каждом деплое**.

### Перед первым CD на Cloud.ru

- Убедитесь, что действующий ключ Fernet и все параметры TPU OAuth, PostgreSQL, Kafka сохранены в `CLOUD_RUNTIME_ENV_PATH` с правами доступа только владельцу.
- Укажите реальный путь к старому Redmine env для `CLOUD_REDMINE_ENV_PATH`; иначе пайплайн правильно остановится, не отключая существующее подключение.
- На сервере должны быть Docker Compose с поддержкой `!override`/`!reset`, работающие `backend_default` и исходные persistent volumes.
- Отдельно согласуйте публичные HTTPS-хосты Redmine/GitLab; не добавляйте wildcard-сети.
- Проверьте через браузер настоящий вход TPU и устойчивость HTTPS-маршрута до Cloud.ru. Локальные `/health=200` не доказывают, что внешний HTTPS всегда доступен.
- При появлении нового Redmine-хоста измените server-only `PROJECT_API_ALLOWED_HOSTS`, не GitHub код.

## Тестирование

Для тестов без БД и внешних токенов (из каталога `backend/`, с установленными Python-зависимостями):

```powershell
python -m unittest -v test_provider_token_contracts test_connection_lifecycle test_mixed_provider_snapshot test_project_snapshot_selection test_dashboard_student_metrics test_dashboard_extras test_browser_security
```

Отдельный интеграционный тест с PostgreSQL `test_new_provider_api.py` **запускается только** на специально изолированной тестовой БД `127.0.0.1:55440/tpu_auth_test` с применёнными миграциями; не запускайте его на Cloud.ru или рабочей базе. Проверка реальных API (не mock) требует собственных токенов чтения и разрешённого публичного адреса; CI не хранит реальные токены.

Полные контракты: `PROJECT_METRICS_API.md`, `FIGMA_METRICS_BACKEND.md`, `SPRINT_AND_DEADLINES_API.md`, `PROVIDER_CONNECTIONS.md`.

# Logging and ELK Integration – Project Analysis

> **📚 For complete ELK stack architecture documentation, see [ELK_STACK_COMPLETE_ANALYSIS.md](./ELK_STACK_COMPLETE_ANALYSIS.md)**  
> **📋 For current status and troubleshooting, see [LOGGING_ELK_FINAL_CHECK.md](./LOGGING_ELK_FINAL_CHECK.md)**

## Status: ✅ Data Streams Enabled

The ELK stack is now using **Elasticsearch Data Streams** (not traditional indices). All Django logs are flowing to `logs-django-pt` data stream.

## 1. Basic log settings

### Where logging is configured

| Location | Purpose |
|----------|---------|
| **`config/settings/base.py`** | Base Django `LOGGING`: **console** handler; when `LOG_FILE_PATH` is set, a **file** handler (RotatingFileHandler, 10MB × 5 backups) is added. Format: `LEVEL|name|timestamp|message`. |
| **`config/settings/production.py`** | Production: ERROR to console; when `LOG_FILE_PATH` is set, same format to file for ELK. |
| **`config/celery.py`** | Celery: `MemoryLoggingFormatter` for console; when `LOG_FILE_PATH` is set, same file handler and format for Filebeat. |
| **`config/gunicorn/gunicorn.conf.py`** | Gunicorn: `HealthCheckFilter` on access_log to drop `/health` and `/auth-health`. Access/error logs go to stderr/stdout. |
| **`config/celery_healthcheck.py`** | `logging.basicConfig(level=logging.INFO)` for healthcheck script. |
| **`config/settings/utils.py`** | Uses `logging.getLogger(__name__)` for settings-related logging. |

**Summary:** Logs go to **console**; when `LOG_FILE_PATH` is set (e.g. in Docker), they also go to a **rotating file** (10MB × 5 backups) for Filebeat to ship to ELK.

**Log format (aligned with Logstash):** `LEVEL|LOGGER_NAME|TIMESTAMP|MESSAGE` (e.g. `INFO|apps.parcels.views|2025-02-02T12:34:56.123|Some message`). Used for both console and file.

---

## 2. Log streams (who produces logs)

Each of these runs as a separate process/container and has its own stdout/stderr stream:

| Stream / Service | How it runs | Log source |
|------------------|-------------|------------|
| **django** | `docker/local/django/start`: `runserver_plus` (local) or prod: `uvicorn` + `daphne` | Django `LOGGING` → console; Gunicorn (if used); uvicorn/daphne; management commands. |
| **celery** | `docker/local/celery/start`: `celery -A config worker ...` | Celery worker logs + `MemoryLoggingFormatter`, task_prerun memory logs, and any `logger.*` from app code in tasks. |
| **celerybeat** | `docker/local/celerybeat/start` | Beat scheduler logs; any logging from beat-related code. |
| **flower** | `docker/local/celery/flower_start` | Flower (Celery monitoring) stdout/stderr. |
| **nginx** | Production only | Nginx access/error logs (when used in front of django/react). |
| **react** | Production only (lata) | Frontend build/runtime logs. |
| **redis** | `redis-server ... --loglevel warning` | Redis logs (optional to ship; usually low volume). |

So the **distinct streams** you care about for “console logs” are: **django**, **celery**, **celerybeat**, **flower**, and optionally **nginx** and **react**.

---

## 3. Types of logs the app generates

### By logger name (Django `LOGGING` + root)

- **django.request** – HTTP request handling (base: DEBUG; prod: not overridden, so follows root ERROR in prod).
- **watchdog** – File watcher (e.g. runserver reload).
- **django.db.backends** – SQL (INFO in base).
- **werkzeug** – WSGI/dev server.
- **PIL** – Image handling.
- **boto / boto3 / botocore / s3transfer / urllib3 / nose** – Set to CRITICAL to reduce noise.
- **daphne** – ASGI server (production; ERROR in prod).
- **Root** – Everything else: all `logging.getLogger(__name__)` from apps and config.

### By application module (all go to root → console)

Logging is used in many apps; examples:

- **tenant_manager** – Tenant init, DB routing, WebSocket auth, migrations, Celery signals.
- **parcels** – Views (errors, ES, exports, WebSocket, validation).
- **logs** (app) – Views, utils, tasks (this is *application* “logs” feature, not Python logging config).
- **integrations, dashboard, manage_reports, notification, custom_auth, common, branded, container, cron_tasks, data_governance, harmonization, onboarding** – Views, utils, models, tasks, management commands.

### By level

- **DEBUG** – Local/base (e.g. django.request, watchdog, root).
- **INFO** – Tenant init, task received/sent, bootstrap, many business events.
- **WARNING** – Missing tenant, no tenant context, overflow/limits.
- **ERROR** – Invalid URLs, validation errors, auth failures, exceptions.
- **CRITICAL** – Only from third-party loggers (boto, etc.) when not silenced.

### By format

- **Base (local):** `LEVEL|YYYY-MM-DDTHH:MM:SS.mmm|message`
- **Production:** `LEVEL YYYY-MM-DDTHH:MM:SS.mmm 'funcName pathname "message"'`
- **Celery:** Custom format with `[timestamp] [level] [name] [Process Memory: ...] [Available RAM: ...] [Available Swap: ...] message`

So the **types** of logs are: **request/sql/watchdog**, **third-party (noisy ones suppressed)**, **application (per-module)** and **Celery (with memory metadata)**.

---

## 4. Pushing these logs to ELK (different cluster / server)

1. **File logging** – When `LOG_FILE_PATH` is set (e.g. in Docker), Django and Celery write to a rotating log file (10MB × 5 backups) in addition to console. Format: `LEVEL|name|timestamp|message`.
2. **Filebeat** – Lives in **this project**; runs in the same compose; reads the project dir (mounted at `/app`) and ships to Logstash.
3. **ELK** – **Lives on a different server/project** (docker-compose, logstash.conf, elasticsearch.yml, kibana.yml). Logstash Beats input on port **5044**; set `LOGSTASH_HOST` and `LOGSTASH_PORT` in this project so Filebeat can reach that server.

---

## 5. PT group and six Elasticsearch data streams

**Design:** One **group** named **pt** (Parcel Tracking). Six **services** produce logs → six **Elasticsearch data streams** (one per service). The 66 application loggers are **split by which service produced the log** (Django process → django stream, Celery process → celery stream, etc.).

| Concept | Where it belongs |
|--------|-------------------|
| Group | **pt** (single product) |
| Service (django, celery, …) | **Data stream** (e.g. `logs-django-pt`, `logs-celery-pt`) |
| App type (parcels, auth) | Field `app_module` |
| Logger name | Field `logger_name` |
| Framework vs app | Field `stream` (django, server, app, aws, …) |
| Severity | Field `log_level` |

**Six data streams (namespace pt, dataset = service):**

- `logs-django-pt` — Web app + management commands
- `logs-celery-pt` — Workers
- `logs-celerybeat-pt` — Scheduler
- `logs-flower-pt` — Celery monitoring
- `logs-nginx-pt` — Access + error (when nginx Filebeat sends here)
- `logs-react-pt` — Frontend (prod)

**Kibana:** Data view `logs-*-pt` (all PT services) or `logs-django-pt`, `logs-celery-pt`, etc. Query: `group:pt AND service:django AND app_module:parcels AND log_level:ERROR`.

**Reference Logstash config:** `docker/logstash/logstash.conf` in **this project** — **copy it to your ELK server** (e.g. `./logstash.conf` next to your ELK docker-compose). On the ELK server, ensure an index template with `data_stream: {}` exists for `logs-*-*` (e.g. from Fleet or created manually).

**✅ Data Streams Status**: The stack is now using Elasticsearch data streams. The index template `pt-logs` (pattern `logs-*-pt`) has been created and is working. See [ELK_STACK_COMPLETE_ANALYSIS.md](./ELK_STACK_COMPLETE_ANALYSIS.md) for complete details.

---

## 6. Filebeat service (this project, dev only)

### What is included

- **`docker/filebeat/filebeat.template.yml`** – **Single Filebeat** with **multiple inputs**: reads all PT log files (app.log, celery.log, celerybeat.log, flower.log) and adds **group: "pt"** and the **respective service** (django, celery, celerybeat, flower) per file. One output to Logstash; Logstash routes to the correct data stream (logs-django-pt, logs-celery-pt, etc.) using the `service` field.
- **`docker/filebeat/entrypoint.sh`** – Substitutes `LOGSTASH_HOST` and `LOGSTASH_PORT` and runs Filebeat.
- **`docker/filebeat/Dockerfile`** – Builds Filebeat 8.11.0 image.
- **`docker-compose.yml`** – Django writes to `apps/logs/app.log`. Filebeat mounts the project at `/app` and reads `/app/apps/logs/*.log`. Default `LOGSTASH_HOST=host.docker.internal` so Filebeat can reach your ELK stack on the host (Logstash Beats on 5044).

### How to run (dev + ELK on another server)

1. On the **ELK server**, start Elasticsearch, Kibana, Logstash (Beats on 5044). Use the **reference** `docker/logstash/logstash.conf` from this project (copy to the ELK project as `logstash.conf`).
2. In **this project**:  
   `docker compose -f docker-compose.yml up -d`  
   Filebeat will send to `host.docker.internal:5044` by default (or set `LOGSTASH_HOST` / `LOGSTASH_PORT` to your ELK server).
3. In Kibana (on the ELK server), create a **data view** for `logs-*-pt` (or `logs-django-pt`, etc.) to view PT logs.

### Log files (dev: 6 streams)

In **dev**, Django writes to **6 log files** in `apps/logs/` (one per stream): **django.log**, **server.log**, **system.log**, **aws.log**, **network.log**, **app.log**. base.py categorizes loggers into these streams. Filebeat has six inputs (one per file), all with `service: "django"` and `stream` set by file (django, server, system, aws, network, app). All events go to the **logs-django-pt** data stream.

### Log format and Logstash

Django/Celery logs use **LEVEL|LOGGER_NAME|TIMESTAMP|MESSAGE** (e.g. `INFO|apps.parcels.views|2025-02-02T12:34:56.123|message`). The reference `docker/logstash/logstash.conf` (copy to your ELK server) groks this and sets stream/app_module. Filebeat sends **group: "pt"** and **service** (django, celery, …) per input; Logstash writes to **logs-{service}-pt**; app_module, logger_name, stream, and log_level are fields inside each stream.

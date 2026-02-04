# Logging → Filebeat → Logstash → Elasticsearch: Final Check (dev only)

> **📚 For complete architecture documentation, see [ELK_STACK_COMPLETE_ANALYSIS.md](./ELK_STACK_COMPLETE_ANALYSIS.md)**

## Status: ✅ Production Ready (Django Service)

The ELK stack is **fully operational** with Elasticsearch data streams enabled. All Django logs are successfully flowing to `logs-django-pt` data stream and visible in Kibana.

## 1. Pipeline overview (dev)

```
Django (single service in dev)  →  writes to 6 log files in apps/logs/ (one per stream)
       ↓
  django.log, server.log, system.log, aws.log, network.log, app.log
       ↓
Docker: django and filebeat mount .:/app → both see apps/logs/
       ↓
Filebeat  →  reads all 6 files, adds group: pt, service: django, stream: <django|server|system|aws|network|app>
       ↓
Logstash  →  grok + stream/app_module, routes to logs-django-pt
       ↓
Elasticsearch  →  data stream logs-django-pt (all 6 streams as fields inside)
```

---

## 2. Six streams (dev: base.py)

| Stream   | Log file     | Loggers |
|----------|--------------|---------|
| **django**  | django.log   | django.request, django.db.backends |
| **server**  | server.log   | werkzeug |
| **system**  | system.log   | watchdog, PIL, nose |
| **aws**     | aws.log      | boto, boto3, botocore, s3transfer |
| **network** | network.log  | urllib3 |
| **app**     | app.log      | root (apps.*, config.*, asyncio, etc.) |

---

## 3. Current state (dev: Django only)

| Step | Status | Details |
|------|--------|--------|
| **Services → log files** | ✅ OK | Django writes to **6 files** in `apps/logs/`: django.log, server.log, system.log, aws.log, network.log, app.log (base.py: one handler per stream). |
| **Docker** | ✅ OK | django and filebeat mount `.:/app`; both see `apps/logs/*.log`. |
| **Filebeat** | ✅ OK | Six inputs (one per file), each adds `group: "pt"`, `service: "django"`, `stream: <stream>`. Dev-only; no celery/celerybeat/flower inputs. |
| **Logstash → Elasticsearch** | ✅ OK | Filter when `[group] == "pt"`, output to **logs-django-pt**. |

**Verdict for dev:** **Ready.** Django → 6 log files → Filebeat (service: django, stream per file) → Logstash → logs-django-pt.

---

## 3.1 Troubleshooting: logs in files but not in ELK

If `.log` files have recent lines but nothing appears in Kibana:

1. **Field location** — Filebeat often sends custom fields under `[fields]` (e.g. `[fields][group]`), not at the event root. The reference **logstash.conf** normalizes this: it copies `[fields][group]` → `[group]`, `[fields][service]` → `[service]`, and `[fields][stream]` → `[stream]` when missing at root. Ensure your ELK server uses that pipeline (copy from `docker/logstash/logstash.conf`).

2. **Data stream index template** — Elasticsearch needs an index template that allows data streams for `logs-*-pt`. If you’re on Elasticsearch 8.x, a built-in logs template may already apply. Otherwise, on the **ELK server** run:
   ```bash
   curl -X PUT "localhost:9200/_index_template/pt-logs" -H "Content-Type: application/json" -d @elasticsearch-index-template-pt-logs.json
   ```
   (Use the file `docker/logstash/elasticsearch-index-template-pt-logs.json` from this project, and add `-u user:password` if security is enabled. The template uses priority 150 so it overrides the built-in `logs` template, priority 100.)

3. **Connectivity** — From the **app** host: Filebeat must reach Logstash (e.g. `LOGSTASH_HOST=host.docker.internal` and `LOGSTASH_PORT=5044` when ELK runs on the host). From the **ELK** host: Logstash must reach Elasticsearch (`elasticsearch:9200` inside Docker, or the correct host/credentials). Check Filebeat logs (`docker logs filebeat`) and Logstash logs (`docker logs logstash`) for connection errors.

4. **Debug in Logstash** — In `logstash.conf`, uncomment the `else { stdout { codec => rubydebug } }` block in the output section, restart Logstash, and run `docker logs -f logstash`. You should see events; if they lack `group` or `service`, the normalization or Filebeat config is the next place to check.

---

## 3.2 Troubleshooting: Filebeat "EOF" / "client is not connected"

If Filebeat logs show **"Connection to ... 5044 established"** followed immediately by **"Failed to publish events caused by: EOF"** or **"client is not connected"**, the TCP handshake succeeds but the connection is closed when Filebeat sends data. Common causes:

1. **Logstash is not running** on the host (or ELK server) with a Beats input on port 5044.  
   - **Fix:** Start Logstash on the machine that `host.docker.internal` resolves to (your dev machine if ELK is local), with an `input { beats { port => 5044 } }` and the pipeline bound to `0.0.0.0` (default).  
   - If ELK runs in Docker on the same host, expose 5044: `ports: ["5044:5044"]` and ensure the Logstash container is up.

2. **Another process is using port 5044** and accepts TCP but does not speak the Beats protocol, so it closes the connection when data arrives.  
   - **Fix:** On the host, check what is listening: `netstat -an | findstr 5044` (Windows) or `ss -tlnp | grep 5044` (Linux). Stop any non-Logstash listener or change Logstash/Filebeat to use another port.

3. **IPv6 unreachable** — You may see `dial tcp [::]:5044: connect: network is unreachable`. Docker/Go can resolve `host.docker.internal` to IPv6 first; if IPv6 is not usable, connections can be flaky.  
   - **Fix:** Force IPv4 by pointing Filebeat at the host’s IPv4 address. On Windows, run `ipconfig` and use the host’s IPv4 (e.g. `192.168.x.x`) in `docker-compose.yml`:  
     `LOGSTASH_HOST=192.168.x.x` (or set in `.env`). Then restart: `docker compose up -d filebeat`.

4. **Logstash pipeline error** — Logstash accepts the connection but crashes or closes it (e.g. plugin error, OOM).  
   - **Fix:** Check Logstash logs on the ELK server (`docker logs logstash` or the service log). Fix any pipeline or plugin errors and restart Logstash.

**Quick check:** From the host, ensure something is listening on 5044 and that it is Logstash. Then restart Filebeat: `docker compose restart filebeat`.

---

## 3.3 Troubleshooting: No data streams in Kibana (template exists, but Data Streams tab empty)

Filebeat is acking events to Logstash, but you see the index template `pt-logs` (pattern `logs-*-pt`) in Kibana and **no data streams**. Work through the following on the **ELK server**.

### A. Confirm Logstash config on the ELK server

The pipeline that **writes to Elasticsearch** must use **data streams**, not a regular index. On the ELK server, your `logstash.conf` **output** section must look like this (and nothing else for PT logs):

```ruby
output {
  if [group] == "pt" and [service] {
    elasticsearch {
      hosts                  => ["elasticsearch:9200"]
      user                   => "logstash_writer"
      password               => "${LOGSTASH_WRITER_PASSWORD}"
      manage_template        => false

      data_stream            => true
      data_stream_type       => "logs"
      data_stream_dataset    => "%{[service]}"
      data_stream_namespace  => "pt"
    }
  }
  else {
    stdout { codec => rubydebug { metadata => true } }
  }
}
```

- If your output uses `index => "logstash-%{+YYYY.MM.dd}"` (or any fixed index) instead of `data_stream => true`, **no** `logs-*-pt` data stream will be created. Replace with the block above (copy from this project’s `docker/logstash/logstash.conf`).
- Ensure the **entire** pipeline (input + filter + output) matches the project’s `docker/logstash/logstash.conf` so that `[group]` and `[service]` are set (filter normalizes `[fields][group]` / `[fields][service]` to root).

### B. Logstash writer user and role (Elasticsearch security)

With `xpack.security.enabled: true`, the user `logstash_writer` must exist and have a role that allows **creating and writing to data streams** matching `logs-*-pt`.

1. **Create the role** (Kibana → Stack Management → Roles, or Dev Tools). Name: e.g. `logstash_writer_pt`. Index privileges:
   - **Index pattern:** `logs-*-pt` (or `logs-*` if you prefer).
   - **Privileges:** `create_index`, `create_doc`, `index`, `create`, `write`, `read` (read optional but useful for reindex/debug).

   Or via API (run on ELK host, adjust `-u elastic:Password`):

   ```bash
   curl -s -u elastic:Password -X POST "http://localhost:9200/_security/role/logstash_writer_pt" \
     -H "Content-Type: application/json" -d '{
      "indices": [
        {
          "names": ["logs-*-pt"],
          "privileges": ["create_index", "create_doc", "index", "create", "write", "read"]
        }
      ]
    }'
   ```

2. **Create the user** and assign the role (Kibana → Stack Management → Users, or API):

   ```bash
   curl -s -u elastic:Password -X POST "http://localhost:9200/_security/user/logstash_writer" \
     -H "Content-Type: application/json" -d '{
      "password" : "Password",
      "roles" : [ "logstash_writer_pt" ],
      "full_name" : "Logstash writer for PT"
    }'
   ```

   Use the same password you set in `.env` as `LOGSTASH_WRITER_PASSWORD`. If the user already exists, update the role assignment so it includes `logstash_writer_pt`.

3. **Restart Logstash** after any user/role change so it reconnects with the correct permissions.

### C. Logstash logs (Elasticsearch errors)

On the ELK server:

```bash
docker logs logstash 2>&1 | tail -200
```

Look for:

- **401 Unauthorized** → wrong user/password or user missing.
- **403 Forbidden** → `logstash_writer` role lacks `create_index` / `index` / `write` on `logs-*-pt`.
- **Connection refused** → Logstash cannot reach `elasticsearch:9200` (network/DNS).

If you see 403, fix the role as in B and restart Logstash.

### D. Password reaching Logstash

Logstash expands `${LOGSTASH_WRITER_PASSWORD}` from the **environment** at startup. Your ELK docker-compose must pass it:

```yaml
environment:
  LOGSTASH_WRITER_PASSWORD: ${LOGSTASH_WRITER_PASSWORD:?Set LOGSTASH_WRITER_PASSWORD in .env}
```

If this is missing or wrong, Logstash may fail to start or get 401. Check `docker logs logstash` from startup for config/plugin errors.

### E. Check whether any PT data streams exist

From the ELK host (or any host with access to Elasticsearch):

```bash
curl -s -u elastic:Password "http://localhost:9200/_data_stream?expand_wildcards=all"
```

If `logs-django-pt` (or any `logs-*-pt`) appears here, data **is** reaching Elasticsearch; the issue is only Kibana (e.g. data view or time range). If **no** `logs-*-pt` stream is listed, the problem is earlier: Logstash config (A), permissions (B), or Logstash errors (C/D).

### F. Quick checklist (ELK server)

| Check | Action |
|-------|--------|
| Logstash output uses data streams | Output block has `data_stream => true`, `data_stream_type => "logs"`, `data_stream_dataset => "%{[service]}"`, `data_stream_namespace => "pt"`. |
| Pipeline file | Same as this project’s `docker/logstash/logstash.conf` (input + filter + output). |
| Index template | `pt-logs` with pattern `logs-*-pt` and priority 150 (you already have this). |
| Role for logstash_writer | Role has index pattern `logs-*-pt` and privileges: `create_index`, `create_doc`, `index`, `create`, `write`. |
| User logstash_writer | Exists and has that role; password matches `LOGSTASH_WRITER_PASSWORD` in .env. |
| Logstash env | `LOGSTASH_WRITER_PASSWORD` set in docker-compose environment. |
| Logstash logs | No 401/403/5xx from Elasticsearch output. |

---

## 4. Gaps for full 6-service setup (Celery, Beat, Flower, Nginx, React)

| Service | Writes to file? | File path | Filebeat input | Ready? |
|---------|-----------------|-----------|----------------|-------|
| **Django** | ✅ Yes | `apps/logs/app.log` | ✅ app.log → service: django | ✅ |
| **Celery** | ⚠️ Same file as Django | Uses Django LOGGING → `app.log` | ✅ celery.log input exists but **file not used** | ❌ Celery writes to app.log |
| **Celery Beat** | ⚠️ Same file as Django | Uses Django LOGGING → `app.log` | ✅ celerybeat.log input exists but **file not used** | ❌ Beat writes to app.log |
| **Flower** | ❌ No file | Stdout only (flower_start has no file logging) | ✅ flower.log input exists but **file never created** | ❌ No file |
| **Nginx** | N/A (other server) | Usually access/error logs | Would need own Filebeat or input on ELK side | — |
| **React** | N/A (other server) | Usually stdout/build logs | Would need own Filebeat or input on ELK side | — |

So today:

- **Only `app.log`** is produced (by Django; if Celery/Beat run they also write to the same `app.log`).
- **Celery/Beat/Flower** do **not** write to `celery.log`, `celerybeat.log`, or `flower.log`. Filebeat inputs for those paths are correct but will see no data until those services write to separate files (or stdout is redirected to files).

---

## 4. What to fix for “all services → correct data streams”

1. **Celery & Celery Beat**  
   Configure them to write to their own log files (e.g. `apps/logs/celery.log`, `apps/logs/celerybeat.log`) instead of sharing `app.log`. Options:
   - Env (e.g. `LOG_FILE_NAME=celery.log`) and in base (or a small logging util) use that for the file handler when running as Celery/Beat, **or**
   - Separate Django settings/profile for Celery that set `LOGGING['handlers']['file']['filename']` to `apps/logs/celery.log` (and similarly for Beat).

2. **Flower**  
   Either:
   - Redirect stdout/stderr to a file (e.g. `flower.log`) in `flower_start` and have Filebeat read that file, **or**
   - Run a separate Filebeat/sidecar that reads Flower’s stdout (e.g. Docker log driver writing to a file).

3. **Docker**  
   No change needed for “reading logs into container”: all relevant services already mount the project (e.g. `.:/app`). Once Celery/Beat/Flower write to `apps/logs/*.log`, the same Filebeat container (same mount) will see those files.

4. **Filebeat**  
   Already has one input per service (app.log, celery.log, celerybeat.log, flower.log) with the right `group` and `service`. No change needed once the log files exist.

5. **Logstash**  
   Already routes by `[group]` and `[service]` to `logs-{service}-pt`. No change needed.

---

## 6. Production

- **config/settings/production.py** overrides `LOGGING` and only defines **console** handlers (no file handler). So in production, Django/Celery do **not** write to `app.log` (or any file) unless you add a file handler (e.g. when `LOG_FILE_PATH` or similar is set). If you want file-based ELK in production, add a file handler in production logging config and ensure the same `apps/logs/` path (or equivalent) is available and mounted for Filebeat.

---

## 7. Summary

| Question | Answer |
|----------|--------|
| **Ready for dev (6 streams, 6 files)?** | **Yes.** Django → django.log, server.log, system.log, aws.log, network.log, app.log → Filebeat (service: django, stream per file) → Logstash → logs-django-pt. |
| **Are all services’ loggers categorized into the 6 streams?** | **Yes.** base.py: django, server, system, aws, network, app (see §2). |
| **Does Filebeat catch all logs in dev?** | **Yes.** Six inputs for the six log files; dev-only (no celery/beat/flower). |
| **Does Logstash route to Elasticsearch correctly?** | **Yes.** group "pt" + service → logs-django-pt. |

**Bottom line:** Dev is ready with **6 stream files** and **one data stream** (logs-django-pt). For production or when adding Celery/Beat/Flower, add per-service log files and Filebeat inputs as in §5.

---

## 8. Related Documentation

- **[ELK_STACK_COMPLETE_ANALYSIS.md](./ELK_STACK_COMPLETE_ANALYSIS.md)**: Complete architecture documentation, data streams inventory, component analysis, and troubleshooting guide
- **[LOGGING_AND_ELK.md](./LOGGING_AND_ELK.md)**: Original logging configuration analysis

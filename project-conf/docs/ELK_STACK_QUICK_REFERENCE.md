# ELK Stack Quick Reference

> **📚 Full Documentation**: [ELK_STACK_COMPLETE_ANALYSIS.md](./ELK_STACK_COMPLETE_ANALYSIS.md)

## Current Status

✅ **Data Streams Enabled**: Using Elasticsearch data streams (not traditional indices)  
✅ **Django Service**: Fully operational, logs flowing to `logs-django-pt`  
✅ **6 Log Streams**: django, server, system, aws, network, app  
✅ **Kibana**: Data visible and queryable

## Data Streams

| Data Stream | Service | Status | Purpose |
|-------------|---------|--------|---------|
| `logs-django-pt` | django | ✅ Active | Web application, management commands |

**Planned**: `logs-celery-pt`, `logs-celerybeat-pt`, `logs-flower-pt`, `logs-nginx-pt`, `logs-react-pt`

## Log Streams (per Service)

| Stream | File | Loggers | Purpose |
|--------|------|---------|---------|
| **django** | `django.log` | `django.request`, `django.db.backends` | Framework logs |
| **server** | `server.log` | `werkzeug` | Dev server logs |
| **system** | `system.log` | `watchdog`, `PIL`, `nose` | System/library logs |
| **aws** | `aws.log` | `boto*`, `s3transfer` | AWS SDK logs |
| **network** | `network.log` | `urllib3` | HTTP client logs |
| **app** | `app.log` | `apps.*`, `config.*` | Application logs |

## Architecture Flow

```
Django → 6 log files → Filebeat → Logstash → Elasticsearch → Kibana
         (apps/logs/)   (6 inputs)  (grok)   (data stream)  (visualize)
```

## Key Files

| Component | File | Purpose |
|-----------|------|---------|
| Django Logging | `config/settings/base.py` | 6 handlers, formatters, logger routing |
| Filebeat Config | `docker/filebeat/filebeat.template.yml` | 6 inputs, metadata, output |
| Filebeat Dockerfile | `docker/filebeat/Dockerfile` | Image build |
| Filebeat Entrypoint | `docker/filebeat/entrypoint.sh` | Runtime config substitution |
| Logstash Config | `docker/logstash/logstash.conf` | Complete pipeline |
| ES Index Template | `docker/logstash/elasticsearch-index-template-pt-logs.json` | Data stream template |
| ES Security | `docker/logstash/elasticsearch-role-user-logstash-writer.json` | Role and user |
| Docker Compose | `docker-compose.yml` | Service orchestration |

## Log Format

```
LEVEL|LOGGER_NAME|TIMESTAMP|MESSAGE
```

**Example**: `INFO|apps.parcels.views|2025-02-02T12:34:56.123|Parcel created`

## Kibana Queries

```kql
# All Django logs
service:django

# Application errors
service:django AND stream:app AND log_level:ERROR

# Parcels module
service:django AND app_module:parcels

# Framework logs
service:django AND stream:django
```

## App Modules

| Module | Logger Pattern | Example |
|--------|---------------|---------|
| **parcels** | `apps.parcels.*` | `apps.parcels.views` |
| **auth** | `apps.custom_auth.*`, `apps.onboarding.*` | `apps.custom_auth.views` |
| **tenant** | `apps.tenant_manager.*` | `apps.tenant_manager.models` |
| **notification** | `apps.notification.*` | `apps.notification.tasks` |
| **reports** | `apps.manage_reports.*` | `apps.manage_reports.views` |
| **integrations** | `apps.integrations.*` | `apps.integrations.utils` |
| **dashboard** | `apps.dashboard.*` | `apps.dashboard.views` |
| **tasks** | `apps.cron_tasks.*`, `celery.*`, `*.tasks` | `apps.cron_tasks.tasks` |
| **common** | `apps.common.*` | `apps.common.utils` |
| **config** | `config.*` | `config.settings.base` |

## Troubleshooting

### No Logs in Kibana
1. Check Filebeat: `docker logs filebeat`
2. Check Logstash: `docker logs logstash`
3. Check Elasticsearch: `curl -u elastic:PASSWORD "http://localhost:9200/_data_stream/logs-*-pt"`
4. Check Kibana data view time range

### Filebeat Connection Issues
- Verify `LOGSTASH_HOST` and `LOGSTASH_PORT`
- Check Logstash is listening on 5044
- Force IPv4 if IPv6 issues: `LOGSTASH_HOST=192.168.x.x`

### Authentication Errors
- Verify `LOGSTASH_WRITER_PASSWORD` in Logstash environment
- Check user exists: `curl -u elastic:PASSWORD "http://localhost:9200/_security/user/logstash_writer"`
- Verify role privileges

## Commands

### Check Data Streams
```bash
curl -u elastic:PASSWORD "http://localhost:9200/_data_stream/logs-*-pt?expand_wildcards=all"
```

### Check Document Count
```bash
curl -u elastic:PASSWORD "http://localhost:9200/logs-django-pt/_count"
```

### View Filebeat Logs
```bash
docker logs filebeat | tail -100
```

### View Logstash Logs
```bash
docker logs logstash | tail -100
```

### Restart Services
```bash
docker compose restart filebeat
docker compose restart logstash  # On ELK server
```

## Next Steps

1. ✅ Django service - **Complete**
2. ⏳ Add Celery service logs
3. ⏳ Add Celerybeat service logs
4. ⏳ Add Flower service logs
5. ⏳ Production deployment (adjust template settings)
6. ⏳ Create Kibana dashboards
7. ⏳ Set up alerts for errors

---

**Last Updated**: 2025-02-02  
**See**: [ELK_STACK_COMPLETE_ANALYSIS.md](./ELK_STACK_COMPLETE_ANALYSIS.md) for complete documentation

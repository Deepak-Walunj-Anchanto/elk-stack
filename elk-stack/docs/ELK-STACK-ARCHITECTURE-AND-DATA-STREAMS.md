# ELK Stack Architecture and Data Streams Documentation

## Table of Contents
1. [Overview](#overview)
2. [Data Streams Created](#data-streams-created)
3. [Architecture Overview](#architecture-overview)
4. [How the ELK Stack Works](#how-the-elk-stack-works)
5. [Data Stream Creation Process](#data-stream-creation-process)
6. [Log Processing Pipeline](#log-processing-pipeline)
7. [Security Architecture](#security-architecture)
8. [Configuration Files](#configuration-files)
9. [Querying in Kibana](#querying-in-kibana)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This ELK (Elasticsearch, Logstash, Kibana) stack is configured to collect, process, and visualize logs from a **Parcel Tracking (PT)** application. The stack uses **Elasticsearch Data Streams** (introduced in Elasticsearch 7.9+) for time-series log data, which provides better performance, automatic index management, and simplified lifecycle policies compared to traditional indices.

### Key Features
- **6 Data Streams** for different services in the PT application
- **Automatic log categorization** into streams (django, server, aws, network, system, app, unknown)
- **Application module classification** for app logs (auth, parcels, tenant, notification, etc.)
- **Secure authentication** with X-Pack security
- **Docker-based deployment** for easy setup and management

---

## Data Streams Created

### Summary
**Total Data Streams: 6**

All data streams follow the naming convention: `logs-{service}-pt` (type-dataset-namespace)

| Data Stream Name | Service | Purpose | Log Source |
|-----------------|---------|---------|------------|
| `logs-django-pt` | Django | Backend API logs | Django application server |
| `logs-celery-pt` | Celery | Background task logs | Celery workers |
| `logs-celerybeat-pt` | Celerybeat | Scheduled task logs | Celerybeat scheduler |
| `logs-flower-pt` | Flower | Celery monitoring logs | Flower monitoring tool |
| `logs-nginx-pt` | Nginx | Web server logs | Nginx reverse proxy |
| `logs-react-pt` | React | Frontend logs | React frontend application |

### Data Stream Structure

Each data stream has the following structure:
- **Type**: `logs` (fixed)
- **Dataset**: Service name (django, celery, celerybeat, flower, nginx, react)
- **Namespace**: `pt` (Parcel Tracking group)

**Example**: `logs-django-pt` = `logs` (type) + `django` (dataset) + `pt` (namespace)

---

## Architecture Overview

### Component Diagram

```
┌─────────────┐
│  PT App     │
│  Services   │
│             │
│  Django     │──┐
│  Celery     │  │
│  Celerybeat │  │
│  Flower     │  │  Filebeat
│  Nginx      │  │  (on app server)
│  React      │──┘
└─────────────┘
      │
      │ (Beats protocol on port 5044)
      ▼
┌─────────────┐
│  Logstash   │
│  Port: 5044 │
│             │
│  - Parse    │
│  - Filter   │
│  - Enrich   │
└─────────────┘
      │
      │ (HTTP/REST API)
      ▼
┌─────────────┐
│Elasticsearch│
│  Port: 9200 │
│             │
│  Data       │
│  Streams    │
└─────────────┘
      │
      │ (HTTP/REST API)
      ▼
┌─────────────┐
│   Kibana    │
│  Port: 5601 │
│             │
│  - Search   │
│  - Visualize│
│  - Dashboard│
└─────────────┘
```

### Network Configuration

- **Docker Network**: `elk-net` (bridge network)
- **Subnet**: `172.19.1.0/24`
- **Service Discovery**: Services communicate using Docker service names (elasticsearch, kibana, logstash)

---

## How the ELK Stack Works

### End-to-End Flow

1. **Log Generation**
   - PT application services (Django, Celery, etc.) generate logs in format: `LEVEL|LOGGER_NAME|TIMESTAMP|MESSAGE`
   - Logs are written to files or stdout/stderr

2. **Log Collection (Filebeat)**
   - Filebeat (running on the application server) collects logs from configured sources
   - Filebeat adds metadata:
     - `group`: "pt" (identifies the application group)
     - `service`: django, celery, celerybeat, flower, nginx, or react (identifies the service)
   - Filebeat sends logs to Logstash using the **Beats protocol** on port 5044

3. **Log Processing (Logstash)**
   - Logstash receives logs on port 5044 (Beats input)
   - **Filter Stage**:
     - Parses log format using Grok: `LEVEL|LOGGER_NAME|TIMESTAMP|MESSAGE`
     - Categorizes logs into streams based on `logger_name`:
       - **django**: Django framework logs (`django.*`)
       - **server**: Server logs (`werkzeug`)
       - **aws**: AWS SDK logs (`boto*`, `s3transfer`)
       - **network**: Network logs (`urllib3`)
       - **system**: System logs (`asyncio`, `PIL`, `root`)
       - **app**: Application logs (`apps.*`, `config.*`)
       - **unknown**: Unmatched loggers
     - For app stream, extracts `app_module`:
       - auth, parcels, tenant, notification, reports, integrations, dashboard, data_governance, branded, container, harmonization, logs, tasks, common, config
     - Sets data stream metadata:
       - `[data_stream][type]`: "logs"
       - `[data_stream][namespace]`: "pt"
       - `[data_stream][dataset]`: service name (from Filebeat)
     - Normalizes `@timestamp` from parsed log timestamp

4. **Data Storage (Elasticsearch)**
   - Logstash outputs to Elasticsearch using `data_stream => true`
   - Elasticsearch automatically creates data streams based on metadata:
     - Pattern: `{type}-{dataset}-{namespace}`
     - Example: `logs-django-pt`
   - Index template (`logs-*-pt`) defines field mappings and settings
   - Data is stored in backing indices (automatically managed by Elasticsearch)

5. **Visualization (Kibana)**
   - Create data views in Kibana:
     - `logs-*-pt` (all PT services)
     - Individual streams: `logs-django-pt`, `logs-celery-pt`, etc.
   - Query and visualize logs using Kibana Discover, Dashboards, and Visualizations

---

## Data Stream Creation Process

### Why Data Streams?

Data streams are the recommended way to store time-series data in Elasticsearch because:
- **Automatic index management**: Backing indices are created automatically
- **Simplified lifecycle**: Easier to manage retention and rollover
- **Better performance**: Optimized for append-only workloads
- **No manual index creation**: Elasticsearch handles index creation based on metadata

### How Data Streams Are Created

Data streams are created **automatically** when Logstash writes the first document. The process:

1. **Index Template Setup** (One-time, manual)
   ```bash
   curl -u elasticsearch_username:PASSWORD -X PUT "http://localhost:9200/_index_template/pt-logs" \
     -H "Content-Type: application/json" \
     -d @elasticsearch-index-template-pt-logs.json
   ```
   - Template matches pattern: `logs-*-pt`
   - Defines field mappings and index settings
   - Marks indices as data streams: `"data_stream": {}`

2. **Security Role Creation** (One-time, manual)
   ```bash
   # Create role with permissions for logs-*-pt pattern
   PUT _security/role/logstash_writer_pt
   {
     "indices": [{
       "names": ["logs-*-pt"],
       "privileges": ["create_index", "create_doc", "index", "create", "write", "read"]
     }]
   }
   ```

3. **User Creation** (One-time, manual)
   ```bash
   # Create user with the role
   POST _security/user/logstash_writer
   {
     "password": "PASSWORD",
     "roles": ["logstash_writer_pt"],
     "full_name": "Logstash writer for PT data streams"
   }
   ```

4. **Automatic Stream Creation** (Automatic, on first write)
   - When Logstash writes a document with:
     - `[data_stream][type]`: "logs"
     - `[data_stream][namespace]`: "pt"
     - `[data_stream][dataset]`: "django" (or celery, etc.)
   - Elasticsearch automatically creates the data stream: `logs-django-pt`
   - First backing index is created automatically

### Data Stream Naming Convention

```
{type}-{dataset}-{namespace}
```

- **type**: Always `logs` (from Logstash configuration)
- **dataset**: Service name from Filebeat (`django`, `celery`, `celerybeat`, `flower`, `nginx`, `react`)
- **namespace**: Group identifier (`pt` for Parcel Tracking)

**Examples**:
- `logs-django-pt` = logs type, django dataset, pt namespace
- `logs-celery-pt` = logs type, celery dataset, pt namespace

---

## Log Processing Pipeline

### Input Stage

```ruby
input {
  beats {
    port => 5044
  }
}
```

- Listens on port 5044 for Beats protocol connections
- Receives logs from Filebeat with metadata (group, service)

### Filter Stage

#### 1. Safety Check
```ruby
if [stream] and [stream] =~ /^\[/ {
  mutate {
    replace => { "stream" => "%{[stream][0]}" }
  }
}
```
- Prevents stream arrays (ensures stream is always a string)

#### 2. Group Filter
```ruby
if [group] == "pt" {
  # Process only PT group logs
}
```

#### 3. Log Parsing (Grok)
```ruby
grok {
  match => {
    "message" => [
      "^%{WORD:log_level}\|%{DATA:logger_name}\|%{TIMESTAMP_ISO8601:log_timestamp}\.%{INT:log_ms}\|%{GREEDYDATA:log_message}$",
      "^%{WORD:log_level}\|%{DATA:logger_name}\|%{TIMESTAMP_ISO8601:log_timestamp}\|%{GREEDYDATA:log_message}$"
    ]
  }
}
```

**Extracted Fields**:
- `log_level`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `logger_name`: Full logger path (e.g., `apps.parcels.views`)
- `log_timestamp`: ISO8601 timestamp
- `log_message`: The actual log message

#### 4. Data Stream Metadata
```ruby
mutate {
  replace => {
    "[data_stream][type]"      => "logs"
    "[data_stream][namespace]" => "pt"
    "[data_stream][dataset]"   => "%{[service]}"
    "[event][module]"          => "pt"
  }
}
```

#### 5. Stream Categorization

**Framework Streams**:
- `django.*` → stream: "django"
- `werkzeug` → stream: "server"
- `boto*`, `s3transfer` → stream: "aws"
- `urllib3` → stream: "network"
- `asyncio`, `PIL`, `root` → stream: "system"

**Application Stream** (66+ loggers):
- `apps.custom_auth.*`, `apps.onboarding.*` → stream: "app", app_module: "auth"
- `apps.parcels.*` → stream: "app", app_module: "parcels"
- `apps.tenant_manager.*` → stream: "app", app_module: "tenant"
- `apps.notification.*` → stream: "app", app_module: "notification"
- `apps.manage_reports.*` → stream: "app", app_module: "reports"
- `apps.integrations.*` → stream: "app", app_module: "integrations"
- `apps.dashboard.*` → stream: "app", app_module: "dashboard"
- `apps.data_governance.*` → stream: "app", app_module: "data_governance"
- `apps.branded.*` → stream: "app", app_module: "branded"
- `apps.container.*` → stream: "app", app_module: "container"
- `apps.harmonization.*` → stream: "app", app_module: "harmonization"
- `apps.logs.*` → stream: "app", app_module: "logs"
- `apps.cron_tasks.*`, `celery.*`, `*.tasks` → stream: "app", app_module: "tasks"
- `apps.common.*` → stream: "app", app_module: "common"
- `config.*` → stream: "app", app_module: "config"
- Unmatched → stream: "unknown", app_module: "unknown"

#### 6. Timestamp Normalization
```ruby
if "_grokparsefailure_pt" not in [tags] and [log_timestamp] {
  date {
    match  => ["log_timestamp", "ISO8601", "yyyy-MM-dd'T'HH:mm:ss"]
    target => "@timestamp"
  }
}
```

### Output Stage

```ruby
output {
  if [group] == "pt" and [service] {
    elasticsearch {
      hosts                  => ["elasticsearch:9200"]
      user                   => "logstash_writer_pt"
      password               => "${LOGSTASH_WRITER_PASSWORD}"
      manage_template        => false
      ecs_compatibility      => "v8"
      data_stream            => true  # Critical: enables data streams
    }
  }
}
```

**Key Points**:
- `data_stream => true`: Tells Elasticsearch to use data streams instead of indices
- `manage_template => false`: We manage templates manually
- `ecs_compatibility => "v8"`: Uses ECS v8 field naming conventions

---

## Security Architecture

### Users and Roles

| User | Purpose | Permissions | Used By |
|------|---------|-------------|---------|
| `elastic` | Superuser | Full cluster access | Human admin, Kibana login |
| `kibana_system` | Kibana operations | `.kibana*` indices | Kibana service |
| `logstash_system` | Logstash monitoring | Monitoring indices | Logstash monitoring |
| `logstash_writer` | Log ingestion | `logs-*-pt` write/read | Logstash output |

### Security Flow

1. **Elasticsearch Security**
   - X-Pack security enabled: `xpack.security.enabled=true`
   - All requests require authentication
   - Passwords stored in Docker volumes (persist across restarts)

2. **Kibana → Elasticsearch**
   - Uses `kibana_system` user
   - Password from environment: `ELASTICSEARCH_PASSWORD`
   - Limited to `.kibana*` indices

3. **Logstash → Elasticsearch**
   - **Monitoring**: `logstash_system` user (for xpack.monitoring)
   - **Data Ingestion**: `logstash_writer` user (for writing logs)
   - Password from environment: `LOGSTASH_WRITER_PASSWORD`

4. **Human Access**
   - Login to Kibana UI as `elastic` user
   - Full admin access for management

### Role Permissions

**logstash_writer_pt Role**:
```json
{
  "indices": [{
    "names": ["logs-*-pt"],
    "privileges": [
      "create_index",  // Create backing indices
      "create_doc",    // Create documents
      "index",         // Index documents
      "create",        // Create operations
      "write",         // Write operations
      "read"           // Read operations
    ]
  }]
}
```

**Why Least Privilege?**
- `logstash_writer` can only write to `logs-*-pt` pattern
- Cannot access other indices
- Cannot modify security settings
- Reduces blast radius if compromised

---

## Configuration Files

### 1. docker-compose.yml
- **Purpose**: Orchestrates Elasticsearch, Kibana, and Logstash services
- **Key Features**:
  - Health checks for all services
  - Service dependencies (Kibana/Logstash wait for Elasticsearch)
  - Volume persistence for data and configs
  - Network isolation (`elk-net`)
  - Environment variable injection for passwords

### 2. elasticsearch.yml
- **Purpose**: Elasticsearch node configuration
- **Key Settings**:
  - `cluster.name`: "elk-cluster"
  - `node.name`: "node-1"
  - `discovery.type`: single-node
  - `xpack.security.enabled`: true
  - `network.host`: 0.0.0.0 (allows container access)

### 3. kibana.yml
- **Purpose**: Kibana server configuration
- **Key Settings**:
  - `server.host`: "0.0.0.0" (allows Docker port mapping)
  - `elasticsearch.hosts`: ["http://elasticsearch:9200"]
  - `elasticsearch.username`: "kibana_system"
  - `xpack.reporting.kibanaServer.hostname`: localhost (for exports)

### 4. logstash.conf
- **Purpose**: Log processing pipeline
- **Sections**:
  - Input: Beats on port 5044
  - Filter: Parsing, categorization, enrichment
  - Output: Elasticsearch data streams

### 5. elasticsearch-index-template-pt-logs.json
- **Purpose**: Index template for PT logs
- **Key Features**:
  - Pattern: `logs-*-pt`
  - Data stream enabled: `"data_stream": {}`
  - Field mappings: @timestamp, message, group, service, stream, logger_name, log_level, log_message, app_module
  - Settings: 1 shard, 0 replicas (suitable for single-node)

### 6. elasticsearch-role-user-logstash-writer.json
- **Purpose**: Security role and user definition
- **Contains**: Role permissions and user creation instructions

---

## Querying in Kibana

### Data Views

Create data views in Kibana:
- **All PT services**: `logs-*-pt`
- **Individual services**: `logs-django-pt`, `logs-celery-pt`, etc.

### Example Queries

#### 1. All PT Logs
```
group:pt
```

#### 2. Django Service Errors
```
group:pt AND service:django AND log_level:ERROR
```

#### 3. Parcels Module Logs
```
group:pt AND stream:app AND app_module:parcels
```

#### 4. Critical Errors Across All Services
```
group:pt AND log_level:CRITICAL
```

#### 5. AWS-Related Logs
```
group:pt AND stream:aws
```

#### 6. Specific Logger
```
group:pt AND logger_name:apps.parcels.views
```

#### 7. Time Range + Service + Module
```
group:pt AND service:django AND app_module:parcels AND log_level:ERROR
```

### Useful Kibana Features

1. **Discover**: Search and filter logs
2. **Dashboards**: Create visualizations
3. **Visualize**: Build charts and graphs
4. **Dev Tools**: Run Elasticsearch queries directly

---

## Troubleshooting

### Common Issues

1. **No Data in Kibana**
   - Check if Filebeat is sending logs to Logstash
   - Verify Logstash is receiving on port 5044: `docker logs logstash`
   - Check Elasticsearch data streams: `GET _data_stream`
   - Verify `logstash_writer` user has correct permissions

2. **Connection Refused**
   - Ensure Elasticsearch is healthy: `docker compose ps`
   - Check `network.host: 0.0.0.0` in `elasticsearch.yml`
   - Verify services are on the same Docker network

3. **Grok Parse Failures**
   - Check log format matches: `LEVEL|LOGGER_NAME|TIMESTAMP|MESSAGE`
   - Review Logstash logs: `docker logs logstash | grep grokparsefailure`
   - Adjust Grok patterns if log format changes

4. **Permission Denied**
   - Verify `logstash_writer` role has `logs-*-pt` permissions
   - Check password in `.env` matches Elasticsearch user
   - Test authentication: `curl -u logstash_writer:PASSWORD http://localhost:9200`

5. **Data Stream Not Created**
   - Ensure index template is created: `GET _index_template/pt-logs`
   - Check Logstash output has `data_stream => true`
   - Verify data stream metadata is set correctly in Logstash filter

### Verification Commands

```bash
# Check Elasticsearch health
curl -u elastic:PASSWORD http://localhost:9200/_cluster/health

# List data streams
curl -u elastic:PASSWORD http://localhost:9200/_data_stream

# Check index template
curl -u elastic:PASSWORD http://localhost:9200/_index_template/pt-logs

# View Logstash logs
docker logs logstash --tail 100

# Check service status
docker compose ps

# Test Logstash connection to Elasticsearch
docker exec logstash curl -u logstash_writer:PASSWORD http://elasticsearch:9200
```

---

## Summary

This ELK stack implementation provides:

✅ **6 Data Streams** for comprehensive log collection from all PT services  
✅ **Automatic Categorization** into logical streams (django, server, aws, network, system, app, unknown)  
✅ **Application Module Classification** for detailed app log analysis  
✅ **Secure Authentication** with least-privilege access  
✅ **Docker-Based Deployment** for easy setup and management  
✅ **Production-Ready Configuration** with health checks, persistence, and restart policies  

The stack is designed to scale and can be extended with additional services, streams, or modules as needed.

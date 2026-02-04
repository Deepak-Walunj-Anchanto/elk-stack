# ELK Stack Complete Analysis and Architecture Documentation

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Data Streams Inventory](#data-streams-inventory)
4. [Component Analysis](#component-analysis)
5. [Data Flow Pipeline](#data-flow-pipeline)
6. [Configuration Deep Dive](#configuration-deep-dive)
7. [Field Mapping and Enrichment](#field-mapping-and-enrichment)
8. [Security and Permissions](#security-and-permissions)
9. [Troubleshooting Guide](#troubleshooting-guide)

---

## Executive Summary

This document provides a complete analysis of the ELK (Elasticsearch, Logstash, Kibana) stack implementation for the Parcel Tracking (PT) application. The stack uses **Elasticsearch Data Streams** (not traditional indices) to handle time-series log data efficiently.

### Key Metrics
- **Total Data Streams**: 1 (currently active: `logs-django-pt`)
- **Log Streams per Service**: 6 (django, server, system, aws, network, app)
- **Application Modules**: 15+ (parcels, auth, tenant, notification, reports, etc.)
- **Log Format**: `LEVEL|LOGGER_NAME|TIMESTAMP|MESSAGE`
- **Filebeat Inputs**: 6 (one per log file)
- **Logstash Filters**: 66+ logger name patterns categorized into streams

### Current Status
✅ **Production Ready** for Django service in development environment
- All 6 log streams are being captured
- Data successfully flowing to Elasticsearch data stream
- Kibana visualization working

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer (Django)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ django   │  │ server   │  │ system   │  │   aws    │      │
│  │  .log    │  │  .log    │  │  .log    │  │  .log    │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│  ┌──────────┐  ┌──────────┐                                    │
│  │ network  │  │   app   │                                    │
│  │  .log    │  │  .log    │                                    │
│  └──────────┘  └──────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Docker Volume Mount (.:/app)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Filebeat (Log Shipper)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 6 Inputs (filestream):                                   │  │
│  │  - django.log → group:pt, service:django, stream:django │  │
│  │  - server.log → group:pt, service:django, stream:server │  │
│  │  - system.log → group:pt, service:django, stream:system │  │
│  │  - aws.log    → group:pt, service:django, stream:aws    │  │
│  │  - network.log→ group:pt, service:django, stream:network│  │
│  │  - app.log    → group:pt, service:django, stream:app    │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Beats Protocol (TCP 5044)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Logstash (Log Processor)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Input: Beats on port 5044                                │  │
│  │                                                           │  │
│  │ Filter Pipeline:                                          │  │
│  │  1. Normalize stream field (prevent arrays)              │  │
│  │  2. Parse log format (grok):                             │  │
│  │     LEVEL|LOGGER_NAME|TIMESTAMP|MESSAGE                   │  │
│  │  3. Set data_stream metadata:                            │  │
│  │     - type: "logs"                                        │  │
│  │     - namespace: "pt"                                     │  │
│  │     - dataset: "%{service}" (django, celery, etc.)       │  │
│  │  4. Categorize by logger_name → stream + app_module      │  │
│  │  5. Normalize @timestamp                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Elasticsearch API (HTTP 9200)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Elasticsearch (Data Stream Storage)                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Data Stream: logs-django-pt                              │  │
│  │   - Type: logs                                           │  │
│  │   - Dataset: django                                      │  │
│  │   - Namespace: pt                                        │  │
│  │   - Index Template: pt-logs (priority 150)              │  │
│  │   - Fields: group, service, stream, logger_name,        │  │
│  │             log_level, log_message, app_module           │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Query API
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Kibana (Visualization)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Data View: logs-*-pt (all PT services)                  │  │
│  │   - Discover: Search and filter logs                     │  │
│  │   - Dashboards: Visual analytics                         │  │
│  │   - Query Examples:                                      │  │
│  │     * group:pt AND service:django                        │  │
│  │     * stream:app AND app_module:parcels                 │  │
│  │     * log_level:ERROR                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Locations

| Component | Location | Purpose |
|-----------|----------|---------|
| **Django Logging Config** | `config/settings/base.py` | Defines 6 log handlers, formatters, and logger routing |
| **Filebeat Config** | `docker/filebeat/filebeat.template.yml` | Defines 6 inputs, processors, and Logstash output |
| **Filebeat Dockerfile** | `docker/filebeat/Dockerfile` | Builds Filebeat 8.11.0 image |
| **Filebeat Entrypoint** | `docker/filebeat/entrypoint.sh` | Substitutes env vars and starts Filebeat |
| **Logstash Config** | `docker/logstash/logstash.conf` | Complete pipeline: input → filter → output |
| **ES Role Config** | `docker/logstash/elasticsearch-role-user-logstash-writer.json` | Security role and user definitions |
| **ES Index Template** | `docker/logstash/elasticsearch-index-template-pt-logs.json` | Data stream template for logs-*-pt |
| **Docker Compose** | `docker-compose.yml` | Orchestrates Django, Filebeat, Redis services |

---

## Data Streams Inventory

### Current Active Data Stream

#### 1. `logs-django-pt`

**Purpose**: Centralized log storage for Django application service

**Structure**:
- **Type**: `logs` (Elasticsearch data stream type)
- **Dataset**: `django` (service identifier)
- **Namespace**: `pt` (Parcel Tracking product group)

**Why Data Streams?**
- **Time-series optimization**: Data streams are optimized for append-only time-series data
- **Automatic index management**: Elasticsearch automatically creates backing indices
- **Simplified lifecycle**: ILM (Index Lifecycle Management) policies apply automatically
- **Better performance**: Write-optimized for high-volume log ingestion
- **No manual index management**: No need to create daily/weekly indices manually

**How It Was Created**:
1. **Index Template**: Created `pt-logs` template with pattern `logs-*-pt` and priority 150
2. **Logstash Output**: Configured with `data_stream => true` in `logstash.conf`
3. **Automatic Creation**: First document written by Logstash automatically created the data stream
4. **Template Application**: Elasticsearch matched the pattern and applied the template

**Data Flow**:
```
Django → 6 log files → Filebeat (6 inputs) → Logstash → logs-django-pt
```

**Fields Stored**:
- `@timestamp`: Event timestamp (parsed from log or Beats timestamp)
- `message`: Raw log line
- `group`: "pt" (product group)
- `service`: "django" (service name)
- `stream`: One of [django, server, system, aws, network, app, unknown]
- `logger_name`: Full logger name (e.g., "apps.parcels.views")
- `log_level`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `log_message`: Parsed message content
- `app_module`: Application module (only when stream=app)
- `log_timestamp`: Original timestamp from log line
- `log_ms`: Milliseconds from original timestamp

**Query Examples**:
```kql
# All Django logs
service:django

# Application errors only
service:django AND stream:app AND log_level:ERROR

# Parcels module logs
service:django AND app_module:parcels

# Framework logs (Django ORM, requests)
service:django AND stream:django

# AWS SDK logs
service:django AND stream:aws
```

### Planned Data Streams (Not Yet Active)

The architecture supports 6 total data streams, but currently only Django is active:

| Data Stream | Service | Status | Purpose |
|-------------|---------|--------|---------|
| `logs-django-pt` | django | ✅ Active | Web application, management commands |
| `logs-celery-pt` | celery | ⏳ Planned | Background task workers |
| `logs-celerybeat-pt` | celerybeat | ⏳ Planned | Scheduled task scheduler |
| `logs-flower-pt` | flower | ⏳ Planned | Celery monitoring dashboard |
| `logs-nginx-pt` | nginx | ⏳ Planned | Web server access/error logs |
| `logs-react-pt` | react | ⏳ Planned | Frontend application logs |

**Why Multiple Streams?**
- **Service Isolation**: Each service's logs are isolated for easier debugging
- **Performance**: Separate streams allow independent scaling and ILM policies
- **Security**: Different services may have different retention/access requirements
- **Query Efficiency**: Filtering by service is faster with separate streams

---

## Component Analysis

### 1. Django Logging Configuration (`config/settings/base.py`)

**Purpose**: Configure Python logging to write structured logs to 6 separate files

**Key Components**:

#### Log Format
```python
format: "%(levelname)s|%(name)s|%(asctime)s.%(msecs)03d|%(message)s"
datefmt: "%Y-%m-%dT%H:%M:%S"
```
**Example Output**: `INFO|apps.parcels.views|2025-02-02T12:34:56.123|Parcel created successfully`

**Why This Format?**
- **Parseable**: Pipe-delimited for easy grok parsing in Logstash
- **Structured**: Contains all metadata needed for categorization
- **Timestamp Precision**: Includes milliseconds for accurate ordering
- **Logger Identification**: Full logger name enables module-level filtering

#### Six Stream Handlers

| Stream | File | Loggers | Purpose |
|--------|------|---------|---------|
| **django** | `django.log` | `django.request`, `django.db.backends` | Framework-level logs (HTTP requests, SQL queries) |
| **server** | `server.log` | `werkzeug` | Development server logs |
| **system** | `system.log` | `watchdog`, `PIL`, `nose` | System/library logs (file watchers, image processing) |
| **aws** | `aws.log` | `boto`, `boto3`, `botocore`, `s3transfer` | AWS SDK logs (S3, etc.) |
| **network** | `network.log` | `urllib3` | HTTP client library logs |
| **app** | `app.log` | `root` (all `apps.*`, `config.*`, etc.) | Application business logic logs |

**File Handler Configuration**:
- **Type**: `RotatingFileHandler`
- **Max Size**: 10 MB per file
- **Backups**: 5 backup files (total ~60 MB per stream)
- **Location**: `apps/logs/{stream}.log`

**Why Separate Files?**
- **Stream Isolation**: Each stream can be processed independently
- **Filebeat Efficiency**: Filebeat can track position per file
- **Debugging**: Easier to tail specific log types during development
- **Volume Control**: High-volume streams (app) don't overwhelm low-volume (aws)

#### Logger Routing Logic

**Framework Loggers** (Explicit):
- `django.request` → `file_django` handler
- `django.db.backends` → `file_django` handler
- `werkzeug` → `file_server` handler
- `boto*`, `s3transfer` → `file_aws` handler
- `urllib3` → `file_network` handler
- `watchdog`, `PIL`, `nose` → `file_system` handler

**Application Loggers** (Root):
- All `apps.*` loggers (e.g., `apps.parcels.views`)
- All `config.*` loggers
- Any other logger not explicitly configured
- → All go to `file_app` handler via root logger

### 2. Filebeat Configuration (`docker/filebeat/filebeat.template.yml`)

**Purpose**: Read log files and ship them to Logstash with metadata enrichment

**Key Components**:

#### Input Configuration (6 filestream inputs)

Each input:
- **Type**: `filestream` (tracks file position, handles rotation)
- **ID**: Unique identifier (e.g., `pt-django-stream-django`)
- **Path**: Absolute path to log file in container (`/app/apps/logs/{stream}.log`)
- **Processors**: Add metadata fields

**Example Input**:
```yaml
- type: filestream
  id: pt-django-stream-django
  paths:
    - /app/apps/logs/django.log
  processors:
    - add_fields:
        target: ""
        fields:
          group: "pt"
          service: "django"
          stream: "django"
```

**Why filestream?**
- **Position Tracking**: Remembers where it left off (survives restarts)
- **Rotation Handling**: Automatically handles log rotation
- **Efficient**: Only reads new lines, not entire files
- **Reliable**: Tracks inode changes, handles file renames

#### Metadata Fields Added

| Field | Value | Purpose |
|-------|-------|---------|
| `group` | "pt" | Product group identifier (allows multi-product ELK) |
| `service` | "django" | Service identifier (routes to correct data stream) |
| `stream` | One of [django, server, system, aws, network, app] | Log stream category (from file name) |

**Why These Fields?**
- **Routing**: Logstash uses `group` and `service` to route to correct data stream
- **Filtering**: Kibana queries can filter by service, stream, group
- **Multi-tenancy**: `group` allows multiple products in same ELK cluster
- **Debugging**: `stream` helps identify log source during troubleshooting

#### Output Configuration

```yaml
output.logstash:
  hosts: ["${LOGSTASH_HOST}:${LOGSTASH_PORT}"]
```

**Dynamic Configuration**:
- `LOGSTASH_HOST`: Default `host.docker.internal` (for local ELK)
- `LOGSTASH_PORT`: Default `5044` (Beats protocol port)
- Substituted at runtime by `entrypoint.sh`

**Why Logstash Output?**
- **Processing**: Logstash provides powerful filtering/enrichment
- **Protocol**: Beats protocol is efficient and reliable
- **Buffering**: Filebeat handles backpressure and retries
- **Compression**: Automatic compression reduces network traffic

#### Processors

```yaml
processors:
  - add_cloud_metadata: ~
  - add_host_metadata: ~
```

**Purpose**:
- **Cloud Metadata**: Adds cloud provider info (AWS region, instance ID, etc.)
- **Host Metadata**: Adds hostname, OS, IP addresses
- **Enrichment**: Provides context for log events

### 3. Filebeat Dockerfile (`docker/filebeat/Dockerfile`)

**Purpose**: Build Filebeat container image

**Key Steps**:
1. **Base Image**: `docker.elastic.co/beats/filebeat:8.11.0` (official Elastic image)
2. **User Switch**: `USER root` (needs root to read log files)
3. **Copy Config**: Template file and entrypoint script
4. **Fix Line Endings**: Windows → Unix line endings for entrypoint
5. **Make Executable**: `chmod +x` on entrypoint
6. **Entrypoint**: Custom script replaces default

**Why Custom Entrypoint?**
- **Environment Variables**: Substitutes `LOGSTASH_HOST` and `LOGSTASH_PORT`
- **Flexibility**: Allows runtime configuration without rebuilding image
- **Template Pattern**: Single template file works for all environments

### 4. Filebeat Entrypoint (`docker/filebeat/entrypoint.sh`)

**Purpose**: Runtime configuration substitution and Filebeat startup

**Process**:
1. **Set Defaults**: `LOGSTASH_HOST=${LOGSTASH_HOST:-logstash}`, `LOGSTASH_PORT=${LOGSTASH_PORT:-5044}`
2. **Substitute**: `sed` replaces `${LOGSTASH_HOST}` and `${LOGSTASH_PORT}` in template
3. **Generate Config**: Creates `/usr/share/filebeat/filebeat.yml` from template
4. **Execute**: Runs Filebeat with generated config

**Why Shell Script?**
- **Simplicity**: Basic string substitution, no complex logic needed
- **Portability**: Works in any shell environment
- **Docker-Friendly**: Standard pattern for config generation

### 5. Logstash Configuration (`docker/logstash/logstash.conf`)

**Purpose**: Process, enrich, and route log events to Elasticsearch

**Pipeline Stages**:

#### Input Stage

```ruby
input {
  beats {
    port => 5044
  }
}
```

**Purpose**: Accept Beats protocol connections from Filebeat

**Configuration**:
- **Port**: 5044 (standard Beats port)
- **Protocol**: Beats (binary protocol, efficient)
- **Connection Handling**: Automatic connection management

#### Filter Stage

**Stage 1: Stream Normalization**
```ruby
if [stream] and [stream] =~ /^\[/ {
  mutate {
    replace => { "stream" => "%{[stream][0]}" }
  }
}
```
**Purpose**: Prevent stream field from being an array (safety check)

**Stage 2: Group Filtering**
```ruby
if [group] == "pt" {
  # ... all processing ...
}
```
**Purpose**: Only process PT group logs (allows multi-product ELK)

**Stage 3: Log Parsing (Grok)**
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

**Patterns**:
1. **With Milliseconds**: `LEVEL|LOGGER|TIMESTAMP.MS|MESSAGE`
2. **Without Milliseconds**: `LEVEL|LOGGER|TIMESTAMP|MESSAGE`

**Extracted Fields**:
- `log_level`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `logger_name`: Full logger name (e.g., `apps.parcels.views`)
- `log_timestamp`: ISO8601 timestamp
- `log_ms`: Milliseconds (if present)
- `log_message`: Actual log message content

**Why Two Patterns?**
- **Flexibility**: Handles logs with or without millisecond precision
- **Robustness**: Prevents parse failures from format variations

**Stage 4: Data Stream Metadata**
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

**Purpose**: Set Elasticsearch data stream metadata

**Fields**:
- `type`: "logs" (data stream type)
- `namespace`: "pt" (product group)
- `dataset`: Dynamic from `service` field (django, celery, etc.)
- `module`: "pt" (ECS module identifier)

**Result**: Data stream name = `{type}-{dataset}-{namespace}` = `logs-django-pt`

**Stage 5: Stream Categorization**

**Framework Streams** (Explicit Patterns):
```ruby
if [logger_name] =~ /^django\./ {
  mutate { replace => { "stream" => "django" } }
}
else if [logger_name] == "werkzeug" {
  mutate { replace => { "stream" => "server" } }
}
# ... etc for aws, network, system
```

**Application Stream** (Module Extraction):
```ruby
else if [logger_name] =~ /^apps\.parcels/ {
  mutate {
    replace => { "stream" => "app" }
    add_field => { "app_module" => "parcels" }
  }
}
# ... etc for 15+ app modules
```

**App Modules Mapped**:
- `apps.custom_auth`, `apps.onboarding` → `app_module: "auth"`
- `apps.parcels` → `app_module: "parcels"`
- `apps.tenant_manager` → `app_module: "tenant"`
- `apps.notification` → `app_module: "notification"`
- `apps.manage_reports` → `app_module: "reports"`
- `apps.integrations` → `app_module: "integrations"`
- `apps.dashboard` → `app_module: "dashboard"`
- `apps.data_governance` → `app_module: "data_governance"`
- `apps.branded` → `app_module: "branded"`
- `apps.container` → `app_module: "container"`
- `apps.harmonization` → `app_module: "harmonization"`
- `apps.logs` → `app_module: "logs"`
- `apps.cron_tasks`, `celery`, `*.tasks` → `app_module: "tasks"`
- `apps.common` → `app_module: "common"`
- `config.*` → `app_module: "config"`
- Unknown → `app_module: "unknown"`

**Why This Categorization?**
- **Query Efficiency**: Filter by module in Kibana (e.g., `app_module:parcels`)
- **Debugging**: Quickly identify which part of app generated log
- **Analytics**: Aggregate errors by module for monitoring
- **Stream Override**: Filebeat sets initial stream from file name; Logstash refines based on logger

**Stage 6: Timestamp Normalization**
```ruby
if "_grokparsefailure_pt" not in [tags] and [log_timestamp] {
  date {
    match  => ["log_timestamp", "ISO8601", "yyyy-MM-dd'T'HH:mm:ss"]
    target => "@timestamp"
  }
}
```

**Purpose**: Use log timestamp as `@timestamp` (Elasticsearch's primary time field)

**Why?**
- **Accuracy**: Log timestamp is more accurate than Filebeat ingestion time
- **Ordering**: Events appear in correct chronological order
- **Fallback**: If parsing fails, uses Beats `@timestamp`

#### Output Stage

```ruby
output {
  if [group] == "pt" and [service] {
    elasticsearch {
      hosts                  => ["elasticsearch:9200"]
      user                   => "logstash_writer_pt"
      password               => "${LOGSTASH_WRITER_PASSWORD}"
      manage_template        => false
      ecs_compatibility      => "v8"
      data_stream            => true
    }
    stdout { codec => rubydebug }
  }
}
```

**Configuration**:
- **Hosts**: Elasticsearch endpoint (assumes same Docker network)
- **Authentication**: User `logstash_writer_pt` with password from env
- **Template Management**: `false` (template created separately)
- **ECS Compatibility**: v8 (Elastic Common Schema version 8)
- **Data Stream**: `true` (use data streams, not indices)
- **Debug Output**: `stdout` for troubleshooting (can be disabled)

**Why Data Streams?**
- **Automatic Management**: Elasticsearch handles index creation/lifecycle
- **Performance**: Optimized for append-only time-series data
- **ILM Integration**: Lifecycle policies apply automatically
- **Simplified Queries**: Single data stream name, not date-based indices

### 6. Elasticsearch Index Template (`docker/logstash/elasticsearch-index-template-pt-logs.json`)

**Purpose**: Define mapping and settings for `logs-*-pt` data streams

**Key Components**:

#### Index Pattern
```json
"index_patterns": ["logs-*-pt"]
```
**Matches**: All data streams with pattern `logs-{dataset}-pt`

#### Data Stream Configuration
```json
"data_stream": {}
```
**Purpose**: Enable data stream mode (not regular index)

#### Priority
```json
"priority": 150
```
**Why 150?**
- Elasticsearch built-in `logs` template has priority 100
- Higher priority (150) ensures this template takes precedence
- Allows custom field mappings for PT-specific fields

#### Settings
```json
"settings": {
  "number_of_shards": 1,
  "number_of_replicas": 0
}
```
**Purpose**: Development-friendly settings (single shard, no replicas)

**Production Note**: Adjust based on volume and availability requirements

#### Field Mappings
```json
"mappings": {
  "properties": {
    "@timestamp": { "type": "date" },
    "message": { "type": "text" },
    "group": { "type": "keyword" },
    "service": { "type": "keyword" },
    "stream": { "type": "keyword" },
    "logger_name": { "type": "keyword" },
    "log_level": { "type": "keyword" },
    "log_message": { "type": "text" },
    "app_module": { "type": "keyword" }
  }
}
```

**Field Types**:
- **keyword**: Exact match, filtering, aggregations (group, service, stream, etc.)
- **text**: Full-text search (message, log_message)
- **date**: Time-based queries and sorting (@timestamp)

**Why These Mappings?**
- **Performance**: Keyword fields are faster for filtering
- **Search**: Text fields support full-text search
- **Analytics**: Keyword fields enable aggregations (count by service, etc.)

### 7. Elasticsearch Security (`docker/logstash/elasticsearch-role-user-logstash-writer.json`)

**Purpose**: Define role and user for Logstash to write to Elasticsearch

#### Role: `logstash_writer_pt`

**Privileges**:
```json
"indices": [{
  "names": ["logs-*-pt"],
  "privileges": ["create_index", "create_doc", "index", "create", "write", "read"]
}]
```

**Purpose**: Allow Logstash to:
- **create_index**: Create backing indices for data streams
- **create_doc**: Create documents
- **index**: Index documents
- **create**: Create new documents
- **write**: Write to existing documents
- **read**: Read for debugging/reindexing

**Security Principle**: Least privilege (only `logs-*-pt` pattern)

#### User: `logstash_writer`

**Configuration**:
```json
{
  "password": "<from LOGSTASH_WRITER_PASSWORD env>",
  "roles": ["logstash_writer_pt"],
  "full_name": "Logstash writer for PT data streams"
}
```

**Purpose**: Service account for Logstash to authenticate

**Security**: Password stored in environment variable, not in code

### 8. Docker Compose Configuration (`docker-compose.yml`)

**Purpose**: Orchestrate Django, Filebeat, and Redis services

#### Django Service
```yaml
django:
  volumes:
    - .:/app:z
  environment:
    DEPLOY_ENV: "LOCAL"
    IS_PT: "True"
```

**Key Points**:
- **Volume Mount**: `.:/app` allows Django to write logs to `apps/logs/`
- **Environment**: Sets deployment context

#### Filebeat Service
```yaml
filebeat:
  build:
    dockerfile: docker/filebeat/Dockerfile
  volumes:
    - .:/app:ro
  environment:
    - LOGSTASH_HOST=${LOGSTASH_HOST:-host.docker.internal}
    - LOGSTASH_PORT=${LOGSTASH_PORT:-5044}
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

**Key Points**:
- **Read-Only Mount**: `:ro` prevents Filebeat from modifying files
- **Host Gateway**: Allows access to host machine (for local ELK)
- **Environment Variables**: Configurable Logstash endpoint

**Why `host.docker.internal`?**
- **Local Development**: ELK stack runs on host machine, not in Docker
- **Cross-Platform**: Works on Windows, macOS, Linux
- **Flexibility**: Can override with actual IP for remote ELK

---

## Data Flow Pipeline

### Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: Django Application Logging                                  │
│                                                                     │
│ Python Code:                                                       │
│   logger = logging.getLogger('apps.parcels.views')                │
│   logger.info('Parcel created')                                   │
│                                                                     │
│ Django LOGGING Config (base.py):                                   │
│   - Matches logger 'apps.parcels.views'                            │
│   - Routes to root logger → file_app handler                       │
│   - Formats: INFO|apps.parcels.views|2025-02-02T12:34:56.123|... │
│   - Writes to: apps/logs/app.log                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: Filebeat File Reading                                      │
│                                                                     │
│ Filebeat Input (filestream):                                       │
│   - Watches: /app/apps/logs/app.log                                │
│   - Reads new lines (tracks position)                              │
│   - Detects: INFO|apps.parcels.views|2025-02-02T12:34:56.123|... │
│                                                                     │
│ Filebeat Processors:                                               │
│   - add_fields: {group: "pt", service: "django", stream: "app"}   │
│   - add_host_metadata: {hostname, os, ip}                          │
│   - add_cloud_metadata: {cloud provider info}                      │
│                                                                     │
│ Filebeat Output:                                                   │
│   - Sends via Beats protocol to LOGSTASH_HOST:5044                 │
│   - Event includes: message, @timestamp, fields.group, etc.        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: Logstash Input                                             │
│                                                                     │
│ Beats Input Plugin:                                                │
│   - Listens on port 5044                                            │
│   - Accepts Beats protocol connection                              │
│   - Receives event from Filebeat                                   │
│   - Event structure:                                                │
│     {                                                               │
│       "@timestamp": "2025-02-02T12:34:56.123Z",                    │
│       "message": "INFO|apps.parcels.views|...",                    │
│       "fields": {                                                   │
│         "group": "pt",                                              │
│         "service": "django",                                        │
│         "stream": "app"                                             │
│       }                                                             │
│     }                                                               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: Logstash Filter Pipeline                                   │
│                                                                     │
│ Filter 1: Stream Normalization                                     │
│   - Check if stream is array → extract first element               │
│                                                                     │
│ Filter 2: Group Check                                              │
│   - if [group] == "pt" → continue processing                       │
│   - else → skip (multi-product support)                            │
│                                                                     │
│ Filter 3: Grok Parsing                                             │
│   - Pattern: %{WORD:log_level}|%{DATA:logger_name}|...            │
│   - Extracts: log_level, logger_name, log_timestamp, log_message   │
│   - Result:                                                         │
│     log_level: "INFO"                                              │
│     logger_name: "apps.parcels.views"                               │
│     log_timestamp: "2025-02-02T12:34:56"                          │
│     log_message: "Parcel created"                                  │
│                                                                     │
│ Filter 4: Data Stream Metadata                                     │
│   - Sets: [data_stream][type] = "logs"                             │
│   - Sets: [data_stream][namespace] = "pt"                          │
│   - Sets: [data_stream][dataset] = "django" (from service)         │
│                                                                     │
│ Filter 5: Stream Categorization                                    │
│   - Matches logger_name: "apps.parcels.views"                       │
│   - Pattern: /^apps\.parcels/                                      │
│   - Sets: stream = "app"                                           │
│   - Sets: app_module = "parcels"                                   │
│                                                                     │
│ Filter 6: Timestamp Normalization                                   │
│   - Parses log_timestamp → @timestamp                              │
│   - Uses log time instead of ingestion time                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 5: Logstash Output                                            │
│                                                                     │
│ Output Condition:                                                   │
│   - if [group] == "pt" and [service] exists                        │
│                                                                     │
│ Elasticsearch Output Plugin:                                        │
│   - Connects to: elasticsearch:9200                                 │
│   - Authenticates: logstash_writer_pt / password                    │
│   - Data Stream Mode: data_stream => true                          │
│   - Stream Name: logs-django-pt (from metadata)                    │
│   - Sends document to Elasticsearch                                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 6: Elasticsearch Data Stream                                  │
│                                                                     │
│ Elasticsearch Processing:                                           │
│   - Receives document with data_stream metadata                     │
│   - Checks index template: pt-logs (pattern: logs-*-pt)            │
│   - Creates data stream: logs-django-pt (if first document)        │
│   - Creates backing index: .ds-logs-django-pt-2025.02.02-000001    │
│   - Applies template mappings and settings                          │
│   - Indexes document                                                │
│                                                                     │
│ Document Stored:                                                    │
│   {                                                                 │
│     "@timestamp": "2025-02-02T12:34:56.123Z",                       │
│     "message": "INFO|apps.parcels.views|...",                      │
│     "group": "pt",                                                  │
│     "service": "django",                                            │
│     "stream": "app",                                                │
│     "logger_name": "apps.parcels.views",                            │
│     "log_level": "INFO",                                            │
│     "log_message": "Parcel created",                                │
│     "app_module": "parcels"                                         │
│   }                                                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 7: Kibana Visualization                                       │
│                                                                     │
│ Data View: logs-*-pt                                               │
│   - Pattern matches: logs-django-pt                                │
│   - Fields available: group, service, stream, app_module, etc.      │
│                                                                     │
│ Query Examples:                                                     │
│   - service:django AND stream:app                                  │
│   - app_module:parcels AND log_level:ERROR                         │
│   - group:pt                                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### Event Transformation Summary

| Stage | Field | Value | Source |
|-------|-------|-------|--------|
| **Django** | Log Line | `INFO|apps.parcels.views|2025-02-02T12:34:56.123|Parcel created` | Python logger |
| **Filebeat** | `message` | `INFO|apps.parcels.views|2025-02-02T12:34:56.123|Parcel created` | File content |
| **Filebeat** | `fields.group` | `"pt"` | Processor |
| **Filebeat** | `fields.service` | `"django"` | Processor |
| **Filebeat** | `fields.stream` | `"app"` | Processor (from file name) |
| **Logstash** | `log_level` | `"INFO"` | Grok extraction |
| **Logstash** | `logger_name` | `"apps.parcels.views"` | Grok extraction |
| **Logstash** | `log_message` | `"Parcel created"` | Grok extraction |
| **Logstash** | `stream` | `"app"` | Logger name pattern match |
| **Logstash** | `app_module` | `"parcels"` | Logger name pattern match |
| **Logstash** | `[data_stream][dataset]` | `"django"` | From service field |
| **Elasticsearch** | Data Stream | `logs-django-pt` | Computed from metadata |

---

## Field Mapping and Enrichment

### Field Hierarchy

```
Event Root
├── @timestamp (date)              # Primary time field (from log or ingestion)
├── message (text)                  # Raw log line
├── group (keyword)                 # Product group: "pt"
├── service (keyword)               # Service name: "django", "celery", etc.
├── stream (keyword)                # Log stream: "django", "server", "app", etc.
├── logger_name (keyword)           # Full logger: "apps.parcels.views"
├── log_level (keyword)             # Log level: "DEBUG", "INFO", "ERROR", etc.
├── log_message (text)              # Parsed message content
├── log_timestamp (text)           # Original timestamp string
├── log_ms (integer)               # Milliseconds (if present)
├── app_module (keyword)            # App module (only when stream=app)
├── data_stream (object)            # Elasticsearch data stream metadata
│   ├── type: "logs"
│   ├── namespace: "pt"
│   └── dataset: "django" (dynamic)
└── event (object)                  # ECS event metadata
    └── module: "pt"
```

### Field Sources

| Field | Added By | Purpose |
|-------|----------|---------|
| `@timestamp` | Logstash (date filter) | Primary time field for queries |
| `message` | Filebeat (from file) | Raw log line for debugging |
| `group` | Filebeat (processor) | Product group identifier |
| `service` | Filebeat (processor) | Service identifier (routes to data stream) |
| `stream` | Filebeat (processor) → Logstash (refined) | Log stream category |
| `logger_name` | Logstash (grok) | Full logger name |
| `log_level` | Logstash (grok) | Log severity level |
| `log_message` | Logstash (grok) | Parsed message content |
| `app_module` | Logstash (pattern match) | Application module (parcels, auth, etc.) |
| `data_stream.*` | Logstash (mutate) | Elasticsearch data stream metadata |

### Enrichment Process

1. **Filebeat Enrichment**:
   - Adds `group`, `service`, `stream` from file name
   - Adds host metadata (hostname, OS, IP)
   - Adds cloud metadata (if in cloud)

2. **Logstash Enrichment**:
   - Parses log format → extracts structured fields
   - Categorizes logger → determines `stream` and `app_module`
   - Normalizes timestamp → sets `@timestamp`
   - Sets data stream metadata → routes to correct stream

3. **Elasticsearch Enrichment**:
   - Applies index template → sets field mappings
   - Creates data stream → if first document
   - Indexes document → stores in backing index

---

## Security and Permissions

### Authentication Flow

```
Logstash → Elasticsearch API (HTTP 9200)
  │
  ├── User: logstash_writer_pt
  ├── Password: ${LOGSTASH_WRITER_PASSWORD} (from env)
  └── Role: logstash_writer_pt
```

### Role Privileges

**Role**: `logstash_writer_pt`

**Index Pattern**: `logs-*-pt`

**Privileges**:
- `create_index`: Create backing indices for data streams
- `create_doc`: Create new documents
- `index`: Index documents
- `create`: Create documents (idempotent)
- `write`: Update existing documents
- `read`: Read documents (for debugging)

**Security Principle**: Least privilege (only `logs-*-pt` pattern, no other indices)

### User Configuration

**User**: `logstash_writer`

**Properties**:
- **Password**: From `LOGSTASH_WRITER_PASSWORD` environment variable
- **Roles**: `["logstash_writer_pt"]`
- **Full Name**: "Logstash writer for PT data streams"

**Creation**:
```bash
curl -u elastic:ELASTIC_PASSWORD -X POST "http://localhost:9200/_security/user/logstash_writer" \
  -H "Content-Type: application/json" -d '{
    "password": "LOGSTASH_WRITER_PASSWORD",
    "roles": ["logstash_writer_pt"],
    "full_name": "Logstash writer for PT"
  }'
```

### Network Security

**Filebeat → Logstash**:
- **Protocol**: Beats (binary, efficient)
- **Port**: 5044 (configurable)
- **Network**: Docker network or host network (for local ELK)

**Logstash → Elasticsearch**:
- **Protocol**: HTTP/HTTPS
- **Port**: 9200 (default)
- **Network**: Docker network (assumes same compose) or remote

**Recommendations**:
- Use TLS for production (HTTPS)
- Restrict network access (firewall rules)
- Rotate passwords regularly
- Use secrets management (Docker secrets, Kubernetes secrets)

---

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. No Logs in Kibana

**Symptoms**: Logs exist in files, but nothing appears in Kibana

**Diagnosis Steps**:

1. **Check Filebeat**:
   ```bash
   docker logs filebeat
   ```
   Look for:
   - Connection errors to Logstash
   - File reading errors
   - Configuration errors

2. **Check Logstash**:
   ```bash
   docker logs logstash
   ```
   Look for:
   - Beats input connection errors
   - Grok parse failures
   - Elasticsearch connection errors
   - 401/403 authentication errors

3. **Check Elasticsearch**:
   ```bash
   curl -u elastic:PASSWORD "http://localhost:9200/_data_stream/logs-*-pt"
   ```
   Verify data stream exists and has documents

4. **Check Data View**:
   - Kibana → Stack Management → Data Views
   - Verify `logs-*-pt` data view exists
   - Check time range (default is last 15 minutes)

**Solutions**:
- Verify `LOGSTASH_HOST` and `LOGSTASH_PORT` in Filebeat
- Check Logstash is listening on port 5044
- Verify Elasticsearch user/password
- Check index template exists
- Verify data view time range

#### 2. Filebeat "EOF" or "Client Not Connected"

**Symptoms**: Filebeat connects but immediately disconnects

**Causes**:
1. Logstash not running on port 5044
2. Another process using port 5044
3. IPv6 connectivity issues
4. Logstash pipeline errors

**Solutions**:
- Verify Logstash is running: `docker ps | grep logstash`
- Check port availability: `netstat -an | grep 5044`
- Force IPv4: Set `LOGSTASH_HOST` to IPv4 address
- Check Logstash logs for errors

#### 3. Grok Parse Failures

**Symptoms**: Logs appear but fields are missing (`_grokparsefailure_pt` tag)

**Causes**:
- Log format doesn't match grok pattern
- Timestamp format variation
- Special characters in message

**Solutions**:
- Check log format matches: `LEVEL|LOGGER|TIMESTAMP|MESSAGE`
- Verify grok patterns in `logstash.conf`
- Test grok patterns: https://grokdebug.herokuapp.com/
- Add fallback patterns for variations

#### 4. Wrong Data Stream

**Symptoms**: Logs go to wrong data stream (e.g., `logs-celery-pt` instead of `logs-django-pt`)

**Causes**:
- Filebeat `service` field incorrect
- Logstash `[data_stream][dataset]` not set correctly

**Solutions**:
- Verify Filebeat input `service` field
- Check Logstash filter sets `[data_stream][dataset]` from `[service]`
- Verify data stream name: `logs-{service}-pt`

#### 5. Missing Fields in Kibana

**Symptoms**: Fields like `app_module` or `stream` are missing

**Causes**:
- Logger name doesn't match any pattern
- Grok parsing failed
- Field not added by Logstash filter

**Solutions**:
- Check logger name in raw `message` field
- Verify logger name matches pattern in `logstash.conf`
- Add new pattern if logger not covered
- Check Logstash logs for filter errors

#### 6. Authentication Errors (401/403)

**Symptoms**: Logstash can't write to Elasticsearch

**Causes**:
- Wrong user/password
- User doesn't have required role
- Role doesn't have required privileges

**Solutions**:
- Verify `LOGSTASH_WRITER_PASSWORD` in Logstash environment
- Check user exists: `curl -u elastic:PASSWORD "http://localhost:9200/_security/user/logstash_writer"`
- Verify role privileges: `curl -u elastic:PASSWORD "http://localhost:9200/_security/role/logstash_writer_pt"`
- Recreate user/role if needed

### Debugging Commands

#### Check Filebeat Status
```bash
docker exec filebeat filebeat test config
docker exec filebeat filebeat test output
docker logs filebeat | tail -100
```

#### Check Logstash Pipeline
```bash
docker exec logstash logstash --config.test_and_exit --path.settings=/usr/share/logstash/config
docker logs logstash | tail -100
```

#### Check Elasticsearch Data Streams
```bash
curl -u elastic:PASSWORD "http://localhost:9200/_data_stream/logs-*-pt?expand_wildcards=all"
```

#### Check Document Count
```bash
curl -u elastic:PASSWORD "http://localhost:9200/logs-django-pt/_count"
```

#### Test Logstash Output (Debug Mode)
Uncomment in `logstash.conf`:
```ruby
else {
  stdout { codec => rubydebug { metadata => true } }
}
```
Restart Logstash and check stdout for events.

---

## Summary

### What We Built

1. **6 Log Streams**: Django application writes to 6 separate log files (django, server, system, aws, network, app)
2. **1 Data Stream**: All logs flow to `logs-django-pt` Elasticsearch data stream
3. **15+ App Modules**: Application logs categorized into modules (parcels, auth, tenant, etc.)
4. **Complete Pipeline**: Django → Filebeat → Logstash → Elasticsearch → Kibana
5. **Security**: Role-based access control for Logstash writer
6. **Template**: Index template for automatic data stream creation

### Why This Architecture

- **Data Streams**: Optimized for time-series log data, automatic index management
- **Separate Files**: Isolate log types, easier debugging, efficient Filebeat processing
- **Structured Logging**: Parseable format enables field extraction and categorization
- **Multi-Product Support**: `group` field allows multiple products in same ELK cluster
- **Service Isolation**: Each service gets its own data stream (scalable to 6 services)
- **Module Categorization**: `app_module` field enables module-level filtering and analytics

### Current Status

✅ **Working**: Django service logs flowing to `logs-django-pt`  
⏳ **Planned**: Celery, Celerybeat, Flower, Nginx, React services

### Next Steps

1. **Add Celery Service**: Configure Celery to write to `celery.log`, add Filebeat input
2. **Add Celerybeat Service**: Configure Celerybeat to write to `celerybeat.log`
3. **Add Flower Service**: Redirect stdout to `flower.log` or use Docker log driver
4. **Production Deployment**: Adjust index template settings (shards, replicas, ILM)
5. **Monitoring**: Create Kibana dashboards for log analytics
6. **Alerting**: Set up alerts for ERROR/CRITICAL logs

---

**Document Version**: 1.0  
**Last Updated**: 2025-02-02  
**Maintained By**: Development Team

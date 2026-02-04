# ELK Stack for Parcel Tracking (PT) Application

This directory contains a complete ELK (Elasticsearch, Logstash, Kibana) stack configuration for collecting, processing, and visualizing logs from the Parcel Tracking application.

## 📋 Quick Overview

- **6 Data Streams** for different services (Django, Celery, Celerybeat, Flower, Nginx, React)
- **Automatic Log Categorization** into logical streams (django, server, aws, network, system, app, unknown)
- **Application Module Classification** for detailed analysis (auth, parcels, tenant, notification, etc.)
- **Secure Authentication** with X-Pack security and least-privilege access
- **Docker-Based Deployment** for easy setup and management

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available for Docker
- Ports 9200, 5601, 5044 available

### Setup Steps

1. **Clone and navigate to the directory**
   ```bash
   cd elk-stack
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env and set passwords (see below)
   ```

3. **Start Elasticsearch**
   ```bash
   docker compose up -d elasticsearch
   ```

4. **Set up passwords** (first time only)
   ```bash
   docker exec -it elasticsearch bin/elasticsearch-reset-password -i -u elastic
   docker exec -it elasticsearch bin/elasticsearch-reset-password -i -u kibana_system
   docker exec -it elasticsearch bin/elasticsearch-reset-password -i -u logstash_system
   ```

5. **Create security role and user**
   - Open Kibana: http://localhost:5601 (login as `elastic`)
   - Go to Dev Tools → Console
   - Run the commands from `elasticsearch-role-user-logstash-writer.json`

6. **Create index template**
   ```bash
   curl -u elastic:PASSWORD -X PUT "http://localhost:9200/_index_template/pt-logs" \
     -H "Content-Type: application/json" \
     -d @elasticsearch-index-template-pt-logs.json
   ```

7. **Start all services**
   ```bash
   docker compose up -d
   ```

8. **Verify**
   - Elasticsearch: http://localhost:9200
   - Kibana: http://localhost:5601
   - Check data streams: `GET _data_stream` in Kibana Dev Tools

## 📊 Data Streams

The stack creates **6 data streams** automatically when logs are ingested:

| Data Stream | Service | Purpose |
|------------|---------|---------|
| `logs-django-pt` | Django | Backend API logs |
| `logs-celery-pt` | Celery | Background task logs |
| `logs-celerybeat-pt` | Celerybeat | Scheduled task logs |
| `logs-flower-pt` | Flower | Celery monitoring logs |
| `logs-nginx-pt` | Nginx | Web server logs |
| `logs-react-pt` | React | Frontend logs |

**Naming Convention**: `{type}-{dataset}-{namespace}`
- Type: `logs` (fixed)
- Dataset: Service name (django, celery, etc.)
- Namespace: `pt` (Parcel Tracking group)

## 📁 Project Structure

```
elk-stack/
├── docker-compose.yml              # Service orchestration
├── elasticsearch.yml               # Elasticsearch configuration
├── kibana.yml                      # Kibana configuration
├── logstash.conf                   # Log processing pipeline
├── elasticsearch-index-template-pt-logs.json  # Index template for data streams
├── elasticsearch-role-user-logstash-writer.json  # Security role/user definition
├── README.md                       # This file
└── docs/
    ├── ELK-STACK-ARCHITECTURE-AND-DATA-STREAMS.md  # Complete architecture documentation
    ├── AUTH-AND-PRODUCTION.md      # Authentication and production notes
    ├── basic security setup.txt    # Security setup guide
    ├── OPENAPI-AND-BACKEND.md      # OpenAPI integration guide
    ├── TROUBLESHOOTING.md          # Common issues and solutions
    └── Pain points of using elk on your own.txt  # ELK challenges and considerations
```

## 📚 Documentation

### Main Documentation
- **[ELK Stack Architecture and Data Streams](docs/ELK-STACK-ARCHITECTURE-AND-DATA-STREAMS.md)** - Complete guide covering:
  - Data streams created and their purposes
  - How the ELK stack works (end-to-end flow)
  - Log processing pipeline details
  - Security architecture
  - Configuration files
  - Querying in Kibana
  - Troubleshooting

### Additional Guides
- **[Authentication and Production](docs/AUTH-AND-PRODUCTION.md)** - Security setup and production considerations
- **[Basic Security Setup](docs/basic%20security%20setup.txt)** - Step-by-step security configuration
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[OpenAPI and Backend](docs/OPENAPI-AND-BACKEND.md)** - Integration with backend services

## 🔐 Security

The stack uses X-Pack security with the following users:

| User | Purpose | Permissions |
|------|---------|-------------|
| `elastic` | Superuser | Full cluster access |
| `kibana_system` | Kibana operations | `.kibana*` indices |
| `logstash_system` | Logstash monitoring | Monitoring indices |
| `logstash_writer` | Log ingestion | `logs-*-pt` write/read only |

**Key Security Features**:
- All requests require authentication
- Least-privilege access for service accounts
- Passwords stored securely in Docker volumes
- No hardcoded credentials in configuration files

## 🔄 How It Works

1. **Log Collection**: Filebeat (on application server) collects logs and sends to Logstash
2. **Log Processing**: Logstash parses, categorizes, and enriches logs
3. **Data Storage**: Elasticsearch stores logs in data streams
4. **Visualization**: Kibana provides search, visualization, and dashboard capabilities

### Log Processing Pipeline

Logs are processed through the following stages:

1. **Input**: Beats protocol on port 5044
2. **Parse**: Grok pattern extracts log_level, logger_name, timestamp, message
3. **Categorize**: Logs categorized into streams (django, server, aws, network, system, app, unknown)
4. **Enrich**: App logs get app_module classification (auth, parcels, tenant, etc.)
5. **Output**: Data streams in Elasticsearch

See [ELK Stack Architecture](docs/ELK-STACK-ARCHITECTURE-AND-DATA-STREAMS.md) for detailed information.

## 🔍 Querying Logs in Kibana

### Create Data Views
- All PT services: `logs-*-pt`
- Individual services: `logs-django-pt`, `logs-celery-pt`, etc.

### Example Queries

```kql
# All PT logs
group:pt

# Django service errors
group:pt AND service:django AND log_level:ERROR

# Parcels module logs
group:pt AND stream:app AND app_module:parcels

# Critical errors across all services
group:pt AND log_level:CRITICAL
```

## 🛠️ Configuration Files

- **docker-compose.yml**: Service definitions, health checks, volumes, networks
- **elasticsearch.yml**: Cluster settings, security, network configuration
- **kibana.yml**: Server settings, Elasticsearch connection, reporting
- **logstash.conf**: Input, filter, and output pipeline configuration
- **elasticsearch-index-template-pt-logs.json**: Index template for data streams
- **elasticsearch-role-user-logstash-writer.json**: Security role and user definitions

## 🐛 Troubleshooting

Common issues and solutions are documented in [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

### Quick Checks

```bash
# Check service status
docker compose ps

# View logs
docker logs elasticsearch
docker logs kibana
docker logs logstash

# Test Elasticsearch
curl -u elastic:PASSWORD http://localhost:9200/_cluster/health

# List data streams
curl -u elastic:PASSWORD http://localhost:9200/_data_stream
```

## 📝 Environment Variables

Create a `.env` file with the following (see `.env.example`):

```env
ELASTICSEARCH_PASSWORD=<kibana_system_password>
LOGSTASH_WRITER_PASSWORD=<logstash_writer_password>
LOGSTASH_SYSTEM_PASSWORD=<logstash_system_password>
```

**⚠️ Important**: Never commit `.env` to version control!

## 🚦 Service Health

All services include health checks:

- **Elasticsearch**: Checks HTTP endpoint (200/401 indicates healthy)
- **Kibana**: Checks API status endpoint
- **Logstash**: Checks node stats endpoint

Services start in order: Elasticsearch → Kibana/Logstash (after ES is healthy)

## 📈 Next Steps

1. **Configure Filebeat** on your application server to send logs to Logstash
2. **Create Kibana Dashboards** for visualization
3. **Set up Index Lifecycle Management (ILM)** for data retention
4. **Configure Alerts** for critical errors
5. **Enable TLS/HTTPS** for production deployments

## 📖 Additional Resources

- [Elasticsearch Data Streams Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/data-streams.html)
- [Logstash Configuration Reference](https://www.elastic.co/guide/en/logstash/current/configuration.html)
- [Kibana User Guide](https://www.elastic.co/guide/en/kibana/current/index.html)

## 📄 License

This configuration is part of the Parcel Tracking application.

---

**For detailed information, see [ELK Stack Architecture and Data Streams](docs/ELK-STACK-ARCHITECTURE-AND-DATA-STREAMS.md)**

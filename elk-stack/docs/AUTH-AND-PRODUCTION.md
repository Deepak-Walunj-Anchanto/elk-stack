# Authentication Setup & Production Notes

## Your Current Setup (Verified)

You followed a sound flow for basic auth. Below is a concise review and corrections.

### What You Did Right

1. **X-Pack security** – `xpack.security.enabled=true` is correct.
2. **Separate users** – Using `elastic`, `kibana_system`, `logstash_system`, and a custom `logstash_writer` is the right pattern.
3. **Least privilege** – `logstash_writer` role with only `pt-logs-*`, `express-logs-*`, `fastapi-logs-*` and write privileges is appropriate.
4. **Kibana keystore** – Using `kibana-keystore` for `elasticsearch.password` is a valid option (we also support env var for simplicity).
5. **Logstash monitoring** – Using `logstash_system` for monitoring and `logstash_writer` for writing is correct.

### Typo in Your Steps

- The step **"ADD KIBANA ENV"** that adds `xpack.monitoring.*` and `LOGSTASH_WRITER_PASSWORD` is for **Logstash**, not Kibana. It should read **"ADD LOGSTASH ENV"**.

### Production-Grade Improvements Applied

| Area | Change |
|------|--------|
| **Secrets** | Passwords moved to `.env` (from `.env.example`). No hardcoded passwords in `docker-compose.yml`. |
| **Config files** | Separate `elasticsearch.yml` and `kibana.yml` (like `logstash.conf`) for clear, file-based config. |
| **Healthchecks** | Added healthchecks for Elasticsearch, Kibana, and Logstash so Compose knows when services are ready. |
| **Start order** | Kibana and Logstash use `depends_on: elasticsearch: condition: service_healthy` so they start after ES is up. |
| **Restart** | `restart: unless-stopped` so containers come back after reboot. |
| **Kibana password** | Can use `ELASTICSEARCH_PASSWORD` in `.env` instead of keystore for simpler deployment (keystore still valid). |

### Optional Next Steps for Production

1. **TLS for Elasticsearch/Kibana**  
   - Use `xpack.security.http.ssl.enabled: true` and certs in ES; configure Kibana with `elasticsearch.ssl.*` and `server.ssl.*` for HTTPS.

2. **Single-node limitation**  
   - `discovery.type=single-node` is fine for dev/small prod. For HA, run a multi-node cluster with `discovery.seed_hosts` and `cluster.initial_master_nodes`.

3. **Resource limits**  
   - Add `deploy.resources.limits` (memory/CPU) in `docker-compose.yml` to avoid one service starving others.

4. **Backups**  
   - Use snapshot/restore (e.g. S3/FS repo) for indices and Kibana saved objects.

5. **`.env`**  
   - Ensure `.env` is in `.gitignore` and never committed; use `.env.example` as a template only.

### API Key Authentication (http_api_key)

Elasticsearch supports key-based authentication. With `xpack.security.enabled: true`, API keys are already enabled. Use them for scripts, backends, or CI instead of username/password.

#### Create an API key

You need a user with permission to manage API keys (e.g. `elastic`). From your host (replace `localhost` with your ES host/port if different).

**Linux / macOS / Git Bash:**

```bash
curl -X POST "http://localhost:9200/_security/api_key" \
  -u "elastic:YOUR_ELASTIC_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-api-key", "expiration": "30d", "role_descriptors": {}}'
```

**Windows CMD** (single quotes break the JSON; use double quotes and escape inner `"` with `\"`):

```cmd
curl -X POST "http://localhost:9200/_security/api_key" -u "elastic:YOUR_ELASTIC_PASSWORD" -H "Content-Type: application/json" -d "{\"name\": \"my-api-key\", \"expiration\": \"30d\", \"role_descriptors\": {}}"
```

**Windows PowerShell** (same as CMD; escape inner double quotes):

```powershell
curl -X POST "http://localhost:9200/_security/api_key" -u "elastic:YOUR_ELASTIC_PASSWORD" -H "Content-Type: application/json" -d "{\"name\": \"my-api-key\", \"expiration\": \"30d\", \"role_descriptors\": {}}"
```

- **`role_descriptors: {}`** – key has same permissions as the user who created it (`elastic` = full access).
- For restricted keys, set [role_descriptors](https://www.elastic.co/guide/en/elasticsearch/reference/current/security-api-create-api-key.html) with specific privileges.

Response example:

```json
{
  "id": "VuaCfGcBCjbkPDmH5-I5",
  "name": "my-api-key",
  "api_key": "ui2lp2axTemsyoUg4dvsgB",
  "encoded": "VuaCfGcBCjbkPDmH5-I5:ui2lp2axTemsyoUg4dvsgB"
}
```

Use the **`encoded`** value in the `Authorization` header.

#### Use the API key in requests

```bash
export API_KEY="VuaCfGcBCjbkPDmH5-I5:ui2lp2axTemsyoUg4dvsgB"
export ES_URL="http://localhost:9200"

curl -X GET "${ES_URL}/_cat/indices?v=true" \
  -H "Authorization: ApiKey ${API_KEY}"
```

From a backend (e.g. Node/Python), send the same header:

- **Header:** `Authorization: ApiKey <encoded_value>`

#### Optional: store in .env

For backend or scripts, you can put the encoded key in `.env` (see `.env.example`) and load it as `ELASTICSEARCH_API_KEY`. Never commit the key to git.

#### Revoke / list API keys

```bash
# List API keys (as elastic user)
curl -X GET "http://localhost:9200/_security/api_key" -u "elastic:YOUR_ELASTIC_PASSWORD"

# Revoke by name
curl -X POST "http://localhost:9200/_security/api_key/_revoke" \
  -u "elastic:YOUR_ELASTIC_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-api-key"}'
```

---

### Quick Start After Clone

```bash
cp .env.example .env
# Edit .env and set:
#   ELASTICSEARCH_PASSWORD  = kibana_system password
#   LOGSTASH_WRITER_PASSWORD = logstash_writer user password
#   LOGSTASH_SYSTEM_PASSWORD = logstash_system password

docker compose up -d elasticsearch
# Wait for healthy, then reset passwords if first run:
#   docker exec -it elasticsearch bin/elasticsearch-reset-password -i -u elastic
#   docker exec -it elasticsearch bin/elasticsearch-reset-password -i -u kibana_system
#   docker exec -it elasticsearch bin/elasticsearch-reset-password -i -u logstash_system

# Create logstash_writer role and user in Kibana Dev Tools (see your steps), then:
docker compose up -d kibana logstash
```

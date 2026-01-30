# ELK Stack Troubleshooting

## "Connection refused" to Elasticsearch (Kibana / Logstash)

If you see:

- **Kibana:** `[ERROR][elasticsearch-service] Unable to retrieve version information from Elasticsearch nodes. connect ECONNREFUSED 172.19.1.2:9200`
- **Logstash:** `Connect to elasticsearch:9200 [elasticsearch/172.19.1.2] failed: Connection refused`

then **Elasticsearch is not running or not yet listening** on port 9200.

**If Elasticsearch logs show** `bound_addresses {127.0.0.1:9200}` or `publish_address {127.0.0.1:9200}`, it is binding to localhost only. Other containers cannot reach it. Ensure `elasticsearch.yml` contains:

```yaml
network.host: 0.0.0.0
```

Then restart Elasticsearch: `docker compose up -d elasticsearch`.

### 1. Run Compose from the correct directory

Compose must be run from the folder that contains `docker-compose.yml`:

```powershell
cd C:\Users\deepak.walunj\Desktop\elk-stack\elk-stack
docker compose up -d
```

If you run from `elk-stack` (parent) without `-f elk-stack/docker-compose.yml`, Compose may use another file or not start the stack.

### 2. Start Elasticsearch first and wait

Elasticsearch can take 60–90 seconds to become ready. Start only Elasticsearch and wait until it’s healthy:

```powershell
cd C:\Users\deepak.walunj\Desktop\elk-stack\elk-stack
docker compose up -d elasticsearch
```

Wait until the healthcheck passes (or check manually):

```powershell
docker compose ps
# elasticsearch should show "healthy"

# Or test ES directly (from host; use your elastic user password if prompted):
curl -u elastic:YOUR_PASSWORD http://localhost:9200
```

Then start the rest:

```powershell
docker compose up -d kibana logstash
```

### 3. If Elasticsearch is not running or keeps exiting

List containers:

```powershell
docker ps -a
```

If `elasticsearch` is missing or status is **Exited**, check its logs:

```powershell
docker logs elasticsearch
```

Common causes:

- **Bootstrap check / memory:** On Windows/WSL, increase Docker memory or set `ES_JAVA_OPTS=-Xms512m -Xmx512m` (already in compose). For "max virtual memory areas vm.max_map_count [65530] is too low", set it on the host (e.g. WSL):  
  `sysctl -w vm.max_map_count=262144`
- **Crash on start:** Look at the end of `docker logs elasticsearch` for the exact error (e.g. config, permission, or resource issue).

### 4. Verify the stack

From the **elk-stack** directory (where `docker-compose.yml` is):

```powershell
docker compose ps
docker compose logs elasticsearch --tail 50
```

All three services should be on the same Docker network and resolve the hostname `elasticsearch`. Once Elasticsearch is up and healthy, Kibana and Logstash will connect after a short delay.

---

## "Invalid version of beats protocol: 71" / "Invalid version of beats protocol: 69"

If Logstash logs show:

- `Invalid version of beats protocol: 71`
- `Invalid version of beats protocol: 69`

**Cause:** Something is sending **HTTP** (e.g. a `GET` request) to the **Beats** port **5044**. The numbers 71 and 69 are the ASCII codes for `G` and `E` — the start of `"GET"`. The Beats input expects the **binary Lumberjack/Beats protocol**, not HTTP.

**What to do:**

1. **Do not** open `http://localhost:5044` in a browser or call `curl http://localhost:5044`.
2. **Do not** use an HTTP health check or HTTP client against port 5044. Only **Beats-compatible agents** (Filebeat, Metricbeat, etc.) should connect to 5044.
3. If you use **Elastic Agent** or **Filebeat** to send logs to Logstash, point them at `localhost:5044` (or your Logstash host) and ensure they use the **Beats/Lumberjack** output, not HTTP.
4. If you want to send logs over HTTP (e.g. from an app or script), add a separate **HTTP input** in Logstash on a *different* port (e.g. 8080) and send JSON there; do not use port 5044 for HTTP.

**Summary:** Port 5044 is for Beats protocol only. Anything sending plain HTTP to 5044 will trigger these errors. Find what is connecting to 5044 (browser, curl, health check, or misconfigured agent) and stop it or point it to the correct protocol/port.

# Backend (FastAPI)

Production-oriented FastAPI app that talks to Elasticsearch using **API key auth only** (no basic auth).

## Structure and data flow

```
Client (browser/API consumer)
    → FastAPI (main.py)
        → Router (routes/elasticsearch.py)   ← validate input, map errors
            → Service (services/elasticsearch_client.py)   ← API key auth, HTTP to ES
                → Elasticsearch (GET /_application/analytics, etc.)
```

- **Routes**: Thin; validate path/query, call service, map `ElasticsearchClientError` to HTTP (404, 422, 503). No ES logic here.
- **Service**: Single place for ES calls. Uses `ELASTICSEARCH_API_KEY` in `Authorization: ApiKey <key>`. No basic auth.
- **Settings**: `ELASTICSEARCH_URL`, `ELASTICSEARCH_API_KEY` from `.env` (see `.env.example`).

## Behavioral analytics (OpenAPI)

- `GET /lms/v1/es/application/analytics` → ES `GET /_application/analytics` (list collections).
- `GET /lms/v1/es/application/analytics/{name}` → ES `GET /_application/analytics/{name}` (one collection).

All requests to Elasticsearch use API key only.

## Setup

```bash
cp .env.example .env
# Set ELASTICSEARCH_API_KEY to the encoded value from ES POST /_security/api_key

pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Env

| Variable | Description |
|----------|-------------|
| `API_PREFIX` | URL prefix for API (e.g. `/lms/v1`). |
| `ELASTICSEARCH_URL` | Elasticsearch base URL (e.g. `http://localhost:9200`). |
| `ELASTICSEARCH_API_KEY` | Encoded API key from `POST /_security/api_key`. Required for ES routes. |

## Troubleshooting: 422 "Elasticsearch rejected the request"

When you get **422 Unprocessable Content** with `"message": "Elasticsearch rejected the request"`, the response now includes **`es_reason`** with the exact error from Elasticsearch. Common causes:

| `es_reason` / cause | Fix |
|---------------------|-----|
| **403 – "action [...] is unauthorized"** or **"is unauthorized for API key"** | The API key lacks the required privilege. The behavioral analytics API needs **`manage_search_application`** (and related) cluster privilege. Create an API key with the **`elastic`** user (full access) or a role that has `manage_search_application`. |
| **400 – "no handler for uri"** | The Elasticsearch version may not support `GET /_application/analytics` (added in **8.8.0**). Upgrade ES or call `GET /_application/analytics/{name}` with a specific collection name. |
| **400 – bad request / validation** | Check the request path and that the cluster has behavioral analytics enabled (technical preview; may require license/feature). |

After the fix, call the endpoint again; the **`es_reason`** field in the JSON response will show the current Elasticsearch error.

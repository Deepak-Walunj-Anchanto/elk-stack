# Multi-tenant architecture (1 DB per tenant)

This codebase implements a strict tenant-isolation model where each tenant has its own PostgreSQL database. The core logic lives in `apps/tenant_manager/`. This document explains the boot process, tenant detection, context management, ORM/database routing, Celery, Channels, caching, management commands, and how to operate/debug the system.

### High-level overview

- Each tenant is represented by a `TenantContext` which holds:
  - `id`: external tenant identifier (e.g., domain or slug)
  - `primary_alias`: the Django database alias for writes
  - `replica_aliases`: zero or more read replica aliases for reads/load-balancing
- At process start, a bootstrap sequence initializes:
  1) `tenant_context_manager` (discovers tenants, builds `TenantContext`s)
  2) `django_orm` (registers databases and read replicas in `django.db.connections`)
  3) `celery_manager` (patches beat schedule and registers signals)
- At request/task time, a tenant context is pushed to a thread-/context-local stack managed by `tls_tenant_manager`. All tenant-aware behaviors (DB routing, cache keying, Celery headers, etc.) flow from the current `TenantContext`.

---

## Bootstrapping and initialization

### AppConfig entrypoint

`apps/tenant_manager/apps.py` is the entrypoint via Django AppConfig `ready()`:

```12:13:apps/tenant_manager/apps.py
    def ready(self):
        app_bootstrapper.run()
```

`app_bootstrapper` (in `apps/tenant_manager/bootstrap.py`) runs a fixed sequence:

```14:22:apps/tenant_manager/bootstrap.py
    def _run_bootstrap_sequence(self):
        for component in self._bootstrap_sequence:
            logger.info("Bootstrapping component {component_name}".format(component_name=component.name))
            component.bootstrap()
```

The sequence is `[tenant_context_manager, django_orm, celery_manager]`.

Why this order matters:
- `tenant_context_manager` needs DB config to create contexts, but it reads the parsed settings via `config.settings.utils.parse_database_settings` (not the live connection registry), so it can run first to compute contexts.
- `django_orm` then registers live database configurations and replica aliases into `django.db.connections` using the same parsed settings.
- `celery_manager` finally patches `app.conf.beat_schedule` per-tenant and registers Celery signals/db-signals.

---

## Tenant model and context

### TenantContext

`apps/tenant_manager/tenant_context.py` defines `TenantContext`. Key points:
- `TenantContext.from_id(id)` normalizes IDs to aliases by replacing `.` and `-` with `_`.
- `primary_alias` is where all writes go.
- `replica_aliases` is a list of read-only DB aliases for reads.
- `get_read_alias()` randomly chooses a replica when available, otherwise uses the primary (safe fallback).
- `get_write_alias()` always returns the primary.

### Context storage (TLS)

`apps/tenant_manager/tenant_manager.py` keeps a stack of contexts in a `contextvars.ContextVar`. Important behaviors:
- `push_tenant_context(context)` pushes a new tenant scope (useful for nested contexts/tasks).
- `pop_tenant_context()` pops the top-most context.
- `current_tenant_context` returns the active context (top of the stack). A default base context is seeded for safety.

### Resolving and binding contexts

`apps/tenant_manager/with_tenant_context.py` provides a `tenant_context_bind` context manager/decorator:
- Accepts a tenant `id` or alias or a `TenantContext` instance.
- Resolves via `tenant_context_manager.get_by_id()` or `get_by_alias()`.
- Pushes the context on enter; pops on exit.

This is used by management commands and tests to ensure code runs within the correct tenant scope.

---

## Discovering tenants and database registration

### Parsing settings and building contexts

`apps/tenant_manager/tenant_context_manager.py` boots by calling `parse_database_settings()` (from `config.settings.utils`) to discover tenants. For each `tenant_id` it:
- Asks the ORM manager for that tenant’s replica aliases.
- Builds a `TenantContext.from_id(tenant_id, replica_aliases=...)` and stores it in an in-memory dict for fast lookup.

This creates the authoritative mapping from external `tenant_id` to `TenantContext` (including replicas).

### ORM manager: connection registration and replicas

`apps/tenant_manager/orms/manager.py` is responsible for registering live database connections with Django and mapping replicas.

Highlights:
- Reads a template `DATABASES` config from settings and merges per-tenant configs returned by `parse_database_settings()`.
- For each tenant:
  - Registers the primary alias (normalized ID) as a Django connection via `register_config()`.
  - Parses `replicas` (array) from the tenant config, creates replica aliases like `<tenant_alias>_replica_1`, merges overrides, and registers each as a Django connection.
  - Stores mapping `tenant_alias -> [replica_aliases...]` for fast lookup.
- Exposes helpers:
  - `get_tenant_replica_aliases(tenant_id)` to return replica alias list.
  - `get_parent_tenant_for_replica(replica_alias)` and `is_replica_alias(alias)`.
- Maintains `reserved_aliases` (e.g., infrastructure DBs) and `skip_migration_aliases` via settings to avoid accidental migrations.
- Refreshes stale DB connections in Celery workers.

Replica config design:
- Tenant config supports a `replicas: [...]` array. Each item is a dict of overrides (e.g., host/port/user) applied on top of the primary’s config to form a new read-only connection.

Example (illustrative):

```python
DATABASES = {
  "default": {...}  # template
}

# parse_database_settings() should return something like:
{
  "tenant-a": {
    "NAME": "db_tenant_a",
    "HOST": "primary.host",
    "ENGINE": "django.db.backends.postgresql",
    "replicas": [
      {"HOST": "replica1.host", "USER": "readonly"},
      {"HOST": "replica2.host", "USER": "readonly"}
    ]
  },
  "tenant-b": {"NAME": "db_tenant_b", "HOST": "primary.host"}  # no replicas
}
```

---

## Tenant detection in HTTP and WebSocket requests

### DRF/HTTP middleware

`apps/tenant_manager/middlware_api.py` implements `ContextAwareAPIMiddleware`:

Resolution order for tenant ID:
1) Optional resolver callable `TENANT_ROUTER_MIDDLEWARE_SETTINGS["TENANT_ID_RESOLVER"]` (import path of `callable(request) -> tenant_id`)
2) `x-tenant-id` HTTP header
3) If `TEST` env var is set, defaults to `default`

If the resolved tenant ID is not found in memory, the middleware:
- Tries to map the incoming header (often a branded CNAME) to a tenant via `BrandedURLTenantConfig` on the special `CELERY_BEAT_DB_ALIAS` connection.
- Caches the mapping using `apps.common.cache_wrapper.cache` for `TENANT_BRANDER_CACHE_RESOLVER` seconds.
- If still not found, returns `400` with an error payload.

On success:
- Pushes the tenant context (`tls_tenant_manager.push_tenant_context(...)`).
- Calls the view.
- Pops the context in a `finally` block.

Whitelist handling:
- Some health endpoints are whitelisted and bypass tenant resolution.

### Channels/WebSocket middleware

`apps/tenant_manager/middleware_channel.py` implements `ContextAwareChannelMiddleware` for ASGI:

Resolution order:
1) `x-tenant-id` header (set by NGINX from `$host` in many deployments)
2) `host` header (fallback)
3) `TEST` env var -> `default`

Optionally, a query param `x-tenant-id` can override for development/testing.

Authentication:
- If `authorization` token is present in the query string, it’s decoded and a user is loaded; otherwise `AnonymousUser`.

Context handling:
- Resolves tenant once, pushes context, runs the inner app, and pops context in `finally`.

---

## Database routing

`apps/tenant_manager/database_router.py` provides `TenantDatabaseRouter` with explicit read/write routing:

- Special-case: all `django_celery_beat` models are forced to `CELERY_BEAT_DB_ALIAS`.
- Reads (`db_for_read`):
  - Use `tls_tenant_manager.current_tenant_context.get_read_alias()` which randomly chooses one of the configured replicas; falls back to primary if none.
- Writes (`db_for_write`):
  - Always use `current_tenant_context.get_write_alias()` -> primary alias.
- `allow_migrate`: blocks migrations for designated app labels (e.g., beat tables) from tenant databases.
- `allow_relation`: allowed by default (relations are within same tenant’s primary/replicas).
- Tracks a `_routing_history` list for debugging and has a `test_replica_routing` management command.

To enable routing, ensure settings include:

```python
DATABASE_ROUTERS = [
  "apps.tenant_manager.database_router.TenantDatabaseRouter",
]
```

---

## Celery integration

`apps/tenant_manager/celery/manager.py` and `apps/tenant_manager/celery/signals.py` handle Celery multi-tenancy.

Beat schedule patching:
- At bootstrap, the manager duplicates `app.conf.beat_schedule` per tenant, renaming schedules to a normalized form and injecting headers with `tenant_id`.
- Schedule name format uses `construct_schedule_name(tenant_alias, schedule_name)` to get a stable name: `<tenant_alias>_<SERVICE_NAME>_<schedule_name>`.

Signals:
- `@before_task_publish`: ensures `tenant_id` header is present on outgoing tasks (pulls from current TLS).
- `@task_prerun`: extracts `tenant_id` from the request and pushes a corresponding context into TLS before the task runs.
- `@worker_process_init`: refreshes stale DB connections for all registered ORMs.

DB signals for beat:
- `pre_save` on `django_celery_beat.PeriodicTask` normalizes the task name to per-tenant format and injects headers with `tenant_id` if missing.

Usage:
- When creating periodic tasks or sending tasks, you do not need to manually pass tenant info; the middleware and signals handle propagation.

---

## Tenant-aware cache

`apps/tenant_manager/cache/cache.py` defines a `TenantAwareRedisClient` that prefixes Redis keys with the current tenant alias. Configure Django cache to use this client as `client_class` to achieve per-tenant isolation of keys.

Example (illustrative):

```python
CACHES = {
  "default": {
    "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": "redis://.../0",
    "OPTIONS": {
      "CLIENT_CLASS": "apps.tenant_manager.cache.cache.TenantAwareRedisClient",
    },
  }
}
```

---

## Management commands and testing utilities

Management commands (all under `apps/tenant_manager/management/commands/`):
- `migrate`:
  - Adds `--tenant-id` to migrate a specific tenant when using a template alias.
  - If a connection alias is directly given and points to a replica, it resolves the parent tenant for context.
  - Guards against migrating reserved aliases.
- `migrate_all`: Iterates over all tenants from `tenant_context_manager` and runs `migrate` per tenant.
- `makemigrations`: Runs under a fixed tenant context (`localhost`) to ensure stable state.
- `shell` and `tenant_createsuperuser`: Require `--tenant-id` and bind the tenant context for the session.
- `test_replica_routing`: Prints read/write routing decisions, helpful for verifying load-balancing.

Testing utilities:
- `TenantAwareTestRunner` forces tests to run under tenant `default` by default (override with context binding where needed).
- Comprehensive pytest suite in `apps/tenant_manager/tests.py` covers contexts, router behavior, ORM manager replica parsing, and error handling.

---

## Settings and configuration reference

Important settings referenced by the tenant manager:

- `TENANT_ROUTER_MIDDLEWARE_SETTINGS`: dict that may include `TENANT_ID_RESOLVER = "path.to.callable"`.
- `TENANT_ROUTER_SERVICE_NAME`: used in Celery schedule name normalization.
- `RESERVED_CONN_ALIASES`: set of DB aliases that should never be migrated as tenants.
- `SKIP_MIGRATION_CONN_ALIASES`: set of DB aliases that are present but must not receive migrations.
- `CELERY_BEAT_DB_ALIAS`, `CELERY_BEAT_APP_LABEL`: special database/app label for beat models (kept outside tenant DBs).
- `TENANT_BRANDER_CACHE_RESOLVER`: cache TTL for branded URL -> tenant_id resolution.
- `DATABASE_ROUTERS`: must include `apps.tenant_manager.database_router.TenantDatabaseRouter`.
- `CACHES.default.OPTIONS.CLIENT_CLASS`: should point to `apps.tenant_manager.cache.cache.TenantAwareRedisClient`.

Notes on database settings:
- `config.settings.utils.parse_database_settings()` must return a mapping `{ tenant_id -> db_config }`, where `db_config` may contain a `replicas: [ { override }, ... ]` array to define read replicas. Each `override` merges into the primary config to define a replica connection.

Alias (whitelabeled domain) support:
- `db_config` may optionally include an `aliases` list of external hostnames that should resolve to the canonical `tenant_id`.
- Example:
```json
{
  "asendia-dev.anchanto.com": {
    "NAME": "asendia",
    "ENGINE": "django.db.backends.postgresql",
    "aliases": ["asendia.com", "www.asendia.com"],
    "replicas": [{"HOST": "replica.host"}]
  }
}
```
- During bootstrap, the tenant manager builds an alias map so that requests for `asendia.com` (and `www.asendia.com`) transparently resolve to tenant `asendia-dev.anchanto.com`.

---

## Request lifecycle summary

1) HTTP/ASGI middleware extracts tenant ID (resolver/header/host/test), resolves to a `TenantContext` (with branded-URL fallback and caching for HTTP), and pushes it to TLS.
2) View/business logic runs; any ORM access will be routed by `TenantDatabaseRouter`:
   - Reads -> random replica (if any), otherwise primary
   - Writes -> primary
3) Response is returned, and the tenant context is popped.

For Celery tasks:
1) When a task is published, a `tenant_id` header is added if missing.
2) Workers on `task_prerun` set the TLS context based on the header before running the task.
3) Any ORM/cache usage inside the task is tenant-aware.

---

## Operational guidance

### Add a new tenant
1) Ensure `parse_database_settings()` returns a new entry for the tenant with its primary config and optional `replicas`.
2) Restart processes so `tenant_context_manager` and `django_orm` bootstrap include the new tenant.
3) Run migrations for the tenant:
   - If using template alias: `python manage.py migrate --database <template_alias> --tenant-id <tenant_id>`
   - If direct alias is present: `python manage.py migrate --database <normalized_tenant_alias>`

### Migrate all tenants
```bash
python manage.py migrate_all --database <template_alias>
```

### Debug routing
```bash
python manage.py test_replica_routing --tenant-id <tenant_id> --iterations 20
```

### Common pitfalls
- Missing `x-tenant-id` header: HTTP middleware returns 400 unless a resolver is configured.
- Using the wrong DB alias for migrations: Prefer `--tenant-id` with a template alias or use the exact tenant alias.
- Replica-only deployments: If `replica_aliases` is empty, reads correctly fall back to primary.
- Channels override: Query param `x-tenant-id` is allowed only for dev/testing; ensure headers are set correctly in production.

---

## Example end-to-end flow (HTTP)

1) NGINX sets `x-tenant-id: <tenant-domain>` header.
2) `ContextAwareAPIMiddleware` reads the header, resolves `TenantContext` (brand mapping if needed), and pushes it.
3) View queries models:
   - `SELECT` operations are routed to replicas when present
   - `INSERT/UPDATE/DELETE` go to primary
4) Response returned; context popped.

## Example end-to-end flow (Celery beat -> worker)

1) At boot, beat schedule is replicated per tenant; names normalized; headers get `tenant_id`.
2) Beat publishes a task with `tenant_id` header.
3) Worker `task_prerun` pushes the tenant context; task runs in the right DB(s).
4) After execution, context is popped by Celery signal lifecycle.

---

## Related files (reference)

- Boot/Config
  - `apps/tenant_manager/apps.py`
  - `apps/tenant_manager/bootstrap.py`
  - `apps/tenant_manager/conf.py`
- Context & TLS
  - `apps/tenant_manager/tenant_context.py`
  - `apps/tenant_manager/tenant_manager.py`
  - `apps/tenant_manager/with_tenant_context.py`
  - `apps/tenant_manager/tenant_context_manager.py`
- ORM/DB routing
  - `apps/tenant_manager/orms/manager.py`
  - `apps/tenant_manager/database_router.py`
- HTTP/ASGI
  - `apps/tenant_manager/middlware_api.py`
  - `apps/tenant_manager/middleware_channel.py`
- Celery
  - `apps/tenant_manager/celery/manager.py`
  - `apps/tenant_manager/celery/signals.py`
  - `apps/tenant_manager/celery/beat/db_signals.py`
- Cache
  - `apps/tenant_manager/cache/cache.py`
- Management commands & tests
  - `apps/tenant_manager/management/commands/*.py`
  - `apps/tenant_manager/tests.py`



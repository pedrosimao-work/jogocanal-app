# ADR-001: Deploy FastAPI through Passenger using an ASGI-to-WSGI adapter

## Status

Accepted

## Date

2026-08-05

## Context

The JogoCanal application is being developed with FastAPI and deployed through an existing DirectAdmin shared-hosting account.

The hosting account provides:

- Python 3.11.15 through Setup Python App
- Apache and Passenger
- Environment variables
- MariaDB
- Cron Jobs
- Terminal access
- HTTPS and subdomain management

The hosting environment does not provide:

- NGINX Unit
- Native ASGI configuration
- Persistent Uvicorn process management
- User-level systemd services
- Reverse-proxy configuration for a custom Uvicorn process

DirectAdmin Setup Python App requires a WSGI callable.

FastAPI is an ASGI application.

## Decision

JogoCanal will remain a FastAPI application and will be exposed to Passenger through `a2wsgi.ASGIMiddleware`.

Passenger loads the WSGI callable named `application` from `wsgi.py`.

The adapter is created lazily inside the active Passenger worker when the first request is received.

It must not be created during startup-file import because Passenger's process lifecycle caused the adapter's event-loop thread to become unavailable, resulting in requests that never completed.

## Production request flow

```text
Browser or Android WebView
        ↓
app.jogocanal.com
        ↓
Apache and Passenger
        ↓
wsgi.py
        ↓
a2wsgi.ASGIMiddleware
        ↓
FastAPI application
        ↓
SQLAlchemy and MariaDB
```

## Operational configuration

- Python runtime: 3.11.15
- Application root: `/home3/jogocavk/jogocanal_app`
- Startup file: `wsgi.py`
- Entry point: `application`
- Public URL: `https://app.jogocanal.com`
- Scraper execution: separate CLI command
- Scheduling: DirectAdmin Cron Jobs
- Production database: DirectAdmin MariaDB

## Consequences

The codebase remains a FastAPI application and retains:

- FastAPI routers
- Dependency injection
- Pydantic validation
- Response models
- Automatic OpenAPI generation
- Swagger UI
- FastAPI testing
- SQLAlchemy integration
- Alembic migrations
- Jinja rendering

The production environment does not provide native ASGI server behaviour.

The application must not depend on:

- WebSockets
- Long-lived asynchronous connections
- ASGI streaming
- FastAPI background tasks for scraper execution

The scraper will remain independent from HTTP request processing and will run through a scheduled CLI command.

## Alternatives considered

### External ASGI hosting

Rejected for the initial deployment because it would add hosting cost and divide the application, database, and operational tooling across different providers.

### Replacing FastAPI with Flask

Rejected because JogoCanal is intended to demonstrate FastAPI, Pydantic, and modern API development.

### Persistent Uvicorn process

Unavailable on the current shared-hosting plan.

### ASGI adapter created during module import

Rejected because Passenger requests hung until the worker process was terminated.

## Verification

The deployed application returned:

```text
HTTP/2 200
```

from:

```text
https://app.jogocanal.com/health
```

with:

```json
{
  "status": "ok",
  "framework": "FastAPI"
}
```

The public OpenAPI JSON and Swagger UI were also verified through the HTTPS subdomain.
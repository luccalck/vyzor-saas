# VYZOR — Integrated Management & AI Automation Platform

VYZOR is a complete application for data management, indicator analysis, process automation, and integration with external sources. The project consists of a FastAPI backend (Python 3.11), persistence via SQLAlchemy/Alembic, static frontend pages for administration and testing, plus modular connectors for CRMs/ERPs and external databases.

## Table of Contents
- Overview
- Key Features
- Architecture
- Project Structure
- Requirements
- Configuration
- Local Execution
- Database & Migrations
- Automated Tests
- External Integrations (Phase 5)
- Main Endpoints
- Frontend (Supa pages)
- Deploy (Docker & CI/CD)
- Security
- Troubleshooting
- Roadmap
- Contributing
- License

## Overview
- Multi-tenant platform with JWT authentication.
- Structured data persistence with SQLAlchemy and Alembic.
- Custom dashboards and indicators, with materialization and task scheduling.
- Reference connectors (e.g., `mysql_readonly`, `hubspot`) with configuration, test, and health endpoints.
- Frontend pages for login, integrations, and quick configuration.

## Key Features
- User authentication (`POST /login`) and profiles.
- Business dashboards (user/admin) and custom indicators.
- ETL, cache, and materialization with schedulers.
- Per-client integrations with secure credential storage and connection tests.
- Aggregated health checks per connector.

## Architecture
- Backend: FastAPI 0.116, SQLAlchemy 2.0, Pydantic v2, Alembic.
- Frontend: static HTML/JS pages under `frontend/supa` consuming backend APIs.
- Database: PostgreSQL (via `DATABASE_URL`).
- Integrations: modular connectors via `ConnectorRegistry` and a base `Connector` class.
- Deploy: Docker and pipelines in `.github/workflows`.

## Project Structure
```
vyzor-saas/
├── backend/
│   ├── app/                # Main backend code
│   │   ├── main.py         # FastAPI entrypoint
│   │   ├── auth.py         # JWT authentication
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── crud.py         # Persistence operations
│   │   ├── schemas.py      # Pydantic schemas
│   │   ├── routes/         # Route modules (e.g., integrations)
│   │   ├── conectores/     # Connectors (mysql_readonly, hubspot)
│   │   └── scheduler_service.py, cache_service.py, etc.
│   ├── requirements.txt    # Backend dependencies
│   ├── migrations/         # Auxiliary SQL scripts
│   └── tests/              # Automated tests
├── frontend/
│   └── supa/               # Static admin/test pages (legacy)
├── frontend-next/          # Next-gen frontend (in development)
├── alembic/                # Alembic migrations
├── sql/                    # Legacy schema reference
├── seeds/                  # Demo data CSVs
├── scripts/                # DB inspection utilities
├── docs/                   # Phase-based documentation
├── requirements.txt        # Root dependencies
└── .env / security.env     # Sensitive configuration (not committed)
```

## Requirements
- `Python 3.11`
- PostgreSQL database reachable via `DATABASE_URL`.
- (Optional) MySQL instance for testing the `mysql_readonly` connector.

Relevant dependencies:
- Backend: see `backend/requirements.txt`.
- Root: see `requirements.txt`.

## Configuration
1. Set environment variables:
   - `DATABASE_URL`: PostgreSQL connection string, e.g., `postgresql://user:pass@host:5432/dbname`.
   - JWT secrets and the like in `.env`/`security.env` (e.g., signing keys).
2. Adjust `alembic.ini` if needed (section `sqlalchemy.url`).
3. Install dependencies:
   - `pip install -r requirements.txt`
   - `pip install -r backend/requirements.txt`

## Local Execution
- Run backend (default local port):
  - `cd backend`
  - `uvicorn app.main:app --host 127.0.0.1 --port 8000`
- If port `8000` is in use:
  - `uvicorn app.main:app --host 127.0.0.1 --port 8001`
- API will be available at `http://127.0.0.1:8000/` (or the chosen port).

## Database & Migrations
- Apply Alembic migrations:
  - `alembic upgrade head`
- Auxiliary scripts under `scripts/`:
  - `scripts/list_all_tables.py`, `scripts/inspect_tables.py`, `scripts/inspect_indexes.py`.

## Automated Tests
- Run the test suite:
  - `cd backend`
  - `pytest -q`
- Test suite covers authentication, cache, ETL, scheduler, reports, and business rules.

## External Integrations (Phase 5)
- Base `Connector` interface with methods: `authenticate`, `fetch`, `push`, `test_connection`, `get_health`, `map_to_internal_models`.
- Connector registration via `ConnectorRegistry` (`hubspot`, `mysql_readonly`).
- Per-client configuration persistence in `integracoes_cliente`.
- Main endpoints:
  - `GET /integrations/connectors`: list available connectors.
  - `GET /integrations/healthz`: aggregated health per connector/client.
  - `GET /integrations/{connector_key}/config`: returns `IntegracaoConfigState` (200, `exists=true/false`).
  - `POST /integrations/{connector_key}/configure`: store per-client credentials.
  - `POST /integrations/{connector_key}/test`: test connection using stored credentials.

### MySQL Readonly Connector
- Dependency: `PyMySQL` (already included).
- Expected credentials: `host`, `port` (default `3306`), `user`, `password` (can be empty), `database` (optional).
- Connection test runs `SELECT 1` and returns:
  - `status: ok` on success
  - `status: error` with message on failure
  - `status: not_configured` if `host` or `user` is missing
- Health reports `ok`, `degraded` (credentials present but connection failed) or `not_configured`.

### Flow without an associated client
- Users without `cliente_id` are not 403'd on configuration reads; `GET /config` returns `exists=false` (200).
- `POST /configure` and `POST /test` auto-provision: create/associate a client with the user to save/test the integration.

## Main Endpoints (examples)
- `POST /login`: authentication; returns JWT token.
- `GET /dashboard/filtros-disponiveis`: filters for the interactive dashboard.
- `GET /integrations/connectors` and `GET /integrations/healthz`: catalog and health of connectors.
- See `backend/app/main.py` and `backend/app/routes/` for the remaining routes.

## Frontend (Supa pages)
- Location: `frontend/supa/`.
- Useful pages:
  - `login.html`: authentication and token storage.
  - `integracoes.html`: connector grid, configuration modal, and save/test buttons.
  - `configuracoes.html`, `usuarios.html`, `index.html`: utilities and navigation.
- Pages call the backend API using the JWT token stored in `localStorage`.

## Deploy (Docker & CI/CD)
- Docker:
  - `backend/Dockerfile` builds an image with `uvicorn` serving `app.main:app`.
- CI/CD:
  - Pipelines in `.github/workflows/` for `dev` and `prod` backends.

## Security
- Never expose credentials in read responses.
- Store secrets in `.env`/`security.env` or a vault.
- Principle of least privilege (minimum scopes per connector).
- Avoid logging tokens and secrets.

## Troubleshooting
- Port in use at startup:
  - Use another port: `--port 8001`.
- Missing `DATABASE_URL`:
  - Set it in the environment or in `alembic.ini`.
- MySQL test failure:
  - Verify MySQL is running, host/port are correct, and credentials are valid.
- Missing dependency:
  - `pip install -r backend/requirements.txt` (includes `PyMySQL`).

## Roadmap
- Phase B: External authentication flows (OAuth 2.0 / tokens) and secure storage.
- Phase C: Admin endpoints for integration CRUD.
- Phase D: Functional connectors (MySQL/HubSpot) with synchronization.
- Phase E: Metrics, cache/retries, observability.
- Phase F: Security hardening, tests, and final documentation.

## Contributing
- Open issues and PRs with clear descriptions.
- Follow the existing code style and avoid removing unrelated lines (preserve baseline).

## License
See the `LICENSE` file at the repository root.

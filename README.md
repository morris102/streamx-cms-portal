# StreamX CMS Portal

> Django + PostgreSQL backend that provides role-based user administration for the StreamX content-management portal.

---

## Metadata

| Field      | Value                                             |
| ---------- | ------------------------------------------------- |
| Service    | `streamx-cms-portal`                              |
| Version    | `1.0.0` (Jenkins image tag); no Python package version |
| Owner      | StreamX                                           |
| Repository | https://github.com/morris102/streamx-cms-portal   |
| Confidence | High for code-verified behavior; Medium for external deployment repositories |

---

## Overview

StreamX CMS Portal is the administrative backend of the StreamX content platform. It is a server-rendered Django project whose first delivered capability lets an **Admin** manage the people who operate the CMS: create accounts, assign one of three roles (`Admin`, `Editor`, `Author`), search and filter users, reset passwords, and deactivate or delete accounts.

The service exists to answer one domain question safely: *who may write, edit, or publish content, and how is that access changed without locking the portal out of administrative control?* To that end, the implementation enforces last-active-Admin protection, self-protection, read-only superusers, and immediate role changes on the very next request.

**Primary actors**

| Actor | Capability |
| --- | --- |
| Admin (or Django superuser) | Full user lifecycle management through `/api/users/` |
| Editor / Author | Authenticated CMS users; cannot call user-management endpoints |
| Inactive account | Cannot administer users even if it still holds the Admin role |
| Django superuser | Treated as Admin; read-only through the user API |

**Scope** — Currently delivered: user-management API, role model, and database configuration. Not yet delivered: login/logout, self-service password reset, content/article management, and a public documentation UI.

---

## Architecture

**Style:** Modular monolith. One Django project (`config`) with domain logic in a dedicated app (`users`). All interactions are **synchronous HTTP/JSON**; there are no message brokers, workers, or background jobs.

```text
Client (session cookie + CSRF)
        │
        ▼
config/urls.py ──► users/urls.py
        │
        ▼
users/views.py          HTTP parsing, status mapping
        │
        ├── users/permissions.py   admin_required decorator, role resolution
        ├── users/serializers.py   validation + response serialization
        └── users/services.py      business rules, transactions
                    │
                    ▼
            Django ORM (auth User / Group)
                    │
                    ▼
              PostgreSQL
```

**Responsibilities**

- `config/` — settings, root URL routing, WSGI/ASGI entry points.
- `users/` — the user-management domain: authorization, validation, transactional business rules, and HTTP views.
- `openspec/` — request/spec artifacts describing intended behavior (`openspec/specs/`) and archived changes.

**Non-responsibilities**

- No content authoring or publishing endpoints yet.
- No token/JWT API; authentication is Django session based.
- No external identity provider integration.

**Trade-off:** Plain Django function views and hand-written validation are used instead of Django REST Framework. This keeps the dependency surface small but means errors, pagination, and serialization are maintained by hand.

---

## Components

| Component | Role | Input | Output | Mode |
| --- | --- | --- | --- | --- |
| `config/urls.py` | Root router | HTTP request | Routes `/admin/` and `/api/users/` | Sync |
| `users/urls.py` | App router | HTTP request | `user_collection`, `user_detail` | Sync |
| `users/views.py` | HTTP layer | Query string / JSON body | `JsonResponse`, `204` | Sync |
| `users/permissions.py` | Authorization | `request.user` | `401` / `403` or passes through | Sync |
| `users/serializers.py` | Validation & shaping | Raw JSON / query dict | Cleaned data or `ValidationError` | Sync |
| `users/services.py` | Business rules | Cleaned data | ORM writes, `ProtectedOperation` (`409`) | Sync (transactional) |
| `users/migrations/0001_roles.py` | Seed data | — | `Admin`, `Editor`, `Author` groups | Startup/migration |
| Django admin (`/admin/`) | Operator console | Browser | HTML | Sync |

---

## Data Flow

All flows are synchronous request/response. There is no asynchronous or event-driven path.

### Read flow — `GET /api/users/`

1. `config.urls` delegates `/api/users/` to `users.urls`.
2. `user_collection` parses `page`, `page_size`, `search`, and `is_active` through `parse_list_params`.
3. `services.list_users` builds an ORM queryset ordered by ID, filters by case-insensitive email substring and active flag, then slices it. The count query and `prefetch_related("groups")` keep the query count constant (verified by a test asserting three queries).
4. `serialize_user` emits the public shape; the view returns `200` with the pagination envelope.

### Write flow — `POST /api/users/`, `PATCH`/`DELETE /api/users/{id}/`

1. For detail operations, `admin_required` resolves the session user and rejects anonymous (`401`), inactive (`403`), or non-Admin (`403`) callers.
2. `parse_json_body` rejects invalid JSON or non-object bodies.
3. `validate_create` / `validate_update` reject unknown fields, invalid email, weak passwords (Django validators), duplicate username/email, invalid roles, and non-boolean `is_active`.
4. `services.create_user` / `update_user` / `delete_user` run inside `transaction.atomic`. Update and delete lock the Admin group and target row with `select_for_update` before evaluating protection rules.
5. Safety rules raise `ProtectedOperation`, mapped to `409`. Success returns `201`, `200`, or `204`.

### Failure mapping

| Condition | Status | Body |
| --- | --- | --- |
| Validation failure | `400` | `{"errors": {"field": ["message"]}}` |
| Missing session / anonymous | `401` | `{"detail": "Authentication required."}` |
| Inactive or non-Admin caller | `403` | `{"detail": "..."}` |
| User not found | `404` | `{"detail": "User not found."}` |
| Method not allowed | `405` | Django default |
| Protected operation | `409` | `{"detail": "..."}` |

---

## API Reference

Base path: `/api/users/`. Requests and responses are JSON. Unsafe methods require the CSRF token because `CsrfViewMiddleware` is enabled. Source of truth: `users/urls.py`, `users/views.py`, `users/serializers.py`.

### Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/users/` | **None in current code** (see Known Limitations) | Paginated, searchable, filterable list |
| `POST` | `/api/users/` | **None in current code** | Create a user |
| `GET` | `/api/users/{id}/` | Admin / superuser | Retrieve one user |
| `PATCH` | `/api/users/{id}/` | Admin / superuser | Partially update a user |
| `DELETE` | `/api/users/{id}/` | Admin / superuser | Delete a user |

### List query parameters

| Parameter | Default | Rules |
| --- | --- | --- |
| `page` | `1` | Integer ≥ 1 |
| `page_size` | `20` | Integer 1–100 |
| `search` | none | Case-insensitive substring of email; blank ignored |
| `is_active` | none | `true` / `false` (case-insensitive) |

Response envelope:

```json
{
  "count": 42,
  "page": 1,
  "page_size": 20,
  "total_pages": 3,
  "results": [
    {
      "id": 1,
      "username": "alice",
      "email": "alice@example.com",
      "first_name": "Alice",
      "last_name": "Nguyen",
      "role": "Author",
      "is_active": true,
      "date_joined": "2026-11-06T12:00:00+00:00"
    }
  ]
}
```

### Create body

Required: `username`, `email`, `password`, `role`. Optional: `first_name`, `last_name`, `is_active` (defaults to `true`).

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "V3ry-Str0ng-Pass!42",
  "role": "Author",
  "first_name": "Alice",
  "last_name": "Nguyen"
}
```

### Update body

Any subset of the writable fields: `username`, `email`, `first_name`, `last_name`, `password`, `role`, `is_active`. Unknown fields are rejected. Changing `role` replaces the previous role.

### Invariants

- Exactly three role names are accepted: `Admin`, `Editor`, `Author`.
- Every non-superuser has exactly one role. A superuser reports `Admin`.
- Responses never include a password, password hash, session, or token.
- Superusers are read-only through this API (`409`).
- The last active Admin cannot be demoted, deactivated, or deleted (`409`).
- An Admin cannot delete or deactivate their own account (`409`).

### Documentation endpoints in code (not routed)

`users/views.py` contains `openapi_spec` and `api_docs` views, but neither is registered in `users/urls.py`, and `users/openapi.json` plus `users/templates/users/docs.html` are absent from the repository. Do not rely on `/api/openapi.json/` or `/api/docs/`; they currently return `404`.

---

## Security

**Implemented**

- Session-cookie authentication with Django's `AuthenticationMiddleware`.
- CSRF protection enforced for `POST`/`PATCH`/`DELETE` (covered by tests).
- Admin-only authorization on detail routes via `admin_required` (`users/permissions.py`).
- Inactive accounts are denied even when they carry the Admin role.
- Password hashing through Django and all four configured password validators.
- Superuser accounts are immutable through the API; the last active Admin is protected with transactional row locks.
- Unknown request fields (including `is_superuser`) are rejected, limiting mass assignment.
- Secrets are read from environment variables / `.env`; `.env` is git-ignored and `.env.example` contains placeholders only.

**Gaps that matter before production**

- `config/settings.py` hardcodes an insecure `SECRET_KEY`, sets `DEBUG = True`, and leaves `ALLOWED_HOSTS` empty.
- The collection route (`GET`/`POST /api/users/`) currently has its `@admin_required` decorator commented out, so listing and creating users are unauthenticated.
- No HTTPS, secure-cookie, HSTS, or production logging configuration.
- The Docker image runs `manage.py runserver` as root.
- Email uniqueness is checked in application code only; there is no database unique index, so concurrent writes can create duplicates.

See `AGENTS.md` for the project's mandatory security rules.

---

## Observability

**Current state:** default Django behavior only.

- **Logging:** Django's default `LOGGING` configuration; no structured logging, request IDs, or correlation IDs.
- **Metrics:** none. No latency, error-rate, or throughput instrumentation.
- **Tracing:** none. OpenTelemetry and W3C Trace Context are not configured.
- **Health checks:** none beyond Django's own startup; no `/healthz` or `/readyz` endpoint.

Because every interaction is synchronous and writes are transactional, the most useful next additions are a request-ID logging filter, an access log with status/latency, an error-rate metric per endpoint, and OpenTelemetry instrumentation for the view → service → PostgreSQL path.

---

## Dependencies

| Dependency | Version | Role | Failure impact |
| --- | --- | --- | --- |
| Python | 3.14 (Docker `python:3.14-slim`) | Runtime | Service cannot start |
| Django | 6.1.3 | Web framework, ORM, auth, admin | Total outage |
| psycopg | 3.3.8 (`binary`) | PostgreSQL driver | Database connections fail; all API calls fail |
| python-dotenv | 1.2.4 | Loads `.env` into process env | Required DB vars must be supplied externally or startup fails |
| PostgreSQL | 13+ (not pinned) | Primary datastore | Total outage; no SQLite fallback |
| Docker | any recent | Image build/run | Deployment pipeline fails |
| GitHub Actions / Jenkins | — | CI build, image push, manifest update | No new releases |

No Django REST Framework, no OpenAPI generator, and no test-only dependency beyond Django.

---

## Deployment

| Artifact | Behavior |
| --- | --- |
| `Dockerfile` | `python:3.14-slim`, installs `requirements.txt`, exposes `8000`, runs `python manage.py runserver 0.0.0.0:8000` on container start |
| `.github/workflows/ci-cd.yml` | On push to `main` or manual dispatch: checkout → Docker Hub login → build image tagged with the commit SHA → push → checkout `streamx-project/streamx-k8s-manifest` → update the image tag in `helm/cms-portal/values.yaml` |
| `Jenkinsfile` | Uses the shared `ci-library@main` `dockerPipeline` with image `stevenguyen9x/streamx-cms-portal`, tag `1.0.0` |

**Environment variables** (required unless noted):

```env
DB_NAME=cms_portal            # required
DB_USER=cms_portal            # required
DB_PASSWORD=change-me         # required
DB_HOST=localhost             # optional, default localhost
DB_PORT=5432                  # optional, default 5432
```

**Runtime note:** the image is a development configuration. A production deployment needs a WSGI/ASGI server (for example Gunicorn), `DEBUG=False`, a real secret, explicit `ALLOWED_HOSTS`, collected static files, and a non-root user.

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.14 |
| Framework | Django 6.1.3 |
| Database | PostgreSQL |
| Driver | psycopg 3 (`psycopg[binary]`) |
| ORM | Django ORM |
| Auth | Django session authentication, `auth.User`, `auth.Group` roles |
| Config | `python-dotenv` + environment variables |
| API style | Plain Django function views + `JsonResponse` (no DRF) |
| Testing | Django `TestCase` / `SimpleTestCase` (55 tests) |
| Packaging | pip + `requirements.txt` |
| Container | Docker |
| CI/CD | GitHub Actions, Jenkins shared library, Helm values in a separate manifest repo |
| Spec workflow | OpenSpec (`openspec/`) |

---

## Project Structure

```text
streamx-cms-portal/
├── config/                     # Django project configuration
│   ├── settings.py             # Apps, DB, auth, i18n, static settings
│   ├── urls.py                 # /admin/ and /api/users/ routing
│   ├── asgi.py
│   └── wsgi.py
├── users/                      # User-management domain app
│   ├── apps.py
│   ├── permissions.py          # Role resolution + admin_required decorator
│   ├── serializers.py          # Request parsing, validation, serialization
│   ├── services.py             # Transactional business rules and protections
│   ├── views.py                # HTTP layer and status mapping
│   ├── urls.py
│   ├── migrations/
│   │   └── 0001_roles.py       # Seeds Admin / Editor / Author groups
│   └── tests/
│       ├── test_views.py
│       ├── test_services.py
│       ├── test_validation.py
│       ├── test_permissions.py
│       ├── test_integration.py
│       └── test_urls.py
├── openspec/                   # Spec-driven change artifacts
│   ├── specs/                  # Current capability specifications
│   └── changes/archive/        # Completed change proposals and designs
├── .github/workflows/ci-cd.yml # Docker build/push + manifest update
├── Dockerfile
├── Jenkinsfile
├── manage.py
├── requirements.txt
├── .env.example
├── AGENTS.md                   # Project conventions for contributors/agents
└── README.md
```

The repository has no `templates/`, `static/`, or `media/` directories yet; those appear as features are added.

---

## Setup Guide

### Prerequisites

- Python 3.14
- PostgreSQL running locally (or reachable over the network)
- A database and a role that can create databases (the test runner creates an isolated test database)

### 1. Create the virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create the database

```bash
createdb cms_portal
```

Or from `psql`:

```sql
CREATE DATABASE cms_portal;
```

### 3. Configure the environment

```bash
cp .env.example .env
```

Edit `.env` with real local credentials. `DB_NAME`, `DB_USER`, and `DB_PASSWORD` are required; Django fails at startup with `KeyError` rather than falling back to SQLite when they are missing.

### 4. Apply migrations and create an administrator

```bash
python manage.py migrate
python manage.py createsuperuser
```

`migrate` also seeds the `Admin`, `Editor`, and `Author` groups. The optional `DJANGO_SUPERUSER_*` variables in `.env.example` can be used with `createsuperuser --noinput`.

### 5. Run the development server

```bash
python manage.py runserver
```

| URL | Purpose |
| --- | --- |
| `http://127.0.0.1:8000/admin/` | Django admin (session login) |
| `http://127.0.0.1:8000/api/users/` | User-management API |

The API uses session authentication, so sign in through `/admin/` first, then call the API from the same browser session (or reuse the `sessionid` cookie). Unsafe methods also require the `csrftoken` cookie/header.

Example:

```bash
curl -s http://127.0.0.1:8000/api/users/?page=1&page_size=10 \
  -H "Cookie: sessionid=<session-id>"
```

### 6. Validate the configuration

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

These commands require the database environment variables to be present because settings read them at import time.

### Run with Docker

```bash
docker build -t streamx-cms-portal .
docker run --rm -p 8000:8000 --env-file .env streamx-cms-portal
```

The container starts Django's development server, so use this for local verification only.

---

## Running Tests

The suite uses Django's built-in test runner and 55 tests across six modules.

```bash
source .venv/bin/activate

# All tests
python manage.py test

# The users app only
python manage.py test users

# One module
python manage.py test users.tests.test_views
```

| Test module | Coverage |
| --- | --- |
| `test_views.py` | Status codes, response shape, pagination, filtering, query-count budget |
| `test_services.py` | Password hashing, role replacement, superuser/last-Admin/self protections |
| `test_validation.py` | Required/unknown fields, email and password rules, duplicates, list parameters |
| `test_permissions.py` | `401`/`403` behavior, inactive Admins, `405`, CSRF enforcement |
| `test_integration.py` | Full create → list → update → delete lifecycle, immediate role changes |
| `test_urls.py` | URL reversal for list and detail routes |

**Test database requirements:** Django creates and destroys a separate PostgreSQL database derived from `DB_NAME`. The configured role must have `CREATEDB` permission; the development database is left untouched. Tests cannot run with SQLite because the settings module always selects PostgreSQL.

**Verified on 2026-11-14 in this workspace:**

- `python manage.py check` with `DB_*` variables supplied → `System check identified no issues (0 silenced).`
- `python manage.py test users` → could not execute: PostgreSQL rejected the configured credentials (`password authentication failed for user "cms_portal"`). No test result is claimed until the suite is run against a valid database.
- Note that `users/tests/test_permissions.py::test_anonymous_is_rejected_with_401` asserts `401` for `GET /api/users/`, while the collection view currently has `@admin_required` commented out. Expect that test (and the matching spec) to fail until the decorator is restored.

---

## Known Limitations

1. **Unauthenticated collection endpoint** — `users/views.py` has `# @admin_required` above `user_collection`, so anyone can list and create users. Detail operations are still Admin-only. This contradicts `openspec/specs/role-based-access-control/spec.md` and the permission tests.
2. **Unrouted documentation views** — `openapi_spec` and `api_docs` exist but are not in `users/urls.py`, and their data/template files are missing. The OpenAPI documentation capability described in `openspec/specs/api-documentation/spec.md` is not currently usable.
3. **Development settings committed** — hardcoded `SECRET_KEY`, `DEBUG = True`, empty `ALLOWED_HOSTS`, no secure-cookie or HTTPS settings.
4. **No production server** — the Dockerfile runs `runserver` as root; static files are not collected or served by a dedicated server.
5. **Application-level email uniqueness** — no database unique constraint or functional index; concurrent inserts can duplicate an email.
6. **No login/logout or password-reset endpoints** — users must use the Django admin session.
7. **No observability stack** — no structured logs, metrics, tracing, or health endpoints.
8. **Limitations inherited from `auth.User`** — the project uses the built-in user model rather than a custom one, which is hard to change later.
9. **Pagination in memory** — `count()` plus a sliced queryset per request; fine at current scale, not ideal for very large tables.

---

## Assumptions

- **The commented `@admin_required` is a temporary local change, not intended behavior.** Reasoning: every permission test and both RBAC/user-management specs require Admin-only access to all endpoints. The README documents the code as it exists today so operators are not surprised.
- **The documentation endpoints were intentionally deferred or reverted.** Reasoning: `openapi.json` was deleted in commit `9b12bfa`, and the routes were never added, while the views and archived proposal remain.
- **PostgreSQL version 13+.** Reasoning: no version is pinned in the repository; psycopg 3 supports modern PostgreSQL, and no version-specific features are used.
- **Deployment targets Kubernetes via an external Helm chart.** Reasoning: CI updates `helm/cms-portal/values.yaml` in `streamx-project/streamx-k8s-manifest`, though that repository was not inspected.
- **No message broker or async job is in scope.** Reasoning: `requirements.txt` and the code contain no broker client and no task queue.

---

## Confidence & Risks

### Confidence Level

**High** for architecture, routes, request/response contracts, role rules, test layout, and configuration, all read directly from source.

**Medium** for deployment topology and production runtime, because the Helm chart and Kubernetes repository are external and the Dockerfile is development-oriented.

### Risk Areas

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Collection endpoint is unauthenticated | Anyone can enumerate emails or create Admin accounts | Restore `@admin_required` and rerun `test_permissions.py` |
| Hardcoded secret / `DEBUG=True` | Secret disclosure and verbose error leakage in production | Move to environment variables; set `DEBUG=False`; populate `ALLOWED_HOSTS` |
| Development server in container | Poor concurrency and no graceful shutdown | Run Gunicorn/uWSGI behind a reverse proxy, as non-root |
| No DB-level email uniqueness | Duplicate accounts under concurrency | Add a functional unique index and handle `IntegrityError` |
| No observability | Slow incident detection and diagnosis | Add request IDs, structured logs, metrics, and OpenTelemetry tracing |
| Spec drift | `openspec/` describes behavior the code does not currently implement | Treat specs as intent; reconcile code and specs before release |

# Design

## Context

See `proposal.md` — Why.

- Django 6.1.3, single `config/settings.py`, SQLite today.
- `psycopg` 3.3.8 and `psycopg-binary` 3.3.8 are already installed in `.venv`; `python-dotenv` is not.
- A healthy `postgres:17` container (`spring_starter-postgres-1`) listens on `localhost:5432` and contains only `postgres` and `spring_starter` databases, with a single `postgres` superuser role.
- No `requirements.txt`, `.env`, or `.env.example` exists.
- `db.sqlite3` contains zero users and zero sessions, so there is no data to migrate.

## Goals / Non-Goals

**Goals:**

- A working PostgreSQL connection for development and tests with no SQLite fallback.
- Credentials kept out of version control and easy to change.
- Reuse of the running server without creating a second container.

**Non-Goals:**

- Hardening `SECRET_KEY`, `DEBUG`, or `ALLOWED_HOSTS`.
- Production database hosting, backups, TLS, or connection pooling.
- Splitting settings into multiple environment-specific modules.
- Model or API changes.

## Decisions

### Reuse the running PostgreSQL server with a dedicated database and role

Create a `cms_portal` database owned by a new `cms_portal` login role on the existing `postgres:17` container. Do not use the `postgres` superuser and do not reuse the `spring_starter` database or password.

The role receives `CREATEDB` so Django can create `test_cms_portal`. This is the minimum extra privilege needed for the test runner.

```sql
CREATE ROLE cms_portal LOGIN PASSWORD '<development-password>' CREATEDB;
CREATE DATABASE cms_portal OWNER cms_portal;
```

Alternatives considered:

- **Own `docker-compose.yml` on port 5433** — better isolation, but adds a second server to start and manage. Reconsider if this project outlives the `spring_starter` stack.
- **System PostgreSQL** — not installed; the service is inactive.

### Use `python-dotenv`, loaded without overriding the process environment

Call `load_dotenv(BASE_DIR / ".env")` near the top of `config/settings.py`. `python-dotenv` defaults to not overriding existing variables, so a shell-provided value wins over `.env`.

Alternatives considered:

- **Export variables in the shell only** — no dependency, but `.env` would not be read automatically, contradicting the workflow documented in `AGENTS.md`.
- **Hand-written parser** — more project code to maintain than one small, standard dependency.

### Read `DB_*` variables directly with fail-fast semantics

Use `os.environ["DB_NAME"]`, `os.environ["DB_USER"]`, and `os.environ["DB_PASSWORD"]` so a missing value raises `KeyError` at startup. Use `os.environ.get("DB_HOST", "localhost")` and `os.environ.get("DB_PORT", "5432")` for the defaults.

`KeyError` is terse but stops the app before it can touch the wrong database. A follow-up can replace it with a clearer configuration error if startup messages become a problem.

### Keep the database block in `config/settings.py`

No settings package split. The project is small and `AGENTS.md` asks for the smallest change consistent with existing patterns.

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["DB_NAME"],
        "USER": os.environ["DB_USER"],
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}
```

Django 6.1 uses psycopg 3 automatically with the `postgresql` backend; no `_psycopg2` suffix is needed.

### Pin the existing versions in a new `requirements.txt`

`Django==6.1.3` and `psycopg[binary]==3.3.8` match the working virtual environment. Add `python-dotenv` pinned to the version installed during implementation. The `[binary]` extra avoids a local build toolchain.

### Tests rely on Django's default test database behavior

Django creates `test_cms_portal` and destroys it after the run. No `TEST` name override is needed. The role's `CREATEDB` attribute is the only prerequisite.

### No data migration

`db.sqlite3` has no users or sessions. Recreate the development superuser with `createsuperuser` after migrating. Keep the SQLite file on disk for rollback but ignore it in Git.

## Risks / Trade-offs

- **Container lifecycle coupling** → The `cms_portal` database lives in the `spring_starter` compose volume. Running `docker compose down -v` there deletes it. Mitigation: keep the rollback path and treat this as development-only data; move to a dedicated container if the data becomes valuable.
- **Another project controls port 5432** → If that stack stops or remaps the port, this project cannot connect. Mitigation: the connection error is immediate, and `.env` makes the host/port easy to change.
- **`CREATEDB` is broader than a normal app role** → Required for Django's test runner. Mitigation: use a separate role in any shared or production environment.
- **Missing `.env` blocks startup** → Intentional fail-fast behavior. Mitigation: `.env.example` documents the required keys.
- **Credentials in a local file** → `.env` must be gitignored. Mitigation: add it to `.gitignore` and commit only placeholders in `.env.example`.

## Migration Plan

1. Create the `cms_portal` role and database on the running container.
2. Add `python-dotenv` to the virtual environment and create `requirements.txt`.
3. Create `.env` with the development password and `.env.example` with placeholders; ignore `.env`.
4. Switch `DATABASES` to PostgreSQL and add `load_dotenv`.
5. Run `python manage.py check`, `migrate`, and `createsuperuser`.
6. Run the test suite against PostgreSQL and add the backend assertion.

Rollback: restore the SQLite `DATABASES` block (the file is still present), or point `DB_*` at another PostgreSQL server. Dropping the `cms_portal` database and role reverses the server-side changes.

## Open Questions

- Whether this project should later get its own PostgreSQL container is deferred; it does not change the specs or task breakdown.

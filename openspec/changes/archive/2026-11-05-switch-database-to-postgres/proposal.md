# Proposal

## Why

The project documents PostgreSQL as its primary database, but `config/settings.py` still uses SQLite. The PostgreSQL driver (`psycopg` 3.3.8) is already installed, and a PostgreSQL 17 server is running locally, so the remaining gap is configuration, credentials, and environment handling.

## What Changes

- Switch the Django `default` database from SQLite to PostgreSQL using `django.db.backends.postgresql` and psycopg 3.
- Read `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` from environment variables instead of hardcoding connection values.
- Load a local `.env` file with `python-dotenv`; add `.env.example` documenting the required keys.
- Add the missing `requirements.txt` with Django, `psycopg[binary]`, and `python-dotenv`.
- Add `.env` and `db.sqlite3` to `.gitignore`.
- Create a dedicated `cms_portal` database and `cms_portal` login role on the existing PostgreSQL 17 server. The role needs `CREATEDB` so Django can create `test_cms_portal` during tests.
- Add one test asserting the configured backend is PostgreSQL.
- Recreate the development superuser; no SQLite data needs migration (the current database has zero users and zero sessions).

Out of scope: `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` hardening; production database hosting; connection pooling; changes to application models or API behavior.

## Capabilities

### New Capabilities

- `database-configuration`: how the application selects its relational database and obtains connection settings from the environment, including local `.env` loading and the PostgreSQL test database.

### Modified Capabilities

None.

## Impact

- `config/settings.py`: database configuration and `.env` loading.
- New `requirements.txt`, `.env.example`, and local `.env` (gitignored).
- `.gitignore`: ignore `.env` and `db.sqlite3`.
- `users/tests.py`: add a backend assertion.
- External state: new `cms_portal` database and `cms_portal` role on the running `postgres:17` container (`localhost:5432`, owned by the separate `spring_starter` compose project).
- No API or model changes. The development data store moves from `db.sqlite3` to PostgreSQL; existing SQLite content is empty, so no data migration is required.

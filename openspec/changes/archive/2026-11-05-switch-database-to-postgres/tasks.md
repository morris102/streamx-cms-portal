# Tasks

## 1. Database server preparation

- [x] 1.1 Create the `cms_portal` login role with `CREATEDB` and the `cms_portal` database owned by it on the running `postgres:17` container; verify by connecting as `cms_portal` and confirming `current_user`, `current_database()`, and `rolcreatedb = true`.
- [x] 1.2 Confirm the new database is reachable over TCP at `localhost:5432` and that the `spring_starter` database is untouched; verify with a successful `psql` connection to `cms_portal` and a database list showing both databases.

## 2. Dependencies and environment files

- [x] 2.1 Install `python-dotenv` into `.venv` and create `requirements.txt` pinning `Django==6.1.3`, `psycopg[binary]==3.3.8`, and the installed `python-dotenv` version; verify `pip install -r requirements.txt` succeeds and `pip check` reports no broken requirements.
- [x] 2.2 Add `.env` and `db.sqlite3` to `.gitignore`; verify with `git check-ignore -v .env db.sqlite3`.
- [x] 2.3 Create a local `.env` with `DB_NAME=cms_portal`, `DB_USER=cms_portal`, the development password, `DB_HOST=localhost`, and `DB_PORT=5432`; create `.env.example` with the same keys and placeholder values; verify `git status` shows `.env.example` but not `.env`.

## 3. Django configuration and configuration test

- [x] 3.1 Add `load_dotenv(BASE_DIR / ".env")` to `config/settings.py` and replace the SQLite `DATABASES` block with the PostgreSQL block that reads `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`; verify `python manage.py check` passes and `python manage.py shell -c "from django.db import connection; print(connection.vendor, connection.settings_dict['NAME'])"` prints `postgresql cms_portal`.
- [x] 3.2 Verify fail-fast behavior: temporarily rename `.env`, run `env -u DB_PASSWORD python manage.py check`, confirm it fails with a missing-configuration error rather than using SQLite, then restore `.env`.
- [x] 3.3 Add a test in `users/tests.py` asserting `connection.vendor == "postgresql"` and the configured database name is `cms_portal`; verify it passes with `python manage.py test users`.

## 4. Schema and development user

- [x] 4.1 Run `python manage.py migrate`; verify `python manage.py showmigrations` reports all migrations applied and that `django_migrations` contains rows in the `cms_portal` database.
- [x] 4.2 Create a development superuser with `python manage.py createsuperuser`; verify the account exists with `User.objects.filter(is_superuser=True).exists()` returning `True`.

## 5. Integration verification

- [x] 5.1 Run the full suite with `python manage.py test`; verify all tests pass against PostgreSQL.
- [x] 5.2 Verify the test database is cleaned up after the run by listing databases and confirming `test_cms_portal` is absent.
- [x] 5.3 Verify the app no longer reads `db.sqlite3` by confirming the connection settings report the PostgreSQL backend and the `cms_portal` name from task 3.1, and that `git check-ignore .env` succeeds.

## Workflow follow-up

- Review the change artifacts, then archive with `/opsx-archive` once implementation and verification are complete.
- If this project outlives the `spring_starter` compose stack, move the database to a dedicated container; the `.env` host and port make that a configuration-only change.

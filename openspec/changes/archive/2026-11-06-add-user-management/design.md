# Design

## Context

See `proposal.md` — Why.

- Django 6.1.3 on Python 3.14; PostgreSQL via `psycopg` 3.
- `config/settings.py` lists `users` in `INSTALLED_APPS` and `config/urls.py` includes `users.urls` at `/api/users/`, but no `users/` package exists. `manage.py check` fails today with `ModuleNotFoundError: No module named 'users'`, so recreating the app is a precondition for any feature work.
- Django REST Framework is **not** installed and no `REST_FRAMEWORK` setting exists. Only `django`, `psycopg`, `python-dotenv` and their transitive deps are in `.venv`.
- `AUTH_USER_MODEL` is the default `auth.User`; the database already has 18 applied migrations and one superuser (`admin`, `admin@example.com`, `is_superuser=t`, no groups).
- No tests exist yet in the repository.

The approved specs are the contract: `specs/user-management/spec.md` and `specs/role-based-access-control/spec.md`.

## Goals / Non-Goals

**Goals:**

- Restore a working Django baseline and add the user-management app without touching unrelated apps.
- One API surface with consistent request validation, status codes, and response shape.
- Authorization enforced once, in shared code, so every endpoint inherits it.
- Role data that survives future changes and stays queryable (groups, not free-text).

**Non-Goals:**

- Any frontend, template, or Django-admin customization for user management.
- Login/logout, password-reset email, self-service profile editing.
- Content-level permissions for Editor/Author (future changes).
- Audit logging, soft delete, token/JWT auth.
- Migrating user data or changing `AUTH_USER_MODEL`.

## Decisions

### 1. Recreate `users` as a minimal app

`users/` gets `__init__.py`, `apps.py`, `urls.py`, `views.py`, `services.py`, `serializers.py` (JSON parsing/validation helpers), `permissions.py`, `tests/`, and `migrations/` (only if a data migration is needed). No models are defined: accounts and roles live in `django.contrib.auth` and `django.contrib.auth.models.Group`.

Rationale: settings/urls already point at `users`; creating the app is the smallest repair and keeps the feature in the app the project intended. Alternative considered: move routes to a new `accounts` app — rejected as needless churn while no code exists.

### 2. Plain Django JSON views, not DRF (provisional)

Implement `@csrf_protect`-covered function views returning `JsonResponse`, with explicit status codes.

Rationale: DRF is not installed and not configured; adding a dependency for one resource contradicts the "no new dependency" guideline. Plain Django is a few dozen lines here. Alternative: add DRF and use `ModelViewSet` + serializers — cleaner later, but introduces settings, exception handling, pagination classes, and a dependency the user has not approved. **This is an approval question.** If DRF is chosen, the same spec/design holds; only the view/serializer layer changes.

### 3. Keep `auth.User`, model roles as one `Group` per user

Roles are the three `Group` rows `Admin`, `Editor`, `Author`, created by a data migration (`get_or_create`). Assignment is `user.groups.set([group])` so replacement is atomic and a user never holds two roles. Superusers report `role = "Admin"` without requiring group membership.

Rationale: no `AUTH_USER_MODEL` change (high-risk, irreversible once deployed), no new profile model, and groups are already migrated and supported by Django's permission system for future content rules. Alternative: `UserProfile.role` with a choice field — simpler to query and validate, but adds a model, a migration, and a custom user/profile split; not justified for three values. **Approval question** for profile vs group.

Role resolution: `user.is_superuser or user.groups.filter(name="Admin").exists()`. A user with no group is treated as having no role; it cannot use the API. Creating/updating through the API always assigns exactly one group.

### 4. Email uniqueness: enforce in code, add a DB index only if approved

Validate uniqueness with `User.objects.filter(email__iexact=email).exclude(pk=instance.pk).exists()` inside the create/update service, and also rely on Django's username uniqueness.

Rationale: PostgreSQL's unique index on `email` is case-sensitive, so it would not enforce the spec's case-insensitive rule. A functional unique index `UniqueConstraint(Lower("email"), name=...)` would, but `auth.User.email` is `blank=True` and existing rows may violate it, and adding constraints to a third-party table needs a migration in our app with `SeparateDatabaseAndState` care. Code-level validation plus select-then-insert is sufficient for an Admin-only endpoint; the DB index is defense in depth. **Approval question:** add the functional unique index now or defer. If deferred, add `shortcut:` comment noting the race window and upgrade trigger.

### 5. Session authentication, Admin-only, explicit 401 vs 403

All endpoints are wrapped by one decorator that:

1. returns **401** if `request.user.is_authenticated` is false;
2. returns **403** if the user is inactive;
3. returns **403** unless `is_superuser` or in the `Admin` group.

CSRF applies to POST/PATCH/DELETE through `CsrfViewMiddleware`; views used by tests authenticate with `client.force_login()`, and real clients must send the CSRF token. `@require_http_methods` restricts methods per route (`GET`/`POST` on the collection, `GET`/`PATCH` on the detail; DELETE on the detail); wrong methods return **405**.

Rationale: the spec already fixes these codes. A decorator keeps the check out of every view and is trivially testable. Alternative: middleware — over-broad and hides which routes are protected.

### 6. API contract implemented per spec

Collection `GET /api/users/`:

- `search` → `email__icontains`; whitespace-only ignored.
- `is_active` → `true`/`false` case-insensitive; anything else → 400.
- `page` (default 1) and `page_size` (default 20, max 100) parsed as integers; non-integer, `< 1`, or `> 100` → 400.
- Order by `id`; envelope `{count, page, page_size, total_pages, results}`; `total_pages = ceil(count / page_size)`, `0` when count is 0; page beyond the end → empty `results`, HTTP 200.
- Single query with `.select_related()` unnecessary (no relations read) but `.only(...)`/`values` are avoided for clarity; pagination is `QuerySet` slicing, not `Paginator`, to control the empty-page behavior.

Detail routes: `GET`, `PATCH`, `DELETE` on `/api/users/<int:user_id>/`.

Writable fields: `username`, `email`, `first_name`, `last_name`, `password`, `role`, `is_active`. Any other key → 400 (reject unknown fields rather than ignore them). Missing required fields on create (`username`, `email`, `password`, `role`) → 400. PATCH is partial: omitted fields unchanged, `password` omitted leaves the hash untouched.

Password: `validate_password` with the user instance, then `set_password`. The response serializer is a fixed dict: `id`, `username`, `email`, `first_name`, `last_name`, `role`, `is_active`, `date_joined`. No password field, ever.

### 7. Service layer holds the business rules

`users/services.py` exposes `list_users(filters)`, `create_user(data)`, `update_user(user, data, actor)`, `delete_user(user, actor)`. Views only parse the request, call the service, and map a result/exception to HTTP.

The service enforces, inside `transaction.atomic()`:

- superuser is read-only → **409** on update/delete;
- self-delete and self-deactivate → **409**;
- last active Admin cannot be deleted, deactivated, or demoted → **409** (checked with `select_for_update()` on the Admin group's active members to make the count serializable);
- duplicate username/email → **400**;
- invalid role → **400**.

Rationale: these rules are easy to bypass if they live in views, and the 409/400 split must be consistent. Alternative: model `clean()`/signals — signals fire on paths that should not be blocked (e.g. `createsuperuser`), and `clean()` is not called by `save()`.

Last-Admin check and mutation run in one transaction so two concurrent demotions cannot both pass. `select_for_update()` requires the surrounding `transaction.atomic()`, which the service provides.

### 8. Data migration for roles

One migration in `users/migrations/` creates the three groups with `get_or_create(name=...)` and a reverse that deletes only groups it created (guarded by "no users assigned"). It does not touch the `admin` superuser or any user rows.

Rationale: roles must exist before the API is usable in any environment. Alternative: create groups lazily on first use — hides failures and races.

### 9. Error shape

Errors are `{"detail": "..."}` for auth/404/409 and `{"errors": {"field": ["message"]}}` for validation (400). This keeps one predictable shape for tests and clients; the spec only requires "a validation error", so the exact keys are an implementation detail and are documented in the README section or docstring.

### 10. Tests with Django `TestCase`

`users/tests/test_views.py`, `test_services.py`, `test_permissions.py` using `django.test.TestCase` and `Client`. `force_login` for sessions; `override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])` to keep the suite fast. Verification commands: `python manage.py test users`, `python manage.py check`.

## Risks / Trade-offs

- **Baseline repair touches files outside the feature** → keep the change to the minimum needed for `check` to pass; do not reformat `settings.py`/`urls.py`.
- **Hard delete destroys history** → acceptable for this change; audit logging is explicitly out of scope. If the portal later needs recovery, switch to soft delete in a follow-up.
- **Case-insensitive email is app-enforced, so a direct DB write or a race can create a duplicate** → documented shortcut; mitigated by the Admin-only API and optional functional index.
- **`auth.User` cannot be swapped later without pain** → decision is deliberate; roles as groups keep the door open for a profile model if needed.
- **Plain Django means hand-rolled validation and pagination** → covered by tests; code volume stays small for five endpoints.
- **409 for protection conflicts, 400 for input errors** → clients must distinguish; documented in the response contract.
- **Plain-text password in request logs** → Django does not log bodies by default; do not add body logging in this change.
- **Superuser bypass**: `admin` is not editable/deletable through the API, so a lost superuser must be recovered with `createsuperuser`, not the API.

## Migration Plan

1. Create `users/` with `apps.py` and `__init__.py`; confirm `manage.py check` passes and `migrate` reports no pending core migrations.
2. Add the roles data migration; `python manage.py migrate users` creates `Admin`, `Editor`, `Author`; reverse removes them only when unused.
3. Deploy code; the API is additive under `/api/users/`, so no existing consumer breaks (there are none).
4. Rollback: revert the code and run `python manage.py migrate users zero` to drop the groups; no user rows were modified, so no data loss. If the functional email index was added, its reverse migration drops the index.

## Open Questions

None that change the specs or the task breakdown. The approval questions in the proposal response (DRF vs plain Django, groups vs profile, hard vs soft delete, functional email index, `is_staff` for Admin-role users) are recorded as decisions above with a provisional default; if the user picks a different option, only the tasks named in that question change, not the specs.

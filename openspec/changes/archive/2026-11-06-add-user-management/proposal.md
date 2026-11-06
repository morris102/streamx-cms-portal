# Proposal

## Why

The CMS Portal has no working user-management module: the `users` app referenced by `config/settings.py` and `config/urls.py` is missing from disk, so `python manage.py check` fails, and there is no API for administering accounts or roles. The portal needs a reliable Admin-facing way to manage the Admin, Editor, and Author roles before content workflows can be built on top of them.

## What Changes

- Recreate the `users` Django app and restore a working project baseline (`manage.py check` must pass).
- Add an Admin-only JSON API under `/api/users/`:
  - `GET /api/users/` — list users with email search, pagination, and active/inactive filtering.
  - `POST /api/users/` — create a user.
  - `GET /api/users/{id}/` — view one user.
  - `PATCH /api/users/{id}/` — update a user.
  - `DELETE /api/users/{id}/` — delete a user.
- Represent roles as Django `Group`s named `Admin`, `Editor`, and `Author`; assign exactly one role per user. Keep Django's default `auth.User` model and do not change `AUTH_USER_MODEL`.
- Treat superusers as Admins. Only Admins and superusers may use the user-management API.
- Validate and protect: required unique username, required unique email (case-insensitive), password hashing and Django password validators, whitelisted writable fields, role whitelist, no self-deletion, and no removal/demotion/deactivation of the last active Admin.
- Use the existing Django session authentication; do not add token/JWT authentication in this change.
- Add automated tests for CRUD, roles, search, pagination, filtering, validation, authorization, and security boundaries.
- Keep the API framework as plain Django JSON views because Django REST Framework is not configured. Adding DRF is a pending decision, not part of the provisional plan.

## Capabilities

### New Capabilities

- `user-management`: Admin-only account CRUD, email search, pagination, and active/inactive filtering.
- `role-based-access-control`: the Admin, Editor, and Author roles, their assignment, and the authorization rules for user-management operations.

### Modified Capabilities

None.

## Impact

- `users/` app recreated: app config, URL routes, views, service/business logic, validation helpers, and tests.
- `config/urls.py` and `config/settings.py` already reference `users`; they are corrected/confirmed rather than redesigned.
- Database: Django `auth_group` data for the three roles via a data migration; an optional unique index on lower-cased `auth_user.email` (pending approval). No custom user model, no destructive migration.
- Dependencies: none added if plain Django is approved; DRF would add `djangorestframework` if selected.
- API: new `/api/users/` endpoints; no existing API contract is preserved because the app is currently absent.
- Security: authorization checks, input validation, password handling, and protection against privilege escalation/last-Admin lockout.
- Out of scope: login/logout endpoints, password-reset email flow, self-service profile editing, a custom frontend, content permissions for Editor/Author, audit logging, and production deployment changes.

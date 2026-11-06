# Tasks

Dependency summary: **1 → 2 → 3 → {4, 5} → 6 → {7, 8} → 9**. Tasks inside a group may run in parallel unless stated otherwise.

## 1. Baseline repair

- [x] 1.1 Recreate the `users` Django app package (`__init__.py`, `apps.py` with `UsersConfig`) and register it correctly, then verify `python manage.py check` exits 0 with no `ModuleNotFoundError` and no `users` warnings. *(blocks every later task)*
- [x] 1.2 Confirm `config/settings.py` `INSTALLED_APPS` and `config/urls.py` include `users` exactly once and `/api/users/` resolves, then verify with `python manage.py check` and `python manage.py show_urls`-equivalent (`manage.py shell -c "from django.urls import get_resolver; print(get_resolver().url_patterns)"`). *(depends on 1.1)*
- [x] 1.3 Add `users/tests/__init__.py` and a smoke test that reverses `users:user-list` and asserts the URL prefix, then verify `python manage.py test users` runs (even with 0 feature tests). *(depends on 1.1)*

## 2. Database and roles

- [x] 2.1 Add the data migration that `get_or_create`s the `Admin`, `Editor`, and `Author` groups, with a reverse that deletes each group only when it has no members, then verify `python manage.py migrate users` twice (idempotent) and `python manage.py migrate users zero` then `migrate users` again. *(depends on 1.1)*
- [x] 2.2 Decide the email-uniqueness enforcement (functional unique index vs code-only). If the index is approved, add the `UniqueConstraint(Lower("email"))` migration using `SeparateDatabaseAndState` and a pre-check that fails loudly on existing duplicates; otherwise record the deferred `shortcut:` comment in the service. Verify with `python manage.py sqlmigrate users <n>` and a duplicate-insert test. *(depends on 2.1; approval question)*
- [x] 2.3 Confirm the migration leaves the existing `admin` superuser and all `auth_user` rows untouched, verifying with a before/after row count and `is_superuser` assertion in a migration test or a documented SQL check. *(depends on 2.1)*

## 3. Backend foundation: validation, authorization, serialization

- [x] 3.1 Implement request parsing and field validation for the user contract (required and optional fields, unknown-field rejection, role whitelist, password validators, case-insensitive username/email duplicate checks), then verify unit tests in `users/tests/test_validation.py` cover each rejection path. *(depends on 2.1)*
- [x] 3.2 Implement the fixed user response serializer (no password, `role` derived from groups with superuser → `Admin`), then verify a unit test asserts the exact key set and that no password/hash/token key can leak. *(depends on 3.1)*
- [x] 3.3 Implement the single authorization decorator (401 unauthenticated, 403 inactive, 403 non-Admin, 405 wrong method) and apply it to all routes, then verify `users/tests/test_permissions.py` covers Admin, superuser, Editor, Author, inactive Admin, and anonymous for every endpoint. *(depends on 1.2; can run in parallel with 3.1)*
- [x] 3.4 Configure the URL routes (`/api/users/` and `/api/users/<int:user_id>/`) with `require_http_methods`, then verify `reverse()` for every route name in a test and that an unknown method returns 405. *(depends on 3.3)*

## 4. Backend: create, view, update, delete

- [x] 4.1 Implement `create_user` in the service layer with hashing, role assignment, `is_active` default, and duplicate handling, then verify tests cover success (201 + hashed password + one group), duplicate username/email including case variants, invalid password, invalid role, missing fields, and unknown fields. *(depends on 3.1, 3.2)*
- [x] 4.2 Implement `get_user` and the detail GET view, then verify tests cover 200 for an existing user and 404 for a missing ID. *(depends on 3.4)*
- [x] 4.3 Implement `update_user` with partial-update semantics, password re-hashing, and role replacement via `groups.set`, then verify tests cover field updates, password change followed by `check_password`, duplicate-on-update, invalid role, unknown field, missing user, and unchanged role when omitted. *(depends on 4.1)*
- [x] 4.4 Implement `delete_user` with protected-operation checks, then verify tests cover 204 + row gone, 404 for a missing user, and that no cascade deletes another user's data. *(depends on 4.2)*
- [x] 4.5 Implement the protection rules in the service — superuser read-only (409), self-delete/self-deactivate (409), last active Admin delete/deactivate/demote (409) — each inside `transaction.atomic()`, with `select_for_update()` on the active Admin set, then verify `users/tests/test_protections.py` covers every scenario in `role-based-access-control` including "another active Admin allows the change". *(depends on 4.3, 4.4)*

## 5. Backend: listing, search, pagination, filtering

- [x] 5.1 Implement the list query builder for `search` and `is_active` with the spec's case-insensitive and blank-input rules, then verify tests cover partial match, case-insensitive match, blank/whitespace ignored, `true`/`false`/mixed case, invalid value → 400, and combined search + filter. *(depends on 3.4)*
- [x] 5.2 Implement pagination parsing and the response envelope (`count`, `page`, `page_size`, `total_pages`, `results`) with defaults 1/20, max 100, ordering by `id`, and empty results beyond the last page, then verify tests cover defaults, custom page/size, invalid values, page beyond end, and `total_pages` when `count` is 0. *(depends on 5.1)*
- [x] 5.3 Verify the list endpoint issues one query for the page and does not N+1 on role resolution, using `assertNumQueries` with a documented expected count (adjust if role resolution adds a prefetch). *(depends on 5.2)*

## 6. QA: integration matrix

- [x] 6.1 Write the end-to-end API test matrix in `users/tests/test_integration.py` that exercises each spec scenario across create → list → view → update → delete in one flow, including role changes taking effect on the next request, and verify `python manage.py test users` passes. *(depends on 4.5, 5.2)*
- [x] 6.2 Verify the full suite on a fresh test database (`python manage.py test` with no reuse) and record the run output; confirm the development database is not modified. *(depends on 6.1)*
- [x] 6.3 Verify `python manage.py check` and `python manage.py makemigrations --check --dry-run` both pass with no pending model changes. *(depends on 6.1)*

## 7. Security review

- [x] 7.1 Review authorization coverage: every endpoint is behind the decorator, no IDOR (users can only be reached by ID through an Admin-authorized route), and no client-supplied `is_superuser`/`is_staff`/group escalation path; verify by grepping the URLconf for undecorated views and running the permission test suite. *(depends on 4.5)*
- [x] 7.2 Review input/output safety: parameterized ORM only, no raw SQL, no password in responses/logs, unknown fields rejected, password validators applied; verify with a repo-wide grep for raw SQL and a test asserting the response key set. *(depends on 6.1)*
- [x] 7.3 Review transport/session controls: CSRF enforced on unsafe methods, no `@csrf_exempt`, session cookie flags unchanged from the approved baseline, and no new secrets committed; verify with grep and `python manage.py check --deploy` (document any pre-existing warnings rather than fixing them here). *(depends on 6.1)*
- [x] 7.4 Record findings and any residual risks in the change's review notes; any high-severity finding blocks task 8. *(depends on 7.1, 7.2, 7.3)*

## 8. Code review and integration

- [x] 8.1 Review the diff against `specs/user-management/spec.md` and `specs/role-based-access-control/spec.md` scenario by scenario and confirm every requirement has a corresponding test; verify with a mapping table in the review notes. *(depends on 6.1, 7.4)*
- [x] 8.2 Review for scope creep and simplicity: no new dependency, no custom user model, no unused abstraction, no unrelated file changes; verify with `git status` and a read of the full diff. *(depends on 8.1)*
- [x] 8.3 Run the final gate — `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test` — and record the exact commands and results in the change. *(depends on 8.2)*
- [x] 8.4 Present the implementation summary and remaining risks to the Orchestrator for approval before archive. *(depends on 8.3)* — approved by the product owner on 2026-11-06.

## Workflow follow-up

- Archive `add-user-management` after approval, syncing the `user-management` and `role-based-access-control` deltas into main specs.
- Verify the archived change and that `openspec validate --all` passes.

# Tasks

Dependency summary: **1 → 2 → 3 → 4 → 5 → 6 → 7**. Agents per task: DB (none needed), Backend, QA, Security, Reviewer, Orchestrator.

## 1. Backend: specification file

- [x] 1.1 Write `users/openapi.json` documenting all five user-management operations: paths `/api/users/` (GET, POST) and `/api/users/{user_id}/` (GET, PATCH, DELETE); request schemas `UserCreateRequest` and `UserUpdateRequest` (seven writable fields only); component schema `User` (the eight-field response shape, no credentials); responses 200/201/204 and errors 400/401/403/404/405/409 with `ValidationError` (`errors` map) and `Error` (`detail`) components; `securitySchemes` documenting Django session cookie auth and the CSRF requirement; `info` with title/version. Verify by loading with the stdlib `json` module. *(depends: none)*

## 2. Backend: documentation endpoints

- [x] 2.1 Add `openapi_spec` and `api_docs` views to `users/views.py`, both wrapped by `admin_required`; add routes in `users/urls.py` (`GET /api/openapi.json/` returning the parsed file, `GET /api/docs/` rendering the Swagger UI template). Create `users/templates/users/docs.html` (minimal page, Swagger UI from CDN pointed at `/api/openapi.json/`). Verify `GET /api/openapi.json/` returns 200 JSON and `GET /api/docs/` returns 200 HTML when logged in as Admin, 401 anonymous, 403 Editor. *(depends: 1.1)*

## 3. QA: drift tests

- [x] 3.1 Add `users/tests/test_docs.py`: spec parses as JSON; documented path/method set equals the implemented route set; `User` schema keys equal the response serializer keys; docs/spec endpoints return the correct status codes for anonymous, non-Admin, and Admin callers. *(depends: 2.1)*

## 4. QA: regression

- [x] 4.1 Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and the full `python manage.py test` suite; confirm the 55 existing tests still pass and record the output. *(depends: 3.1)*

## 5. Security review

- [x] 5.1 Confirm both documentation endpoints enforce Admin-only access (no anonymous/Editor access), the spec contains no secrets or credential fields, response schemas exclude password/hash/token fields, and no new dependency introduces a supply-chain or attack surface risk. Record findings in `review.md`. *(depends: 2.1; parallel with 3.1, 4.1)*

## 6. Independent review

- [x] 6.1 Review the implementation against `specs/api-documentation/spec.md` scenario by scenario, confirm every openapi document entry matches `users/views.py` status codes, confirm no over-engineering (no DRF, no new dependency, no unused abstraction), and record the review verdict in `review.md`. *(depends: 4.1, 5.1)*

## 7. Orchestrator: integration and archive

- [x] 7.1 Address any findings raised in 5 and 6, re-run the gates, sync the `api-documentation` delta into `openspec/specs/`, and archive this change. Handle the sibling change `add-user-management` (task 8.4: archive approval) before or after, as approved. *(depends: 6.1)* — reviewed 2026-11-06; no findings to address. Archived as `2026-11-06-add-user-management-api`; the sibling change was archived first as `2026-11-06-add-user-management`.

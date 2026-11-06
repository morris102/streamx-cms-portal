# Proposal

## Why

The user-management endpoints (`GET/POST /api/users/`, `GET/PATCH/DELETE /api/users/{id}/`) are implemented and tested, but the project has no machine-readable API contract: there is no OpenAPI file, no documentation endpoint, and no interactive UI. Consumers of the API must read source code or hand-written notes to learn the request/response shapes, status codes (201/204/400/401/403/404/405/409), and authentication model. An OpenAPI 3.x specification served by the project removes that cost and becomes the single source of truth for the API surface.

## What Changes

- Add a hand-maintained OpenAPI 3.0 specification (`openapi.json`) describing all five user-management operations, their request/response schemas, error responses, and session authentication.
- Serve the specification at `GET /api/openapi.json/` so it can be consumed by tooling and exported by saving the response.
- Serve a Swagger UI page at `GET /api/docs/` backed by the served specification.
- Restrict both documentation endpoints to authenticated Admin users (same rule as the API itself).
- Add a drift-protection test: the suite parses the specification and asserts it covers every route, method, and response status implemented in `users/views.py`.

### Already complete (no work in this change)

The create/update/delete APIs themselves, PostgreSQL integration, role model, protection rules, and their tests were delivered by the sibling change `add-user-management`, which is at 28/29 tasks awaiting archive approval. This change does not re-implement them and does not modify the API behavior.

## Capabilities

### New Capabilities

- `api-documentation`: the OpenAPI specification, its documentation endpoints, export path, and accuracy guarantees.

### Modified Capabilities

None. The `user-management` and `role-based-access-control` requirements are unchanged; the specification documents them as they exist.

## Impact

- `users/openapi.json` — new data file (the specification).
- `users/views.py` — two new function views (serve spec, serve Swagger UI page), reusing the existing `admin_required` decorator.
- `users/urls.py` — two new routes.
- `users/templates/users/docs.html` — one template (CDN-loaded Swagger UI).
- `users/tests/` — new drift and endpoint tests.
- Dependencies: none. Django REST Framework is not installed; adding DRF plus drf-spectacular solely for documentation would rewire auth, pagination, and error handling for a solved API. A maintained JSON file with automated drift tests is the smaller, honest contract for five stable endpoints. *(Approval question D-1.)*
- Database: no schema changes; no migrations.
- Security: documentation endpoints are Admin-only, so the API surface is not exposed to anonymous visitors; the spec contains no secrets or credentials.

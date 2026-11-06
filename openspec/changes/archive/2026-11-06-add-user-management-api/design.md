# Design

## Context

The API exists (`add-user-management`, 28/29 tasks, pending archive). Facts verified in this session:

- Plain Django function views + `JsonResponse`; DRF is not installed (`requirements.txt`: Django 6.1.3, psycopg 3, python-dotenv).
- Session auth via `admin_required` decorator; CSRF enforced by middleware. 401/403/404/405/409/201/204 semantics are fixed and tested (55 tests).
- Response contract: success = fixed key set `id, username, email, first_name, last_name, role, is_active, date_joined`; validation errors = `{"errors": {...}}` (400); rejections = `{"detail": ...}` (401/403/409).
- No OpenAPI file, no docs endpoints, no static file for a spec exists today.

## Goals / Non-Goals

**Goals:** one accurate OpenAPI 3.0 document, served and browsable, with tests that fail if it drifts from the code.

**Non-Goals:** adding DRF; auto-generating the spec at request time from annotations; public-facing docs; documenting endpoints that don't exist; login/logout or password-reset flows (out of scope from the previous change; not documented).

## Decisions

### 1. Hand-maintained `openapi.json`, not drf-spectacular

drf-spectacular requires DRF, which is not installed. Installing DRF just for docs is out of proportion, and a maintained spec is honest here because a drift test enforces accuracy.

Rationale for **JSON** over YAML: the test suite can parse JSON with the stdlib (`json` module); YAML would add a PyYAML dependency solely for test validation. The request allows "`openapi.yaml` or `openapi.json`". **Approval question D-1:** if the project wants docs generated from code (worth it when more APIs are added), the right move is adopting DRF + drf-spectacular (or hand-rolled schema generation) as a separate change—not this one. *(Provisional: no new dependencies.)*

### 2. File location and serving

The spec lives at `users/openapi.json` next to the code it describes. `users/views.py` gains two views:

- `openapi_spec` — reads the file relative to `__file__`, returns it as `JsonResponse` (stdlib `json` reads it, guaranteeing valid JSON before it ever reaches a client).
- `api_docs` — renders `users/templates/users/docs.html`, a minimal page that loads Swagger UI from its CDN and points it at `/api/openapi.json/`.

Both are wrapped in the existing `admin_required` decorator, so 401/403 behavior is identical to the API. Routes: `users/urls.py` gains `path("openapi.json/", ...)` and `path("docs/", ...)`.

Net new lines: one data file, two five-line views, two URL entries, one small template. No dependencies.

### 3. Spec content mirrors the implemented contract exactly

Documented per operation: parameters (query params for list: `page`, `page_size`, `search`, `is_active`; path param `user_id`), request bodies (`UserCreateRequest`, `UserUpdateRequest` with only the seven writable fields), responses with all implemented status codes, and components: `User` (the eight-field success shape), the two request schemas, `ValidationError` (`errors`), `Error` (`detail`). `securitySchemes` documents `sessionAuth` (cookie, Django session) plus the CSRF requirement stated in the operation description;Swagger "try it out" works with docs pages loaded in the same session.

No operation will document a status code the views cannot return (verified against `users/views.py` line-by-line when writing the file). The spec contains no credentials or secrets.

### 4. Drift test

`users/tests/test_docs.py`:

1. `GET /api/openapi.json/` returns 200 and parses as JSON with the stdlib.
2. Reverse-engineered URL list (from `users/urls.py`) equals the spec's user-management paths × methods — every documented operation exists and no implemented operation is missing.
3. The `User` schema key set equals the response serializer's key set (import `USER_KEYS` set from `serializers.py` if it's factored out, else inline the expected list with a comment to keep it in sync).
4. `/api/docs/` returns 200 with Swagger UI assets referenced.

This is the cheapest real guarantee that the spec is not stale; a code-generation toolchain would add more moving parts for the same result.

### 5. Route placement detail

`openapi.json` contains a `.`, which `path("openapi.json/", ...)` handles correctly since it's a static segment, conflicting with nothing—the URL names are `users:openapi-json` and `users:api-docs`.

## Risks / Trade-offs

- **Hand-maintained spec can go stale** → mitigated by the drift test; the test fails before CI/merge notices a mismatch.
- **CDN-loaded Swagger UI unavailable offline / behind strict CSP** → acceptable for an internal Admin tool; vendoring the two static assets is a trivial follow-up if the deployment blocks CDNs. The served JSON itself never leaves the repo.
- **Hand-written spec is not auto-derived from code** → deliberate trade-off (D-1); revisit with DRF when the API surface grows.
- **`/api/docs/` exposes the API surface to any logged-in session** → it is Admin-gated, same as the API itself, and documents nothing secret (no data, no credentials, only shapes).

## Migration Plan

No database changes. Deploy is additive: two new URLs, no existing route or behavior changes. Rollback: delete the file/views/routes/template, then revert tests—the API behavior is untouched.

## Open Questions

- **D-1 (approval):** No-dependency hand-maintained `openapi.json` (provisional) vs. adopting DRF + drf-spectacular to auto-generate. The latter would also need to rewire pagination/error handling/serializers to the currently hand-rolled equivalents; deferred unless the project wants DRF for other reasons.

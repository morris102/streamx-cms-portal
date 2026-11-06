# Review Notes

## Requirement to test mapping (`api-documentation`)

| Spec requirement | Tests (`users/tests/test_docs.py`) |
| --- | --- |
| OpenAPI specification file (served + export) | `OpenApiSpecTests::test_spec_file_is_valid_json`, `DocsEndpointTests::test_admin_gets_spec_json` |
| Interactive documentation UI | `DocsEndpointTests::test_admin_gets_swagger_ui` |
| Documentation is Admin-only | `DocsEndpointTests::test_anonymous_is_unauthorized`, `::test_non_admin_is_forbidden` |
| Specification documents the implemented contract | `OpenApiSpecTests::test_documented_operations_match_implementation` |
| ... user response excludes credentials | `OpenApiSpecTests::test_user_schema_has_no_credentials`, `::test_request_schemas_are_write_only` |
| Specification drift is caught by tests | the whole of `OpenApiSpecTests` |

## Security review

| Check | Result |
| --- | --- |
| Doc endpoints Admin-only | Pass — `admin_required` on both views; tests assert 401/403/200 |
| Secrets in spec | Pass — only shapes, paths, and status codes; no credentials (tested) |
| Password fields | Pass — `password` exists only in request schemas; response schema key set is hardcoded to `USER_KEYS` (tested) |
| CSRF | Pass — no `@csrf_exempt`; CSRF documented as `X-CSRFToken`; middleware still enforces it |
| Raw SQL / auth changes | Pass — grep for `csrf_exempt`, `.raw(`, `cursor.`, `.extra(` returns nothing; auth code untouched |
| New dependencies | Pass — none added; browser loads Swagger UI assets from unpkg CDN |
| Regression | Pass — full suite 63/63 OK (55 pre-existing + 8 new) |

Residual risks:

- Swagger UI assets load from CDN in the Admin's browser; offline or strict-CSP deployments need the two assets vendored. Follow-up if deployment blocks external scripts.
- The spec is hand-maintained; staleness is caught by the drift test, not prevented. Trade-off approved as D-1 (no-dependency approach).

## Reviewer verdict

Scenario-by-scenario deltas were compared against `users/views.py` status codes: documented responses are exactly 200/201/204 (success) and 400/401/403/404/405/409 (errors) — including PATCH/DELETE 409 with their three protection messages and the list 400 for invalid pagination/filter parameters. No undocumented implemented operation; no documented non-implemented behavior. No new dependency, no abstraction, no unrelated file touched.

**Decision: APPROVED.**

## Gate results

- `python manage.py test` — 63 tests, OK.
- `python manage.py check` — System check identified no issues.
- `python manage.py check --deploy` — same 8 pre-existing deployment-hardening warnings as the previous change (`mail.E001`, HSTS, SSL redirect, `django-insecure-` SECRET_KEY, cookie flags, DEBUG, ALLOWED_HOSTS). Predate this change; out of scope.

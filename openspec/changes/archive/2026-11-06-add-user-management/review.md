# Review Notes

## Requirement to test mapping

| Spec requirement | Tests |
| --- | --- |
| `user-management` — Paginated user listing | `test_views.py::test_pagination_envelope_and_beyond_last_page`, `::test_invalid_pagination_is_400`, `::test_list_query_count_is_constant` |
| `user-management` — Email search | `test_views.py::test_search_is_case_insensitive_and_blank_is_ignored`, `::test_search_and_active_filter_combine` |
| `user-management` — Active/inactive filtering | `test_views.py::test_search_and_active_filter_combine`, `::test_invalid_filter_is_400` |
| `user-management` — Create user | `test_views.py::test_create_returns_201_and_safe_representation`, `::test_create_rejects_unknown_field`, `::test_create_rejects_duplicate_username`; `test_services.py::test_create_*` |
| `user-management` — View user | `test_views.py::test_get_user_and_missing_user` |
| `user-management` — Update user | `test_views.py::test_patch_updates_fields_and_returns_200`; `test_services.py::test_update_*` |
| `user-management` — Delete user | `test_views.py::test_delete_returns_204_and_removes_user`; `test_services.py::test_delete_removes_user` |
| `user-management` — Response excludes credentials | `test_views.py::test_create_returns_201_and_safe_representation` (exact `USER_KEYS`) |
| `role-based-access-control` — Three roles exist | `test_services.py::test_create_hashes_password_and_assigns_one_role`; `test_validation.py::test_invalid_role` |
| `role-based-access-control` — Role assignment | `test_services.py::test_update_replaces_role`, `::test_update_omitted_role_is_unchanged` |
| `role-based-access-control` — Admin-only user management | `test_permissions.py` (anonymous, Editor, Author, Admin, superuser) |
| `role-based-access-control` — Superuser read-only | `test_services.py::test_superuser_is_read_only`; `test_integration.py::test_protected_operations_return_409` |
| `role-based-access-control` — Last active Admin protected | `test_services.py::test_last_admin_cannot_be_demoted`, `::test_admin_cannot_deactivate_self`; `test_integration.py::test_protected_operations_return_409` |
| `role-based-access-control` — Self-protection | `test_services.py::test_admin_cannot_delete_self`, `::test_admin_cannot_deactivate_self`; `test_integration.py::test_protected_operations_return_409` |
| `role-based-access-control` — Role changes take effect immediately | `test_integration.py::test_role_change_takes_effect_on_next_request` |
| `role-based-access-control` — Inactive accounts cannot administer | `test_permissions.py::test_inactive_admin_is_forbidden` |

## Security review

| Check | Result |
| --- | --- |
| All routes go through `admin_required` | Pass — both routes in `users/urls.py` |
| IDOR | Pass — detail routes are Admin-authorized; no client-supplied identity fields are trusted |
| Privilege escalation | Pass — `is_superuser`, `is_staff`, and groups are not writable; role whitelist enforced |
| Raw SQL | Pass — none (`grep` for `.raw(`, `cursor.`, `.extra(` returned nothing) |
| CSRF | Pass — no `csrf_exempt`; test confirms unsafe request without token is rejected |
| Credentials in output/logs | Pass — fixed response key set; no password, hash, or token fields |
| Password storage | Pass — `set_password` / validators; no plaintext storage |
| Last-Admin lockout | Pass — checked under `select_for_update()` on the Admin group; 409 returned |
| Secrets committed | Pass — no secret values in `users/` |

Residual risks:

- Case-insensitive email uniqueness is application-level only; a direct DB write or a concurrent insert can create a duplicate. Marked with a `shortcut:` comment in `users/services.py`.
- `python manage.py check --deploy` still reports pre-existing project issues (`MAILERS` console backend as `mail.E001`, plus `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and cookie/HTTPS warnings). These predate this change and are out of scope; they are deployment hardening items.
- `__pycache__` and `*.pyc` are not in `.gitignore`, so generated files appear as untracked. Unrelated cleanup; no generated file was added to the change.

## Gate results

- `python manage.py check` — no issues.
- `python manage.py makemigrations --check --dry-run` — no changes detected.
- `python manage.py test` — 55 tests, OK.

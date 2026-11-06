"""Authorization helpers for the user-management API."""

from functools import wraps

from django.contrib.auth.models import Group, User
from django.http import JsonResponse

ROLE_NAMES = ("Admin", "Editor", "Author")
ADMIN_ROLE = "Admin"


def role_for(user):
    """Return the effective role name, treating superusers as Admin."""
    if user.is_superuser:
        return ADMIN_ROLE
    for group in user.groups.all():
        if group.name in ROLE_NAMES:
            return group.name
    return None


def has_admin_role(user):
    return user.is_superuser or user.groups.filter(name=ADMIN_ROLE).exists()


def admin_required(view_func):
    """Reject anonymous, inactive, and non-Admin callers before the view runs."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            # Django treats inactive users as anonymous; still report the
            # deactivated session as forbidden rather than unauthenticated.
            session_user_id = request.session.get("_auth_user_id")
            if session_user_id and User.objects.filter(
                pk=session_user_id, is_active=False
            ).exists():
                return JsonResponse(
                    {"detail": "Inactive accounts cannot administer users."},
                    status=403,
                )
            return JsonResponse({"detail": "Authentication required."}, status=401)
        if not user.is_active:
            return JsonResponse(
                {"detail": "Inactive accounts cannot administer users."}, status=403
            )
        if not has_admin_role(user):
            return JsonResponse({"detail": "Admin role required."}, status=403)
        return view_func(request, *args, **kwargs)

    return wrapper

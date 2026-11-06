"""Business rules for user management. Views only parse requests and map results."""

from django.contrib.auth.models import Group, User
from django.db import transaction
from django.db.models import Q

from .permissions import ADMIN_ROLE
from .serializers import serialize_user, total_pages, validate_create, validate_update


class ProtectedOperation(Exception):
    """A valid request blocked by a safety rule, mapped to HTTP 409."""


def list_users(*, page, page_size, search=None, is_active=None):
    queryset = User.objects.prefetch_related("groups").order_by("id")
    if search:
        queryset = queryset.filter(email__icontains=search)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)

    count = queryset.count()
    start = (page - 1) * page_size
    users = queryset[start : start + page_size]
    return {
        "count": count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages(count, page_size),
        "results": [serialize_user(user) for user in users],
    }


@transaction.atomic
def create_user(data):
    cleaned = validate_create(data)
    group = Group.objects.get(name=cleaned["role"])

    user = User(
        username=cleaned["username"],
        email=cleaned["email"],
        first_name=cleaned["first_name"],
        last_name=cleaned["last_name"],
        is_active=cleaned["is_active"],
    )
    user.set_password(cleaned["password"])
    # shortcut: email uniqueness is checked before insert and there is no
    # database index, so a concurrent insert can still create a duplicate.
    # Upgrade to a functional unique index if direct DB writes become possible.
    user.save()
    user.groups.set([group])
    return user


@transaction.atomic
def update_user(user, data, actor):
    # Serializes Admin-changing operations so two concurrent requests cannot
    # both observe "another active Admin exists".
    Group.objects.select_for_update().get(name=ADMIN_ROLE)
    user = User.objects.select_for_update().get(pk=user.pk)

    if user.is_superuser:
        raise ProtectedOperation("Superuser accounts are read-only through the API.")

    cleaned = validate_update(data, user)

    if actor.pk == user.pk and cleaned.get("is_active") is False:
        raise ProtectedOperation("You cannot deactivate your own account.")

    new_role = cleaned.get("role")
    new_active = cleaned.get("is_active")
    if _loses_active_admin(user, new_role, new_active) and not _other_active_admin_exists(
        user.pk
    ):
        raise ProtectedOperation(
            "The last active Admin cannot be demoted or deactivated."
        )

    for field in ("username", "email", "first_name", "last_name"):
        if field in cleaned:
            setattr(user, field, cleaned[field])

    if "password" in cleaned:
        user.set_password(cleaned["password"])
    if new_active is not None:
        user.is_active = new_active
    user.save()

    if new_role is not None:
        user.groups.set([Group.objects.get(name=new_role)])

    return user


@transaction.atomic
def delete_user(user, actor):
    Group.objects.select_for_update().get(name=ADMIN_ROLE)
    user = User.objects.select_for_update().get(pk=user.pk)

    if user.is_superuser:
        raise ProtectedOperation("Superuser accounts are read-only through the API.")
    if actor.pk == user.pk:
        raise ProtectedOperation("You cannot delete your own account.")
    if _is_active_admin(user) and not _other_active_admin_exists(user.pk):
        raise ProtectedOperation("The last active Admin cannot be deleted.")

    user.delete()


def _is_active_admin(user):
    return user.is_active and (
        user.is_superuser or user.groups.filter(name=ADMIN_ROLE).exists()
    )


def _loses_active_admin(user, new_role, new_active):
    if not _is_active_admin(user):
        return False
    role_removed = new_role is not None and new_role != ADMIN_ROLE
    return role_removed or new_active is False


def _other_active_admin_exists(exclude_pk):
    admin_ids = User.objects.filter(
        Q(is_superuser=True) | Q(groups__name=ADMIN_ROLE), is_active=True
    ).values_list("pk", flat=True)
    rows = (
        User.objects.select_for_update()
        .filter(pk__in=admin_ids)
        .exclude(pk=exclude_pk)
        .values_list("pk", flat=True)[:1]
    )
    return bool(list(rows))

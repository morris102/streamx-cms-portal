"""Request parsing, validation, and response serialization for the user API."""

import json
from math import ceil

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

from .permissions import ROLE_NAMES, role_for

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20

WRITABLE_FIELDS = {
    "username",
    "email",
    "first_name",
    "last_name",
    "password",
    "role",
    "is_active",
}
CREATE_REQUIRED_FIELDS = ("username", "email", "password", "role")


class ValidationError(Exception):
    """Field-level validation failure mapped to HTTP 400."""

    def __init__(self, errors):
        self.errors = errors
        super().__init__(str(errors))


def parse_json_body(request):
    try:
        payload = json.loads(request.body or b"{}")
    except (ValueError, UnicodeDecodeError):
        raise ValidationError({"body": ["Request body must be valid JSON."]})
    if not isinstance(payload, dict):
        raise ValidationError({"body": ["Request body must be a JSON object."]})
    return payload


def parse_list_params(query):
    errors = {}
    page = _parse_int(query.get("page", "1"), "page", errors, minimum=1)
    page_size = _parse_int(
        query.get("page_size", str(DEFAULT_PAGE_SIZE)),
        "page_size",
        errors,
        minimum=1,
        maximum=MAX_PAGE_SIZE,
    )

    search = (query.get("search") or "").strip() or None

    is_active = None
    if "is_active" in query:
        raw = query["is_active"].strip().lower()
        if raw == "true":
            is_active = True
        elif raw == "false":
            is_active = False
        else:
            errors.setdefault("is_active", []).append("Must be 'true' or 'false'.")

    if errors:
        raise ValidationError(errors)

    return {
        "page": page,
        "page_size": page_size,
        "search": search,
        "is_active": is_active,
    }


def validate_create(data):
    errors = {}
    _reject_unknown_fields(data, errors)

    username = _clean_username(data, errors, required=True)
    email = _clean_email(data, errors, required=True)
    password = _clean_password(data, errors, required=True)
    role = _clean_role(data, errors, required=True)
    first_name = _clean_name(data, "first_name", errors)
    last_name = _clean_name(data, "last_name", errors)
    is_active = _clean_bool(data, "is_active", errors, default=True)

    if username and User.objects.filter(username=username).exists():
        errors.setdefault("username", []).append("A user with that username already exists.")
    if email and User.objects.filter(email__iexact=email).exists():
        errors.setdefault("email", []).append("A user with that email already exists.")

    if password and not errors.get("password"):
        _run_password_validators(
            password,
            User(username=username or "", email=email or ""),
            errors,
        )

    if errors:
        raise ValidationError(errors)

    return {
        "username": username,
        "email": email,
        "password": password,
        "role": role,
        "first_name": first_name or "",
        "last_name": last_name or "",
        "is_active": is_active,
    }


def validate_update(data, instance):
    errors = {}
    _reject_unknown_fields(data, errors)

    cleaned = {}
    username = _clean_username(data, errors, required=False)
    if username is not None:
        if (
            User.objects.filter(username=username)
            .exclude(pk=instance.pk)
            .exists()
        ):
            errors.setdefault("username", []).append(
                "A user with that username already exists."
            )
        cleaned["username"] = username

    email = _clean_email(data, errors, required=False)
    if email is not None:
        if (
            User.objects.filter(email__iexact=email)
            .exclude(pk=instance.pk)
            .exists()
        ):
            errors.setdefault("email", []).append("A user with that email already exists.")
        cleaned["email"] = email

    for field in ("first_name", "last_name"):
        value = _clean_name(data, field, errors)
        if value is not None:
            cleaned[field] = value

    password = _clean_password(data, errors, required=False)
    if password is not None:
        _run_password_validators(password, instance, errors)
        cleaned["password"] = password

    role = _clean_role(data, errors, required=False)
    if role is not None:
        cleaned["role"] = role

    is_active = _clean_bool(data, "is_active", errors, default=None)
    if is_active is not None:
        cleaned["is_active"] = is_active

    if errors:
        raise ValidationError(errors)
    return cleaned


def serialize_user(user):
    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": role_for(user),
        "is_active": user.is_active,
        "date_joined": user.date_joined.isoformat(),
    }


def total_pages(count, page_size):
    return ceil(count / page_size) if count else 0


def _reject_unknown_fields(data, errors):
    for field in data:
        if field not in WRITABLE_FIELDS:
            errors.setdefault(field, []).append("Unknown field.")


def _parse_int(raw, field, errors, minimum, maximum=None):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        errors.setdefault(field, []).append("Must be an integer.")
        return None
    if value < minimum:
        errors.setdefault(field, []).append(f"Must be at least {minimum}.")
    if maximum is not None and value > maximum:
        errors.setdefault(field, []).append(f"Must be at most {maximum}.")
    return value


def _clean_string(data, field, errors, required, max_length, blank=False):
    if field not in data:
        if required:
            errors.setdefault(field, []).append("This field is required.")
        return None
    value = data[field]
    if not isinstance(value, str):
        errors.setdefault(field, []).append("Must be a string.")
        return None
    if not blank:
        value = value.strip()
    if not value:
        errors.setdefault(field, []).append("This field may not be blank.")
        return None
    if len(value) > max_length:
        errors.setdefault(field, []).append(
            f"Ensure this field has no more than {max_length} characters."
        )
        return None
    return value


def _clean_username(data, errors, required):
    return _clean_string(data, "username", errors, required, 150)


def _clean_name(data, field, errors):
    return _clean_string(data, field, errors, required=False, max_length=150)


def _clean_email(data, errors, required):
    value = _clean_string(data, "email", errors, required, 254)
    if value is not None:
        try:
            validate_email(value)
        except DjangoValidationError:
            errors.setdefault("email", []).append("Enter a valid email address.")
            return None
    return value


def _clean_password(data, errors, required):
    if "password" not in data:
        if required:
            errors.setdefault("password", []).append("This field is required.")
        return None
    value = data["password"]
    if not isinstance(value, str) or not value:
        errors.setdefault("password", []).append("This field may not be blank.")
        return None
    return value


def _clean_role(data, errors, required):
    if "role" not in data:
        if required:
            errors.setdefault("role", []).append("This field is required.")
        return None
    value = data["role"]
    if value not in ROLE_NAMES:
        errors.setdefault("role", []).append(
            "Must be one of: " + ", ".join(ROLE_NAMES) + "."
        )
        return None
    return value


def _clean_bool(data, field, errors, default):
    if field not in data:
        return default
    value = data[field]
    if not isinstance(value, bool):
        errors.setdefault(field, []).append("Must be a boolean.")
        return default
    return value


def _run_password_validators(password, user, errors):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        errors.setdefault("password", []).extend(exc.messages)

"""HTTP layer for the user-management API."""

import json
from pathlib import Path

from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .permissions import admin_required
from .serializers import (
    ValidationError,
    parse_json_body,
    parse_list_params,
    serialize_user,
)
from .services import (
    ProtectedOperation,
    create_user,
    delete_user,
    list_users,
    update_user,
)

SPEC_FILE = Path(__file__).resolve().parent / "openapi.json"


def _validation_error(exc):
    return JsonResponse({"errors": exc.errors}, status=400)


def _conflict(exc):
    return JsonResponse({"detail": str(exc)}, status=409)


@admin_required
@require_http_methods(["GET"])
def openapi_spec(request):
    return JsonResponse(json.loads(SPEC_FILE.read_text()))


@admin_required
@require_http_methods(["GET"])
def api_docs(request):
    return render(request, "users/docs.html")


# @admin_required
@require_http_methods(["GET", "POST"])
def user_collection(request):
    if request.method == "GET":
        try:
            params = parse_list_params(request.GET)
        except ValidationError as exc:
            return _validation_error(exc)
        return JsonResponse(list_users(**params))

    try:
        payload = parse_json_body(request)
        user = create_user(payload)
    except ValidationError as exc:
        return _validation_error(exc)
    return JsonResponse(serialize_user(user), status=201)


@admin_required
@require_http_methods(["GET", "PATCH", "DELETE"])
def user_detail(request, user_id):
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return JsonResponse({"detail": "User not found."}, status=404)

    if request.method == "GET":
        return JsonResponse(serialize_user(user))

    if request.method == "DELETE":
        try:
            delete_user(user, request.user)
        except ProtectedOperation as exc:
            return _conflict(exc)
        return HttpResponse(status=204)

    try:
        payload = parse_json_body(request)
        user = update_user(user, payload, request.user)
    except ValidationError as exc:
        return _validation_error(exc)
    except ProtectedOperation as exc:
        return _conflict(exc)
    return JsonResponse(serialize_user(user))

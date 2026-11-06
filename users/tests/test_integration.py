import json

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from users.permissions import ROLE_NAMES

PASSWORD = "V3ry-Str0ng-Pass!42"


class IntegrationTests(TestCase):
    def setUp(self):
        for name in ROLE_NAMES:
            Group.objects.get_or_create(name=name)
        self.admin = self._make("admin", "Admin")
        self.client.force_login(self.admin)
        self.list_url = reverse("users:user-list")

    def _make(self, username, role=None, *, superuser=False):
        user = User(
            username=username,
            email=f"{username}@example.com",
            is_superuser=superuser,
            is_staff=superuser,
        )
        user.set_password(PASSWORD)
        user.save()
        if role:
            user.groups.set([Group.objects.get(name=role)])
        return user

    def _json(self, method, url, payload=None):
        return getattr(self.client, method)(
            url,
            data=json.dumps(payload or {}),
            content_type="application/json",
        )

    def test_full_lifecycle(self):
        created = self._json(
            "post",
            self.list_url,
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": PASSWORD,
                "role": "Author",
            },
        )
        self.assertEqual(created.status_code, 201)
        user_id = created.json()["id"]

        listing = self.client.get(self.list_url, {"search": "alice", "is_active": "true"})
        self.assertEqual(listing.json()["count"], 1)

        detail_url = reverse("users:user-detail", args=[user_id])
        updated = self._json("patch", detail_url, {"role": "Editor", "first_name": "Al"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["role"], "Editor")

        fetched = self.client.get(detail_url)
        self.assertEqual(fetched.json()["first_name"], "Al")

        deleted = self.client.delete(detail_url)
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(detail_url).status_code, 404)

    def test_role_change_takes_effect_on_next_request(self):
        author = self._make("author", "Author")
        promoted = self._json(
            "patch",
            reverse("users:user-detail", args=[author.pk]),
            {"role": "Admin"},
        )
        self.assertEqual(promoted.status_code, 200)

        self.client.force_login(author)
        self.assertEqual(self.client.get(self.list_url).status_code, 200)

        demoted = self._json(
            "patch",
            reverse("users:user-detail", args=[author.pk]),
            {"role": "Author"},
        )
        self.assertEqual(demoted.status_code, 200)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)

    def test_protected_operations_return_409(self):
        root = self._make("root", superuser=True)
        root.is_active = False
        root.save()
        root_url = reverse("users:user-detail", args=[root.pk])
        self.assertEqual(self._json("patch", root_url, {"first_name": "R"}).status_code, 409)
        self.assertEqual(self.client.delete(root_url).status_code, 409)

        self_url = reverse("users:user-detail", args=[self.admin.pk])
        self.assertEqual(self.client.delete(self_url).status_code, 409)
        self.assertEqual(
            self._json("patch", self_url, {"is_active": False}).status_code, 409
        )
        self.assertEqual(
            self._json("patch", self_url, {"role": "Editor"}).status_code, 409
        )

    def test_second_admin_allows_role_change(self):
        second = self._make("admin2", "Admin")
        self.client.force_login(second)
        target_url = reverse("users:user-detail", args=[self.admin.pk])
        response = self._json("patch", target_url, {"role": "Editor"})
        self.assertEqual(response.status_code, 200)

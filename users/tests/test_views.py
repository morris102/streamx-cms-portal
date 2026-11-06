import json

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from users.permissions import ROLE_NAMES
from users.services import list_users

PASSWORD = "V3ry-Str0ng-Pass!42"
USER_KEYS = {
    "id",
    "username",
    "email",
    "first_name",
    "last_name",
    "role",
    "is_active",
    "date_joined",
}


def make_user(username, role=None, *, active=True, superuser=False):
    user = User(
        username=username,
        email=f"{username}@example.com",
        is_active=active,
        is_superuser=superuser,
        is_staff=superuser,
    )
    user.set_password(PASSWORD)
    user.save()
    if role:
        user.groups.set([Group.objects.get(name=role)])
    return user


class UserApiTests(TestCase):
    def setUp(self):
        for name in ROLE_NAMES:
            Group.objects.get_or_create(name=name)
        self.admin = make_user("admin", "Admin")
        self.client.force_login(self.admin)
        self.list_url = reverse("users:user-list")

    def _detail(self, user_id):
        return reverse("users:user-detail", args=[user_id])

    def _post(self, payload):
        return self.client.post(
            self.list_url, data=json.dumps(payload), content_type="application/json"
        )

    def _patch(self, user_id, payload):
        return self.client.patch(
            self._detail(user_id),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def _payload(self, username="alice", role="Author", **overrides):
        return {
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
            "role": role,
            **overrides,
        }

    def test_create_returns_201_and_safe_representation(self):
        response = self._post(self._payload())
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(set(body), USER_KEYS)
        self.assertEqual(body["role"], "Author")
        self.assertNotIn("password", body)
        self.assertTrue(User.objects.get(pk=body["id"]).check_password(PASSWORD))

    def test_create_rejects_unknown_field(self):
        response = self._post(self._payload(is_superuser=True))
        self.assertEqual(response.status_code, 400)
        self.assertIn("is_superuser", response.json()["errors"])

    def test_create_rejects_duplicate_username(self):
        self._post(self._payload())
        response = self._post(self._payload(email="other@example.com"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json()["errors"])

    def test_get_user_and_missing_user(self):
        user = make_user("bob", "Editor")
        response = self.client.get(self._detail(user.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "Editor")
        self.assertEqual(self.client.get(self._detail(999999)).status_code, 404)

    def test_patch_updates_fields_and_returns_200(self):
        user = make_user("bob", "Author")
        response = self._patch(
            user.pk, {"first_name": "Bob", "email": "bob2@example.com"}
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.first_name, "Bob")
        self.assertEqual(user.email, "bob2@example.com")

    def test_patch_missing_user_is_404(self):
        self.assertEqual(self._patch(999999, {"first_name": "X"}).status_code, 404)

    def test_delete_returns_204_and_removes_user(self):
        user = make_user("bob", "Author")
        response = self.client.delete(self._detail(user.pk))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())
        self.assertEqual(self.client.delete(self._detail(user.pk)).status_code, 404)

    def test_search_is_case_insensitive_and_blank_is_ignored(self):
        make_user("alice", "Author")
        make_user("bob", "Author")
        response = self.client.get(self.list_url, {"search": "ALICE"})
        self.assertEqual(response.json()["count"], 1)
        blank = self.client.get(self.list_url, {"search": "   "})
        self.assertEqual(blank.json()["count"], 3)

    def test_search_and_active_filter_combine(self):
        make_user("alice", "Author", active=False)
        make_user("alicia", "Author", active=True)
        response = self.client.get(
            self.list_url, {"search": "ali", "is_active": "false"}
        )
        usernames = [row["username"] for row in response.json()["results"]]
        self.assertEqual(usernames, ["alice"])

    def test_invalid_filter_is_400(self):
        self.assertEqual(self.client.get(self.list_url, {"is_active": "maybe"}).status_code, 400)

    def test_pagination_envelope_and_beyond_last_page(self):
        for index in range(3):
            make_user(f"user{index}", "Author")
        response = self.client.get(self.list_url, {"page": 1, "page_size": 2})
        body = response.json()
        self.assertEqual(body["count"], 4)
        self.assertEqual(body["page"], 1)
        self.assertEqual(body["page_size"], 2)
        self.assertEqual(body["total_pages"], 2)
        self.assertEqual(len(body["results"]), 2)

        beyond = self.client.get(self.list_url, {"page": 9, "page_size": 2})
        self.assertEqual(beyond.status_code, 200)
        self.assertEqual(beyond.json()["results"], [])
        self.assertEqual(beyond.json()["count"], 4)

    def test_invalid_pagination_is_400(self):
        self.assertEqual(self.client.get(self.list_url, {"page_size": 101}).status_code, 400)
        self.assertEqual(self.client.get(self.list_url, {"page": "x"}).status_code, 400)

    def test_superuser_reports_admin_role(self):
        root = make_user("root", None, superuser=True)
        response = self.client.get(self._detail(root.pk))
        self.assertEqual(response.json()["role"], "Admin")

    def test_list_query_count_is_constant(self):
        for index in range(5):
            make_user(f"user{index}", "Author")
        # count + page + prefetched groups
        with self.assertNumQueries(3):
            list_users(page=1, page_size=20, search=None, is_active=None)

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from users.permissions import ROLE_NAMES

PASSWORD = "V3ry-Str0ng-Pass!42"


def make_user(username, role=None, *, active=True, superuser=False, **extra):
    user = User(
        username=username,
        email=f"{username}@example.com",
        is_active=active,
        is_superuser=superuser,
        is_staff=superuser,
        **extra,
    )
    user.set_password(PASSWORD)
    user.save()
    if role:
        user.groups.set([Group.objects.get(name=role)])
    return user


class PermissionTests(TestCase):
    def setUp(self):
        for name in ROLE_NAMES:
            Group.objects.get_or_create(name=name)
        self.admin = make_user("admin", "Admin")
        self.superuser = make_user("root", superuser=True)
        self.editor = make_user("editor", "Editor")
        self.author = make_user("author", "Author")
        self.inactive_admin = make_user("sleeper", "Admin", active=False)
        self.target = make_user("target", "Author")

    def test_anonymous_is_rejected_with_401(self):
        for url in (reverse("users:user-list"), reverse("users:user-detail", args=[self.target.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)

    def test_editor_and_author_are_forbidden(self):
        for user in (self.editor, self.author):
            self.client.force_login(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(reverse("users:user-list")).status_code, 403)

    def test_inactive_admin_is_forbidden(self):
        self.client.force_login(self.inactive_admin)
        self.assertEqual(self.client.get(reverse("users:user-list")).status_code, 403)

    def test_admin_and_superuser_are_allowed(self):
        for user in (self.admin, self.superuser):
            self.client.force_login(user)
            with self.subTest(user=user.username):
                self.assertEqual(self.client.get(reverse("users:user-list")).status_code, 200)

    def test_wrong_method_returns_405(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.put(reverse("users:user-list"), data={}).status_code, 405)

    def test_csrf_is_enforced_for_unsafe_methods(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        response = client.post(
            reverse("users:user-list"),
            data={
                "username": "new",
                "email": "new@example.com",
                "password": PASSWORD,
                "role": "Author",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

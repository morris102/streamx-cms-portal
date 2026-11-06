from django.contrib.auth.models import Group, User
from django.test import TestCase

from users.permissions import ROLE_NAMES
from users.services import (
    ProtectedOperation,
    create_user,
    delete_user,
    update_user,
)

PASSWORD = "V3ry-Str0ng-Pass!42"
NEW_PASSWORD = "An0ther-Str0ng-Pass!7"


class ServiceTests(TestCase):
    def setUp(self):
        for name in ROLE_NAMES:
            Group.objects.get_or_create(name=name)
        self.admin = self._make("admin", "Admin")

    def _make(self, username, role, *, active=True, superuser=False):
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

    def _payload(self, username="new", role="Editor"):
        return {
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
            "role": role,
        }

    def test_create_hashes_password_and_assigns_one_role(self):
        user = create_user(self._payload())
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Editor"])

    def test_create_defaults_to_active(self):
        user = create_user(self._payload())
        self.assertTrue(user.is_active)

    def test_create_rejects_duplicate_email_case_insensitive(self):
        from users.serializers import ValidationError

        self._make("bob", "Author")
        with self.assertRaises(ValidationError):
            create_user(self._payload("alice") | {"email": "BOB@example.com"})

    def test_update_changes_password(self):
        user = self._make("editor", "Editor")
        update_user(user, {"password": NEW_PASSWORD}, self.admin)
        user.refresh_from_db()
        self.assertTrue(user.check_password(NEW_PASSWORD))

    def test_update_replaces_role(self):
        user = self._make("author", "Author")
        update_user(user, {"role": "Editor"}, self.admin)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Editor"])

    def test_update_omitted_role_is_unchanged(self):
        user = self._make("author", "Author")
        update_user(user, {"first_name": "Ann"}, self.admin)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), ["Author"])

    def test_superuser_is_read_only(self):
        root = self._make("root", None, superuser=True)
        with self.assertRaises(ProtectedOperation):
            update_user(root, {"first_name": "Root"}, self.admin)
        with self.assertRaises(ProtectedOperation):
            delete_user(root, self.admin)

    def test_admin_cannot_delete_self(self):
        with self.assertRaises(ProtectedOperation):
            delete_user(self.admin, self.admin)

    def test_admin_cannot_deactivate_self(self):
        with self.assertRaises(ProtectedOperation):
            update_user(self.admin, {"is_active": False}, self.admin)

    def test_last_admin_cannot_be_demoted(self):
        with self.assertRaises(ProtectedOperation):
            update_user(self.admin, {"role": "Editor"}, self.admin)

    def test_another_admin_allows_demotion(self):
        second = self._make("admin2", "Admin")
        updated = update_user(self.admin, {"role": "Editor"}, second)
        self.assertEqual(list(updated.groups.values_list("name", flat=True)), ["Editor"])

    def test_last_admin_cannot_be_deleted(self):
        superuser = self._make("root", None, superuser=True)
        # A superuser also counts as an active Admin, so use a lone group Admin
        # with the superuser temporarily inactive.
        superuser.is_active = False
        superuser.save()
        with self.assertRaises(ProtectedOperation):
            delete_user(self.admin, self.admin)

    def test_delete_removes_user(self):
        user = self._make("author", "Author")
        delete_user(user, self.admin)
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

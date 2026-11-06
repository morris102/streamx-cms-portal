from django.contrib.auth.models import Group, User
from django.test import TestCase

from users.permissions import ROLE_NAMES
from users.serializers import (
    ValidationError,
    parse_list_params,
    validate_create,
    validate_update,
)

PASSWORD = "V3ry-Str0ng-Pass!42"


class ValidationTests(TestCase):
    def setUp(self):
        for name in ROLE_NAMES:
            Group.objects.get_or_create(name=name)

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_create(
                {
                    "username": "alice",
                    "email": "alice@example.com",
                    "password": PASSWORD,
                    "role": "Author",
                    "is_superuser": True,
                }
            )
        self.assertIn("is_superuser", ctx.exception.errors)

    def test_missing_required_fields(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_create({})
        self.assertEqual(
            set(ctx.exception.errors),
            {"username", "email", "password", "role"},
        )

    def test_invalid_role(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_create(
                {
                    "username": "alice",
                    "email": "alice@example.com",
                    "password": PASSWORD,
                    "role": "Owner",
                }
            )
        self.assertIn("role", ctx.exception.errors)

    def test_invalid_email(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_create(
                {
                    "username": "alice",
                    "email": "not-an-email",
                    "password": PASSWORD,
                    "role": "Author",
                }
            )
        self.assertIn("email", ctx.exception.errors)

    def test_weak_password(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_create(
                {
                    "username": "alice",
                    "email": "alice@example.com",
                    "password": "short",
                    "role": "Author",
                }
            )
        self.assertIn("password", ctx.exception.errors)

    def test_duplicate_username_and_email(self):
        User.objects.create_user("alice", "alice@example.com", PASSWORD)
        with self.assertRaises(ValidationError) as ctx:
            validate_create(
                {
                    "username": "alice",
                    "email": "ALICE@example.com",
                    "password": PASSWORD,
                    "role": "Author",
                }
            )
        self.assertIn("username", ctx.exception.errors)
        self.assertIn("email", ctx.exception.errors)

    def test_update_excludes_self_from_duplicate_checks(self):
        alice = User.objects.create_user("alice", "alice@example.com", PASSWORD)
        cleaned = validate_update(
            {"username": "alice", "email": "ALICE@example.com"}, alice
        )
        self.assertEqual(cleaned["username"], "alice")

    def test_update_rejects_duplicate_of_other_user(self):
        User.objects.create_user("bob", "bob@example.com", PASSWORD)
        alice = User.objects.create_user("alice", "alice@example.com", PASSWORD)
        with self.assertRaises(ValidationError) as ctx:
            validate_update({"email": "BOB@example.com"}, alice)
        self.assertIn("email", ctx.exception.errors)

    def test_is_active_must_be_boolean(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_create(
                {
                    "username": "alice",
                    "email": "alice@example.com",
                    "password": PASSWORD,
                    "role": "Author",
                    "is_active": "false",
                }
            )
        self.assertIn("is_active", ctx.exception.errors)


class ListParamTests(TestCase):
    def test_defaults(self):
        params = parse_list_params({})
        self.assertEqual(params["page"], 1)
        self.assertEqual(params["page_size"], 20)
        self.assertIsNone(params["search"])
        self.assertIsNone(params["is_active"])

    def test_blank_search_is_ignored(self):
        self.assertIsNone(parse_list_params({"search": "   "})["search"])

    def test_active_filter_is_case_insensitive(self):
        self.assertIs(parse_list_params({"is_active": "TRUE"})["is_active"], True)
        self.assertIs(parse_list_params({"is_active": "False"})["is_active"], False)

    def test_invalid_active_filter(self):
        with self.assertRaises(ValidationError):
            parse_list_params({"is_active": "maybe"})

    def test_page_size_upper_bound(self):
        with self.assertRaises(ValidationError):
            parse_list_params({"page_size": "101"})

    def test_page_below_one(self):
        with self.assertRaises(ValidationError):
            parse_list_params({"page": "0"})

    def test_non_integer_page(self):
        with self.assertRaises(ValidationError):
            parse_list_params({"page": "two"})

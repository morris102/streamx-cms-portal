from django.test import SimpleTestCase
from django.urls import reverse


class UrlSmokeTests(SimpleTestCase):
    def test_user_list_url(self):
        self.assertEqual(reverse("users:user-list"), "/api/users/")

    def test_user_detail_url(self):
        self.assertEqual(reverse("users:user-detail", args=[1]), "/api/users/1/")

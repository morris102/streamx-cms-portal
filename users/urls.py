from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("", views.user_collection, name="user-list"),
    path("<int:user_id>/", views.user_detail, name="user-detail"),
]

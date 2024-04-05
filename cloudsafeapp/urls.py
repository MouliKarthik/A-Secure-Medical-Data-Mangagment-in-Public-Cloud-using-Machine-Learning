from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("dashboard/upload", views.upload_view, name="upload"),
    path("dashboard/fetch", views.fetch_view, name="fetch"),
    path(
        "dashboard/fetch/<str:file_id>",
        views.fetch_file_view,
        name="fetch_file",
    ),
    # Other URL patterns for your project...
]

handler404 = "cloudsafeapp.views.custom_404_view"

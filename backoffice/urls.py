from django.contrib.auth import views as auth_views
from django.urls import path

from backoffice import views

app_name = "backoffice"

urlpatterns = [
    path("", views.application_list, name="application-list"),
    path("applications/<int:pk>/", views.application_detail, name="application-detail"),
    path("export/", views.export_to_sheet, name="export"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="backoffice/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]

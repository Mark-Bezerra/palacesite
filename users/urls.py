from django.urls import path

from . import views

app_name = "users"
urlpatterns = [
    path("register/", views.sign_up, name="register"),
    path("login/", views.sign_in.as_view(), name="login"),
]

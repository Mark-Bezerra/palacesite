from django.urls import path
from . import views

app_name = "palace"
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('players/<str:player>/', views.PlayerView.as_view(), name='player'),
    path('profile/', views.SelfPlayerView, name='profile'),
    path("lobby/<str:lobby_name>/", views.LobbyView, name="lobby"),
    path("lobby0/", views.LobbyZed, name="lobby0"),
    path("lobbyplayers/<str:lobby_name>", views.LobbyPlayers, name="players")
]
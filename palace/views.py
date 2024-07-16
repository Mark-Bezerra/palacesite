from typing import Any
from django.shortcuts import render
from django.views import generic
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import HttpResponseRedirect

from .models import Player, Game


class IndexView(generic.TemplateView):
    template_name = "palace/index.html"

class GameIndexView(generic.TemplateView):
    template_name = "palace/game_index.html"

    def get_context_data(self, **kwargs):
        context = super(GameIndexView, self).get_context_data(**kwargs)
        context['lobbies'] = Game.objects.all()
        return context


@login_required
def SelfPlayerView(request):
    username = request.user.username
    return redirect("../players/" + username)


class PlayerView(generic.DetailView):
    slug_url_kwarg = "player"  # this the `argument` in the URL conf
    slug_field = "player"

    model = Player
    template_name = "palace/profile.html"

@login_required
def LobbyView(request, lobby_name):
    # User enters a lobby. If not in the database already, it is created
    lobby, created = Game.objects.get_or_create(lobby_name=lobby_name)

    # But maybe the user is already in a game... lets check
    # [Checking which specific user made this HTTP request
    # is possible because of the @login_required decorator above]
    if request.user.player.ingame != None and request.user.player.ingame != lobby:
        return HttpResponse("<h1>You're in a game already</h1>")

    elif request.user.player.ingame == None:
        request.user.player.ingame = lobby
        request.user.player.save()

    # Dynamically render an HTML page for them
    return render(
        request,
        "palace/lobby.html",
        {
            # "Context" dictionaries are passed so the page rendered
            # is a specific lobby
            "lobby_name": lobby.lobby_name,
            "players": lobby.players.order_by("player"),
        },
    )

def LobbyZed(request):
    return redirect("../lobby/0")

def LobbyPlayers(request, lobby_name):
    lobby = Game.objects.get(lobby_name=lobby_name)

    return render(
        request,
        "palace/lobbyplayers.html",
        {
            "lobby_name": lobby.lobby_name,
            "players": lobby.players.order_by("player"),
        },
    )

import json
import random

from channels.generic.websocket import AsyncWebsocketConsumer, SyncConsumer
import time
from asgiref.sync import async_to_sync
from channels.auth import login
from channels.db import database_sync_to_async
from django.conf import settings
from . import models
from channels.layers import get_channel_layer
import random
from time import sleep
from threading import Timer


# WebSocket 'consumers' consume front end WebSockets
# for the purpose of coding the backend response to
# connections being opened and messages being received
class LobbyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.lobby_name = self.scope["url_route"]["kwargs"]["lobby_name"]
        self.room_group_name = "palace_%s" % self.lobby_name
        self.scope["session"]["seed"] = random.randint(1, 1000)
        self.user = self.scope["user"]
        self.username = await self.get_username()

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Game worker reacts to new connection
        await self.channel_layer.send(
            "moderator",
            {
                "type": "connect",
                "username": self.username,
                "id": self.lobby_name,
                "player_channel": self.channel_name,
            },
        )

    # This runs when a websocket connection is disconnected
    # by page being closed or connectivity issue
    async def disconnect(self, close_code):
        await self.channel_layer.send(
            "moderator",
            {
                "type": "disconnect",
                "username": self.username,
                "player_channel": self.channel_name,
            },
        )

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Remove a game lobby from the game lobbies database
    # Which is used only for active games
    @database_sync_to_async
    def delete_lobby(self):
        models.Game.objects.get(lobby_name=self.lobby_name).delete()

    # Set a player's status to being out of any lobby
    @database_sync_to_async
    def remove_from_lobby(self):
        self.user.player.ingame = None
        self.user.player.save()

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        username = self.scope["user"].username

        if message[1:2] == ">":
            await self.channel_layer.send(
                "moderator",
                {
                    "type": "demand",
                    "demand": message[:1],
                    "message": message[2:],
                    "username": username,
                },
            )
        else:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "username": username,
                },
            )

    # Channel Layer function, [sends] by the "update" function
    async def refresh_lobby(self, event):
        player_list = await self.get_players()
        message = ", ".join(player_list)

        # Send player list to WebSocket in HTML element
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "game_event",
                "event": "users",
            },
        )

    # Make a string player_list by query to Game objects
    @database_sync_to_async
    def get_players(self):
        lobby = models.Game.objects.get(lobby_name=self.lobby_name)
        player_list = []

        # Players have a foreign key of a joined lobby
        for player in lobby.players.order_by("player"):
            player_list.append(player.player)

        return player_list

    @database_sync_to_async
    def get_username(self):
        return self.user.player.player

    # Make an integer player_count by query to Game objects
    @database_sync_to_async
    def get_player_count(self):
        lobby = models.Game.objects.get(lobby_name=self.lobby_name)
        self.user.player.save()
        player_count = 0

        # Players have a foreign key of a joined lobby
        for player in lobby.players.order_by("player"):
            player_count += 1

        return player_count

    # Below are 4 kinds of messages that can be sent to the client
    # First is the chat_message from other players
    # Then game_message, a broadcast from the game
    # Then game_event, which tells the client to run a function
    # Lastly game_event, which reveals something to one client

    async def chat_message(self, event):
        message = event["message"]
        username = event["username"]

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps(
                {"type": "chat", "message": message, "username": username}
            )
        )

    async def game_message(self, event):
        message = event["message"]
        theme = event["theme"]

        message.replace(
            self.scope["user"].username, f"{self.scope['user'].username}(you)"
        )

        await self.send(
            text_data=json.dumps(
                {"type": "broadcast", "message": message, "theme": theme}
            )
        )

    async def game_event(self, event):
        game_event = event["event"]

        if "message" in event:
            message = event["message"]
        else:
            message = ""

        if "theme" in event:
            theme = event["theme"]
        else:
            theme = ""

        if "player" in event:
            player = event["player"]
        else:
            player = ""

        if "role" in event:
            role = event["role"]
        else:
            role = ""

        message.replace(
            self.scope["user"].username, f"{self.scope['user'].username}(you)"
        )

        await self.send(
            text_data=json.dumps(
                {
                    "type": "event",
                    "event": game_event,
                    "message": message,
                    "theme": theme,
                    "player": player,
                    "role": role,
                }
            )
        )

    async def assigned_roles(self, event):
        profile = await self.get_username()
        player_channel = self.channel_name

        await self.channel_layer.send(
            "moderator",
            {"type": "init.game", "player": profile, "player_channel": player_channel},
        )


class Player:
    out = False
    connected = True
    spectator = False
    role = ""
    channel = ""
    votes = 0

    def __init__(self, channel):
        self.channel = channel


class Game:
    players = {}
    roles = ["King", "Guard", "Guard", "Guard", "Guard", "Beast"]
    lobby = True
    game_over = False
    capacity = 6
    player_count = 0
    votes = 0
    group = ""

    def __init__(self, lobby_name):
        self.group = "palace_%s" % lobby_name
        random.shuffle(self.roles)


# This 'worker' runs on a redis server and acts as an
# invisible spectator. Its purpose is to keep track of
# 'game-state', that is, what each player's role is,
# and the actions they are performing. If not for this,
# the players would not be able to keep secrets.
class GameConsumer(SyncConsumer):
    players = {}
    roles = ["King", "Guard", "Guard", "Guard", "Guard", "Beast"]
    lobby = True
    game_over = False
    capacity = 6
    player_count = 0
    votes = 0
    random.shuffle(roles)
    lobby_name = ""
    group = ""

    def connect(self, event):
        username = event["username"]
        print(username + " joined")

        # Game connection in lobby phase
        if self.lobby:
            if self.player_count == 0:
                self.lobby_name = event["id"]
                self.group = "palace_%s" % event["id"]

            self.players[username] = Player(event["player_channel"])

            self.group_message(
                {
                    "type": "refresh_lobby",
                },
            )
            self.player_count += 1

            if self.player_count == self.capacity:

                sleep(1)

                self.group_message(
                    {
                        "type": "game_event",
                        "event": "beginning",
                        "message": "Game beginning!",
                        "theme": "primary",
                    },
                )

                sleep(5)

                self.lobby = False

                self.group_message(
                    {
                        "type": "assigned_roles",
                    },
                )

        # Game connection of game in-progress
        else:
            if username in self.players:
                # a player has reconnected
                if not self.players[username].connected:
                    self.group_message(
                        {
                            "type": "game_event",
                            "event": "reconnected",
                            "player": username,
                        },
                    )
                    self.players[username].connected = True

            else:
                # a spectator has joined
                self.players[username] = Player(event["player_channel"])
                self.players[username].spectator = True


    def disconnect(self, event):
        username = event["username"]
        player_model = models.Player.objects.get(player=username)
        print(username + " left")

        # Game Disconnection
        if self.lobby:
            if username in self.players:
                del self.players[username]

            player_model.ingame = None
            player_model.save()

            self.player_count -= 1

            self.group_message(
                {
                    "type": "refresh_lobby",
                }
            )

        # Game Disconnection
        else:
            self.players[username].connected = False

            self.group_message(
                {
                    "type": "game_event",
                    "event": "disconnected",
                    "player": username,
                },
            )

            self.player_count -= 1

        if self.player_count == 0:
            self.message(
                {
                    "type": "delete_lobby",
                    "player_channel": event["player_channel"],
                },
            )
            models.Game.objects.get(lobby_name=self.lobby_name).delete()
            self.lobby = True
            self.roles = ["King", "Guard", "Guard", "Guard", "Guard", "Beast"]
            random.shuffle(self.roles)
            self.players = {}
            self.votes = 0
            self.game_over = False

    # The lobby has filled, the game begins.
    def init_game(self, event):
        character = event["player"]
        role = self.roles.pop()

        self.players[character].role = role

        self.message(
            {
                "type": "game_event",
                "player_channel": event["player_channel"],
                "event": "self",
                "player": f"{character}",
            },
        )

        self.message(
            {
                "type": "game_event",
                "player_channel": event["player_channel"],
                "event": "role",
                "player": f"{character}",
                "role": f"{role}",
            },
        )

        if not self.roles:
            self.tell_guards()

    #  Think of each player in the game running this function
    def tell_guards(self):
        king = ""

        for name, player in self.players.items():
            if player.role == "King":
                king = name

        # Their role is checked
        for player in self.players.values():
            if player.role == "Guard":
                self.message(
                    {
                        "type": "game_event",
                        "player_channel": player.channel,
                        "event": "role",
                        "player": f"{king}",
                        "role": "King",
                    },
                )
                self.message(
                    {
                        "type": "game_message",
                        "player_channel": player.channel,
                        "message": f"{king} is the King, guard him and keep this secret!",
                        "theme": "warning",
                    },
                )

        sleep(5)
        self.cycle()

    def demand(self, event):
        demand = event["demand"]
        msg = event["message"]
        username = event["username"]

        if demand == "c":
            self.vote(msg)
            return None
        elif demand == "v":
            self.voted(msg, username)
            return None
        elif demand == "j":
            self.jump(msg)
            return None

    def voted(self, player, voter):
        self.group_message(
            {
                "type": "game_message",
                "message": voter + " voted for " + player,
                "theme": "success",
            },
        )

    def vote(self, player):
        voted = player
        self.players[voted].votes += 1
        self.votes += 1
        print(voted + " has " + str(self.players[voted].votes) + " votes")

        # If everyone has voted:
        if self.votes == self.capacity:
            self.tally()
            self.votes = 0

    def jump(self, player):
        jumped = player
        role = self.players[jumped].role

        self.group_message(
            {
                "type": "game_message",
                "message": "The " + role + " " + jumped + " has been jumped on!",
                "theme": "dark",
            },
        )

        if role == "King":
            self.group_message(
                {
                    "type": "game_message",
                    "message": "The beast wins!",
                    "theme": "dark",
                },
            )
        else:
            self.group_message(
                {
                    "type": "game_message",
                    "message": "The palace team wins!",
                    "theme": "info",
                },
            )

        self.game_over = True

    def tally(self):
        votes = 0
        voted = ""

        if self.game_over:
            return None

        for i, name in enumerate(self.players):
            if self.players[name].votes > votes:
                votes = self.players[name].votes
                voted = name

        self.group_message(
            {
                "type": "game_message",
                "message": voted
                + " has been voted out!"
                + " He was "
                + self.players[voted].role,
                "theme": "danger",
            },
        )
        # add personal role
        self.group_message(
            {
                "type": "game_event",
                "update": "out",
                "player": voted,
            },
        )

        self.group_message(
            {
                "type": "game_message",
                "message": "New cycle beginning in 5 seconds",
                "theme": "light",
            },
        )

        sleep(5)

        self.cycle()

    def cycle(self):
        self.group_message(
            {
                "type": "game_event",
                "event": "new_cycle",
                "message": "Discuss and cast votes!",
                "theme": "light",
            },
        )

        Timer(
            50.0,
            self.group_message,
            [
                {
                    "type": "game_message",
                    "theme": "light",
                    "message": "Cycle finished! Counting votes.",
                },
            ],
        ).start()



    def message(self, event):
        async_to_sync(self.channel_layer.send)(
            event["player_channel"],
            event,
        )

    def group_message(self, event):
        async_to_sync(self.channel_layer.group_send)(self.group, event)

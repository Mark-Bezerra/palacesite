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

    # player removal from lobby in database
    @database_sync_to_async
    def remove_from_lobby(self):
        self.user.player.ingame = None
        self.user.player.save()

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        username = self.scope["user"].username

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "username": username,
            },
        )

    async def refresh_lobby(self, event):
        player_list = await self.get_players()
        message = ", ".join(player_list)

        # Send player list to WebSocket in HTML element
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "update",
                "update": "users",
                "message": message,
            },
        )

    # Make a string player_list by query to Lobby objects
    @database_sync_to_async
    def get_players(self):
        lobby = models.Lobby.objects.get(lobby_name=self.lobby_name)
        player_list = []

        # Players have a foreign key of a joined lobby
        for player in lobby.players.order_by("player"):
            player_list.append(player.player)

        return player_list

    @database_sync_to_async
    def get_username(self):
        return self.user.player.player

    # Make an integer player_count by query to Lobby objects
    @database_sync_to_async
    def get_player_count(self):
        lobby = models.Lobby.objects.get(lobby_name=self.lobby_name)
        self.user.player.save()
        player_count = 0

        # Players have a foreign key of a joined lobby
        for player in lobby.players.order_by("player"):
            player_count += 1

        return player_count

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]
        username = event["username"]

        # Send message to WebSocket
        await self.send(
            text_data=json.dumps({"message": message, "username": username})
        )

    async def update(self, event):
        message = event["message"]
        update = event["update"]

        message.replace(
            self.scope["user"].username, f"{self.scope['user'].username}(you)"
        )

        await self.send(text_data=json.dumps({"message": message, "update": update}))

    async def game_update(self, event):
        player = event["player"]
        role = event["role"]
        update = event["update"]

        await self.send(
            text_data=json.dumps({"role": role, "player": player, "update": update})
        )

    # Begin the game and get the game worker going...
    """ async def begin_game(self):
        lobby_name = self.lobby_name
        profile = await self.get_username()
        player_channel = self.channel_name

        count = await self.get_player_count()
        if count == 3:
            message = "Game beginning!"
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "username": "Room",
                },
            )

            await self.channel_layer.send(
                "moderator",
                {
                    "type": "game.begin",
                    "id": lobby_name,
                    "player": profile,
                    "player_channel": player_channel,
                },
            )"""

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

    def __init__(self, channel):
        self.channel = channel


class GameConsumer(SyncConsumer):
    players = {}
    roles = ["King", "Guard", "Beast"]
    lobby = True
    capacity = 3
    random.shuffle(roles)
    group = ""

    def connect(self, event):
        username = event["username"]

        # Lobby connection
        if self.lobby:
            if self.group == "":
                self.group = "palace_%s" % event["id"]

            self.players[username] = Player(event["player_channel"])

            self.group_message(
                {
                    "type": "refresh_lobby",
                },
            )
            self.capacity -= 1

            if self.capacity == 0:
                print("starting in 5")
                sleep(5)
                self.group_message(
                    {
                        "type": "chat_message",
                        "message": "Game beginning!",
                        "username": "Room",
                    },
                )

                self.lobby = False

                self.group_message(
                    {
                        "type": "assigned_roles",
                    },
                )

        # Game connection
        else:
            if username in self.players:
                # reconnect
                if not self.players[username].connected:
                    self.group_message(
                        {
                            "type": "game_update",
                            "update": "reconnected",
                            "player": username,
                        },
                    )
                    self.players[username].connected = True

            else:
                # spectator
                self.players[username] = Player(event["player_channel"])
                self.players[username].spectator = True

    def disconnect(self, event):
        username = event["username"]
        player_model = models.Player.objects.get(player=username)

        # Lobby Disconnection
        if self.lobby:
            if username in self.players:
                del self.players[username]

            player_model.ingame = None
            player_model.save()

            capacity += 1

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
                    "type": "game_update",
                    "update": "disconnect",
                    "player": username,
                },
            )

    def init_game(self, event):
        character = event["player"]
        role = self.roles.pop()

        self.players[character].role = role

        self.message(
            {
                "type": "chat_message",
                "player_channel": event["player_channel"],
                "message": f"Your role is {role}",
                "username": "Room",
            },
        )

        self.message(
            {
                "type": "game_update",
                "player_channel": event["player_channel"],
                "update": "role",
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
                        "type": "game_update",
                        "player_channel": player.channel,
                        "update": "role",
                        "player": f"{king}",
                        "role": "King",
                    },
                )
                self.message(
                    {
                        "type": "chat_message",
                        "player_channel": player.channel,
                        "message": f"{king} is the King, guard him and keep this secret!",
                        "username": "Room",
                    },
                )

    def message(self, event):
        async_to_sync(self.channel_layer.send)(
            event["player_channel"],
            event,
        )

    def group_message(self, event):
        async_to_sync(self.channel_layer.group_send)(self.group, event)

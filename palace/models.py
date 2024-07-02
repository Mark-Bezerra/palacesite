from django.db import models
from django.conf import settings

CHAT_ZONES = (
    ('game','GAME'),
    ('mafia','MAFIA'),
    ('private','PRIVATE'),
)

# The game model
class Game(models.Model):
    name = models.TextField()
    capacity = models.SmallIntegerField(default=6)

    # The name that will appear in the address bar
    lobby_name = models.SlugField(unique=True)

# The player model
class Player(models.Model):
    # Each player is connected to one of the 'user' Django authentication models
    user = models.OneToOneField(settings.AUTH_USER_MODEL,primary_key=True,related_name="player",on_delete=models.CASCADE,)

    # This field says which lobby the player is in
    ingame = models.ForeignKey(Game,on_delete=models.SET_NULL,related_name="players",default="",blank=True,null=True,)
    player = models.CharField(max_length=16, default="")
    wins = models.IntegerField()

    def __str__(self):
        return self.user.username

    def get_absolute_url(self):
        return self.user.username

class Game_Message(models.Model):
    game = models.ForeignKey(Game, on_delete=models.PROTECT, related_name="messages")

    sender = models.ForeignKey(Player, on_delete=models.PROTECT,related_name="sent")
    chat_zone = models.CharField(max_length=16, choices=CHAT_ZONES, default='data')
    private_recipient = models.ForeignKey(Player, on_delete=models.PROTECT, related_name="received", blank=True)
    is_vote = models.BooleanField(null=False)
    is_status = models.BooleanField(null=False)

    message = models.TextField(default="")
    timestamp = models.DateTimeField(auto_now_add=True)
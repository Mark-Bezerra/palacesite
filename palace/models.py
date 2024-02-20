from django.db import models
from django.conf import settings


# The lobby model
class Lobby(models.Model):
    name = models.TextField()
    capacity = models.SmallIntegerField(default=6)

    # The name that will appear in the address bar
    lobby_name = models.SlugField(unique=True)

# The player model
class Player(models.Model):
    # Each player is connected to one of the 'user' Django authentication models
    user = models.OneToOneField(settings.AUTH_USER_MODEL,primary_key=True,related_name="player",on_delete=models.CASCADE,)

    # This field says which lobby the player is in
    ingame = models.ForeignKey(Lobby,on_delete=models.SET_NULL,related_name="players",default="",blank=True,null=True,)
    player = models.CharField(max_length=16, default="")
    wins = models.IntegerField()

    def __str__(self):
        return self.user.username

    def get_absolute_url(self):
        return self.user.username

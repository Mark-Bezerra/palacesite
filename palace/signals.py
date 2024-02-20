from django.dispatch import receiver
from django.db.models.signals import post_save, post_init
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import User

from .models import Player

@receiver(post_save, sender=User)
def create_player(sender, instance, created, **kwargs):
    if created:
        Player.objects.create(user=instance, player=instance.username, wins=0)
        instance.player.save()
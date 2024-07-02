from django.contrib import admin

# Register your models here.
from .models import Player, Game

class PalaceAdmin(admin.ModelAdmin):
    pass

admin.site.register(Player, PalaceAdmin)
admin.site.register(Game, PalaceAdmin)
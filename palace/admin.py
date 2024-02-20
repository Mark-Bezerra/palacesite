from django.contrib import admin

# Register your models here.
from .models import Player, Lobby

class PalaceAdmin(admin.ModelAdmin):
    pass

admin.site.register(Player, PalaceAdmin)
admin.site.register(Lobby, PalaceAdmin)
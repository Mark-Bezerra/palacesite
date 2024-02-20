from django.apps import AppConfig

class PalaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'palace'

    def ready(self):
        from . import signals

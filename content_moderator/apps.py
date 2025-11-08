from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'content_moderator'
    def ready(self):
        import content_moderator.signals

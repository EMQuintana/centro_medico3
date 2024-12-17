from django.apps import AppConfig

class FichaMedicaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ficha_medica'

    def ready(self):
        from .scheduler import iniciar_scheduler
        iniciar_scheduler()

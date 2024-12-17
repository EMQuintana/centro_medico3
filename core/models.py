from django.db import models
from django.contrib.auth.models import User  # Importar el modelo de usuario predeterminado de Django

class UserActivity(models.Model):
    """
    Modelo para registrar las actividades realizadas por los usuarios.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    activity = models.TextField(verbose_name="Descripción de la actividad")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y hora")

    def __str__(self):
        return f"{self.user.username} realizó: {self.activity} en {self.timestamp}"

# Create your models here.


from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Reserva
from django.core.cache import cache

@receiver(post_save, sender=Reserva)
def notificar_reserva_creada_modificada(sender, instance, created, **kwargs):
    mensaje = ""
    if created:
        mensaje = f"Se ha creado una nueva reserva para {instance.paciente.nombre} el {instance.fecha_reserva.fecha_disponible}."
    else:
        mensaje = f"Se ha modificado la reserva de {instance.paciente.nombre}. La nueva fecha es {instance.fecha_reserva.fecha_disponible}."
    
    # Almacenar el mensaje en caché para que sea recuperado en el frontend
    cache.set(f"notificacion_reserva_{instance.id}", mensaje, timeout=60)

@receiver(post_delete, sender=Reserva)
def notificar_reserva_eliminada(sender, instance, **kwargs):
    mensaje = f"Se ha eliminado la reserva de {instance.paciente.nombre} para el {instance.fecha_reserva.fecha_disponible}."
    cache.set(f"notificacion_reserva_eliminada_{instance.id}", mensaje, timeout=60)

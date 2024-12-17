from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Reserva, Notificacion

@receiver(post_save, sender=Reserva)
def notificar_reserva_modificada(sender, instance, created, **kwargs):
    mensaje = ""
    if created:
        mensaje = f"Se ha creado una nueva reserva para {instance.paciente.nombre} la fehca del {instance.fecha_reserva.fecha_disponible}."
    else:
        mensaje = f"La reserva de {instance.paciente.nombre} ha sido modificada. La nueva fecha es {instance.fecha_reserva.fecha_disponible}."

    Notificacion.objects.create(
        usuario=instance.medico.user,
        mensaje=mensaje
    )

@receiver(post_delete, sender=Reserva)
def notificar_reserva_eliminada(sender, instance, **kwargs):
    mensaje = f"La reserva de {instance.paciente.nombre} programada para el {instance.fecha_reserva.fecha_disponible} ha sido eliminada."
    Notificacion.objects.create(
        usuario=instance.medico.user,
        mensaje=mensaje
    )

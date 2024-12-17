from .models import Reserva, Notificacion
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils.timezone import now, localtime
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

from django.db import IntegrityError

def enviar_notificaciones_programadas():
    hora_actual = localtime(now())  # Hora local
    logger.info(f"Ejecutando notificaciones. Hora actual: {hora_actual}")

    reservas = Reserva.objects.filter(
        fecha_reserva__fecha_disponible__range=[
            hora_actual - timedelta(minutes=1),
            hora_actual + timedelta(minutes=5)
        ]
    )
    logger.info(f"Total reservas encontradas: {reservas.count()}")

    for reserva in reservas:
        tiempo_restante = reserva.fecha_reserva.fecha_disponible - hora_actual
        logger.info(f"Tiempo restante para {reserva.paciente.nombre}: {tiempo_restante}")

        try:
            # Notificación 5 minutos antes
            if timedelta(minutes=4, seconds=55) < tiempo_restante <= timedelta(minutes=5):
                mensaje = f"La reserva para {reserva.paciente.nombre} comenzará en 5 minutos."
                _, created = Notificacion.objects.get_or_create(
                    usuario=reserva.medico.user,
                    mensaje=mensaje
                )
                if created:
                    logger.info(f"Notificación creada (5 minutos antes): {mensaje}")

            # Notificación en la hora exacta
            if timedelta(minutes=-1) <= tiempo_restante <= timedelta(minutes=1):
                mensaje = f"La reserva para {reserva.paciente.nombre} está programada ahora."
                _, created = Notificacion.objects.get_or_create(
                    usuario=reserva.medico.user,
                    mensaje=mensaje
                )
                if created:
                    logger.info(f"Notificación creada (hora exacta): {mensaje}")

        except IntegrityError as e:
            logger.error(f"Error al crear notificación: {e}")


def iniciar_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(enviar_notificaciones_programadas, 'interval', seconds=10)
  # Corre cada 30 segundos
    scheduler.start()
    logger.info("Scheduler iniciado para enviar notificaciones programadas.")

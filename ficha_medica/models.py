from django.db import models
from django.contrib.auth.models import User, Group
from datetime import date
from django.utils.timezone import localtime, now
from django.core.validators import RegexValidator

class Paciente(models.Model):
    rut = models.CharField(max_length=12, unique=True)  # Ejemplo: 12345678-9
    nombre = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(blank=True, null=True)  # Campo adicional
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\d+$',
                message="El teléfono solo debe contener números.",
                code='invalid_telefono'
            )
        ]
    )
    email = models.EmailField(blank=True, null=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    def __str__(self):
        return f"{self.nombre} ({self.rut})"

    @property
    def edad(self):
        """Calcula la edad del paciente basado en la fecha de nacimiento."""
        if self.fecha_nacimiento:
            today = date.today()
            return today.year - self.fecha_nacimiento.year - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))
        return None

class Especialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)  # Nombre único para la especialidad
    descripcion = models.TextField(blank=True, null=True)  # Descripción opcional

    class Meta:
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"

    def __str__(self):
        return self.nombre


class Medico(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(Especialidad, on_delete=models.CASCADE, related_name="medicos")  # Relación con Especialidad
    telefono = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\d+$',
                message="El teléfono solo debe contener números.",
                code='invalid_telefono'
            )
        ]
    )

    class Meta:
        verbose_name = "Medico"
        verbose_name_plural = "Medicos"

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.especialidad.nombre}"

    def save(self, *args, **kwargs):
        # Crear o asignar grupo 'Medico' al usuario
        grupo, created = Group.objects.get_or_create(name='Medico')
        self.user.groups.add(grupo)
        super().save(*args, **kwargs)

class FichaMedica(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='fichas')
    medico = models.ForeignKey(Medico, on_delete=models.SET_NULL, null=True, related_name='fichas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    diagnostico = models.TextField()
    tratamiento = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Ficha"
        verbose_name_plural = "Fichas"

    def __str__(self):
        if self.medico:
            return f"Ficha de {self.paciente.nombre} - Médico: {self.medico.user.first_name} {self.medico.user.last_name} ({self.fecha_creacion.strftime('%d/%m/%Y')})"
        else:
            return f"Ficha de {self.paciente.nombre} - Médico: No asignado ({self.fecha_creacion.strftime('%d/%m/%Y')})"

class Recepcionista(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\d+$',
                message="El teléfono solo debe contener números.",
                code='invalid_telefono'
            )
        ]
    )
    direccion = models.TextField(blank=True, null=True)
    fecha_contratacion = models.DateField(blank=True, null=True)

    class Meta:
        verbose_name = "Recepcionista"
        verbose_name_plural = "Recepcionistas"

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - Recepcionista"

    def save(self, *args, **kwargs):
        # Crear o asignar grupo 'Recepcionista' al usuario
        grupo, created = Group.objects.get_or_create(name='Recepcionista')
        self.user.groups.add(grupo)
        super().save(*args, **kwargs)

class Disponibilidad(models.Model):
    medico = models.ForeignKey('Medico', on_delete=models.CASCADE)
    fecha_disponible = models.DateTimeField()
    ocupada = models.BooleanField(default=False)

    def fecha_local(self):
        return localtime(self.fecha_disponible)  # Convierte a la zona horaria local
    
    class Meta:
        verbose_name = "Disponibilidad"
        verbose_name_plural = "Disponibilidades"

    def __str__(self):
        return f"{self.medico} - {self.fecha_disponible}"




class Reserva(models.Model):
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    especialidad = models.ForeignKey(Especialidad, on_delete=models.CASCADE)
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE)
    fecha_reserva = models.ForeignKey(Disponibilidad, on_delete=models.CASCADE)
    motivo = models.TextField()
    recepcionista = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # Agregar este campo

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"

    def __str__(self):
        return f"Reserva de {self.paciente.nombre} gestionada por {self.recepcionista.first_name if self.recepcionista else 'N/A'} para el médico {self.medico.user.first_name}"

class Notificacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    mensaje = models.TextField()
    fecha_creacion = models.DateTimeField(default=now)
    leido = models.BooleanField(default=False)

    def __str__(self):
        return f"Notificación para {self.usuario.username} - {self.mensaje}"



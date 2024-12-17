from django.contrib import admin
from .models import Paciente, Medico, FichaMedica, Recepcionista, Reserva, Especialidad, Disponibilidad

# Configuración para Especialidad
@admin.register(Especialidad)
class EspecialidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')  # Campos visibles
    search_fields = ('nombre',)  # Campo para la barra de búsqueda
    ordering = ('nombre',)  # Orden alfabético por nombre

# Configuración para Paciente
@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre', 'telefono', 'email')  # Campos visibles en la lista
    search_fields = ('rut', 'nombre', 'telefono', 'email')  # Campos para la barra de búsqueda
    list_filter = ('direccion',)  # Filtro por dirección
    ordering = ('nombre',)  # Orden por nombre

# Configuración para Médico
@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'especialidad', 'telefono', 'get_rut')  # Mostrar nombre completo y RUT
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'especialidad__nombre')  # Campos para búsqueda
    list_filter = ('especialidad',)  # Filtro por especialidad
    ordering = ('user__last_name',)  # Orden por apellido

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_full_name.short_description = "Nombre Completo"

    def get_rut(self, obj):
        return obj.user.username
    get_rut.short_description = "RUT"

# Configuración para Ficha Médica
@admin.register(FichaMedica)
class FichaMedicaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'fecha_creacion', 'diagnostico')  # Campos visibles
    search_fields = ('paciente__rut', 'paciente__nombre', 'medico__user__username', 'diagnostico')  # Campos de búsqueda
    list_filter = ('fecha_creacion', 'medico')  # Filtros por fecha de creación y médico
    date_hierarchy = 'fecha_creacion'  # Barra de navegación por fecha
    ordering = ('-fecha_creacion',)  # Orden descendente por fecha de creación

# Configuración para Recepcionista
@admin.register(Recepcionista)
class RecepcionistaAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'telefono', 'direccion', 'fecha_contratacion', 'get_rut')  # Mostrar nombre completo y RUT
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'telefono')  # Campos de búsqueda
    list_filter = ('fecha_contratacion',)  # Filtro por fecha de contratación
    ordering = ('user__last_name',)  # Orden por apellido

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_full_name.short_description = "Nombre Completo"

    def get_rut(self, obj):
        return obj.user.username
    get_rut.short_description = "RUT"

# Configuración para Reserva
@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'medico', 'fecha_reserva', 'motivo')  # Campos visibles
    search_fields = ('paciente__nombre', 'paciente__rut', 'medico__user__username', 'motivo')  # Campos de búsqueda
    list_filter = ('fecha_reserva__fecha_disponible', 'medico')  # Filtros por fecha y médico
    ordering = ('-fecha_reserva__fecha_disponible',)  # Orden descendente por fecha de disponibilidad

    def get_fecha_reserva(self, obj):
        return obj.fecha_reserva.fecha_disponible
    get_fecha_reserva.admin_order_field = 'fecha_reserva__fecha_disponible'
    get_fecha_reserva.short_description = 'Fecha de Reserva'

@admin.register(Disponibilidad)
class DisponibilidadAdmin(admin.ModelAdmin):
    list_display = ('medico', 'fecha_disponible')  # Mostrar campos relevantes en la tabla
    list_filter = ('medico', 'fecha_disponible')  # Agregar filtros
    search_fields = ('medico__user__first_name', 'medico__user__last_name')

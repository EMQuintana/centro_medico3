from django.contrib import admin
from django.urls import path
from ficha_medica import views as ficha_medica_views
from django.contrib.auth import views as auth_views
 
urlpatterns = [
    # Página principal (Inicio de sesión y redirección por rol)
    path('', ficha_medica_views.home, name='home'),
    path('admin/medicos/', ficha_medica_views.listar_medicos, name='listar_medicos'),
    path('admin/medicos/modificar/<int:medico_id>/', ficha_medica_views.modificar_medico, name='modificar_medico'),
    path('admin/medicos/eliminar/<int:medico_id>/', ficha_medica_views.eliminar_medico, name='eliminar_medico'),

    # Recepcionistas
    path('admin/recepcionistas/', ficha_medica_views.listar_recepcionistas, name='listar_recepcionistas'),
    path('admin/recepcionistas/modificar/<int:recepcionista_id>/', ficha_medica_views.modificar_recepcionista, name='modificar_recepcionista'),
    path('admin/recepcionistas/eliminar/<int:recepcionista_id>/', ficha_medica_views.eliminar_recepcionista, name='eliminar_recepcionista'),

    # Recepcionista
    path('recepcionista/', ficha_medica_views.recepcionista_dashboard, name='recepcionista_dashboard'),
    path('recepcionista/pacientes/', ficha_medica_views.listar_pacientes, name='listar_pacientes'),
    path('recepcionista/reservas/', ficha_medica_views.listar_reservas, name='listar_reservas'),
    path('reserva/crear/', ficha_medica_views.crear_reserva, name='crear_reserva'),
    path('crear-paciente/', ficha_medica_views.crear_paciente, name='crear_paciente'),
    path('pacientes/', ficha_medica_views.listar_pacientes, name='listar_pacientes'),
    path('pacientes/modificar/<int:paciente_id>/', ficha_medica_views.modificar_paciente, name='modificar_paciente'),
    path('pacientes/eliminar/<int:paciente_id>/', ficha_medica_views.eliminar_paciente, name='eliminar_paciente'),
    path('reservas/modificar/<int:reserva_id>/', ficha_medica_views.modificar_reserva, name='modificar_reserva'),
    path('reservas/eliminar/<int:reserva_id>/', ficha_medica_views.eliminar_reserva, name='eliminar_reserva'),

    # Médico
    path('medico/', ficha_medica_views.medico_dashboard, name='medico_dashboard'),
    path('medico/fichas/filtrar/<str:paciente_rut>/', ficha_medica_views.filtrar_fichas_por_paciente, name='filtrar_fichas_por_paciente'),
    path('fichas/', ficha_medica_views.listar_fichas, name='listar_fichas_medicas'),
    path('fichas/crear/<int:reserva_id>/', ficha_medica_views.crear_ficha_medica, name='crear_ficha'),
    path('fichas/modificar/<int:ficha_id>/', ficha_medica_views.modificar_ficha, name='modificar_ficha'),
    path('fichas/eliminar/<int:ficha_id>/', ficha_medica_views.eliminar_ficha, name='eliminar_ficha'),
    path('disponibilidades/', ficha_medica_views.gestionar_disponibilidades, name='gestionar_disponibilidades'),
    path('disponibilidades/eliminar/<int:disponibilidad_id>/', ficha_medica_views.eliminar_disponibilidad, name='eliminar_disponibilidad'),
    path('marcar-notificacion-leida/<int:notificacion_id>/', ficha_medica_views.marcar_notificacion_leida, name='marcar_notificacion_leida'),
    path('notificaciones/ajax/', ficha_medica_views.obtener_notificaciones, name='obtener_notificaciones'),
    path('reservas/activas/', ficha_medica_views.obtener_reservas_activas, name='obtener_reservas_activas'),
    path('modificar-disponibilidad/', ficha_medica_views.modificar_disponibilidad, name='modificar_disponibilidad'),
    path('ficha/<int:ficha_id>/pdf/', ficha_medica_views.generar_ficha_pdf, name='generar_ficha_pdf'),

    # APIs
    path('api/medicos/', ficha_medica_views.api_medicos, name='api_medicos'),
    path('api/disponibilidades/', ficha_medica_views.api_disponibilidades, name='api_disponibilidades'),
    path('api/validar_rut/', ficha_medica_views.api_validar_rut, name='api_validar_rut'),

    # Panel de administración
    path('admin/', admin.site.urls),
    path('admin-dashboard/', ficha_medica_views.admin_dashboard, name='admin_dashboard'),

    # Gestión de usuarios
    path('medico/crear/', ficha_medica_views.crear_medico, name='crear_medico'),
    path('recepcionista/crear/', ficha_medica_views.crear_recepcionista, name='crear_recepcionista'),

    # Cierre de sesión
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]

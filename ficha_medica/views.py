
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import JsonResponse
from django.core.serializers.json import DjangoJSONEncoder
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import HttpResponse

from ficha_medica.utils import role_required
from ficha_medica.forms import (
    FichaMedicaForm, DisponibilidadForm, ReservaForm,
    PacienteForm, MedicoForm, RecepcionistaForm
)
from .models import (
    FichaMedica, Paciente, Reserva, Disponibilidad,
    Medico, Especialidad, Recepcionista, Notificacion
)

from django.utils.timezone import make_aware, localtime, now
from datetime import datetime, timedelta, date
from django.contrib.auth.models import Group, User
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import json
import logging

# Configuración de logging
logger = logging.getLogger(__name__)





def admin_or_superuser_required(view_func):
    """
    Decorador que permite acceso solo a administradores o superusuarios.
    """
    return user_passes_test(lambda u: u.is_active and (u.is_staff or u.is_superuser))(view_func)


def generar_ficha_pdf(request, ficha_id):
    # Obtener la ficha médica específica
    ficha = FichaMedica.objects.get(id=ficha_id)

    # Configurar la respuesta HTTP para PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ficha_medica_{ficha_id}.pdf"'

    # Crear el objeto canvas para generar el PDF
    p = canvas.Canvas(response, pagesize=A4)

    # Añadir contenido al PDF
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "Ficha Médica")

    p.setFont("Helvetica", 12)
    p.drawString(100, 750, f"Paciente: {ficha.paciente.nombre}")
    p.drawString(100, 730, f"RUT: {ficha.paciente.rut}")
    p.drawString(100, 710, f"Edad: {ficha.paciente.edad if ficha.paciente.edad else 'No registrada'}")
    p.drawString(100, 690, f"Diagnóstico: {ficha.diagnostico}")
    p.drawString(100, 670, f"Tratamiento: {ficha.tratamiento}")
    p.drawString(100, 650, f"Observaciones: {ficha.observaciones if ficha.observaciones else 'Ninguna'}")
    p.drawString(100, 630, f"Fecha de Creación: {ficha.fecha_creacion.strftime('%d/%m/%Y')}")

    p.setFont("Helvetica-Oblique", 10)  # Fuente corregida
    p.drawString(100, 600, "Este documento fue generado automáticamente.")

    # Finalizar y cerrar el PDF
    p.showPage()
    p.save()

    return response

@login_required
@admin_or_superuser_required
def crear_recepcionista(request):
    if request.method == 'POST':
        form = RecepcionistaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "El recepcionista ha sido creado exitosamente.")
            return redirect('admin_dashboard')  # Cambia esta redirección según corresponda
        else:
            messages.error(request, "Hubo un error al crear el recepcionista.")
    else:
        form = RecepcionistaForm()

    return render(request, 'recepcionistas/crear_recepcionista.html', {'form': form})

@login_required
def admin_dashboard(request):
    """
    Vista del panel de administración personalizada.
    Accesible solo para usuarios con permisos de administrador.
    """
    if not request.user.is_superuser and not request.user.groups.filter(name='Administrador').exists():
        return HttpResponseForbidden("No tienes permiso para acceder a esta página.")
    
    # Calcular estadísticas rápidas
    total_medicos = Medico.objects.count()
    total_recepcionistas = Recepcionista.objects.count()
    total_pacientes = Paciente.objects.count()
    total_reservas = Reserva.objects.count()

    return render(request, 'core/admin_dashboard.html', {
        'total_medicos': total_medicos,
        'total_recepcionistas': total_recepcionistas,
        'total_pacientes': total_pacientes,
        'total_reservas': total_reservas,
    })

@login_required
@admin_or_superuser_required
def listar_medicos(request):
    medicos = Medico.objects.select_related('user', 'especialidad').all()
    return render(request, 'core/listar_medicos.html', {'medicos': medicos})

@login_required
@admin_or_superuser_required
def modificar_medico(request, medico_id):
    medico = get_object_or_404(Medico, id=medico_id)

    if request.method == 'POST':
        form = MedicoForm(request.POST, instance=medico)
        if form.is_valid():
            medico = form.save(commit=False)
            medico.user.first_name = form.cleaned_data['first_name']
            medico.user.last_name = form.cleaned_data['last_name']
            medico.user.username = form.cleaned_data['username']
            medico.user.save()
            medico.save()
            messages.success(request, "Los cambios del médico se han guardado exitosamente.")
            return redirect('listar_medico')
        else:
            messages.error(request, "Hubo errores en el formulario. Revisa los campos.")
    else:
        form = MedicoForm(instance=medico)
        form.fields['first_name'].initial = medico.user.first_name
        form.fields['last_name'].initial = medico.user.last_name
        form.fields['username'].initial = medico.user.username

    return render(request, 'core/modificar_medico.html', {'form': form, 'medico': medico})




@login_required
@admin_or_superuser_required
def eliminar_medico(request, medico_id):
    medico = get_object_or_404(Medico, id=medico_id)
    medico.user.delete()  # Eliminar también el usuario asociado
    medico.delete()
    messages.success(request, "Médico eliminado exitosamente.")
    return redirect('listar_medicos')

@login_required
@admin_or_superuser_required
def listar_recepcionistas(request):
    recepcionistas = Recepcionista.objects.select_related('user').all()
    return render(request, 'core/listar_recepcionistas.html', {'recepcionistas': recepcionistas})

@login_required
@admin_or_superuser_required
def modificar_recepcionista(request, recepcionista_id):
    recepcionista = get_object_or_404(Recepcionista, id=recepcionista_id)
    if request.method == 'POST':
        # Actualizar los datos del recepcionista
        recepcionista.user.first_name = request.POST.get('first_name')
        recepcionista.user.last_name = request.POST.get('last_name')
        recepcionista.user.username = request.POST.get('username')
        recepcionista.telefono = request.POST.get('telefono')
        recepcionista.direccion = request.POST.get('direccion')
        recepcionista.user.save()
        recepcionista.save()

        # Mensaje de éxito
        messages.success(request, "Los cambios del recepcionista han sido guardados exitosamente.")
        return redirect('listar_recepcionistas')  # Redirige al dashboard
    return render(request, 'core/modificar_recepcionista.html', {'recepcionista': recepcionista})


@login_required
@admin_or_superuser_required
def eliminar_recepcionista(request, recepcionista_id):
    recepcionista = get_object_or_404(Recepcionista, id=recepcionista_id)
    recepcionista.user.delete()  # Eliminar también el usuario asociado
    recepcionista.delete()
    messages.success(request, "Recepcionista eliminado exitosamente.")
    return redirect('listar_recepcionistas')



def home(request):
    """
    Página de inicio que maneja el inicio de sesión y redirección según roles.
    """
    if request.user.is_authenticated:
        if request.user.groups.filter(name='Recepcionista').exists():
            return redirect('recepcionista_dashboard')
        elif request.user.groups.filter(name='Medico').exists():
            return redirect('medico_dashboard')
        elif request.user.is_superuser:
            return redirect('admin_dashboard')
        else:
            return render(request, 'core/home.html', {'error': 'No tiene un grupo asignado.'})

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('/')
        else:
            messages.error(request, "Credenciales inválidas.")

    return render(request, 'core/home.html')





@login_required
@role_required('Medico')
def listar_fichas(request):
    fichas = FichaMedica.objects.all()
    rut_query = request.GET.get('rut', '').strip()
    fecha_query = request.GET.get('fecha', '').strip()

    # Filtrar por RUT
    if rut_query:
        fichas = fichas.filter(paciente__rut__icontains=rut_query)

    # Filtrar por Fecha
    if fecha_query:
        fichas = fichas.filter(fecha_creacion__date=fecha_query)

    # Paginación
    paginator = Paginator(fichas, 10)  # 10 fichas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'fichas_medicas/gestionar_fichas.html', {
        'fichas': page_obj,
    })

@login_required
@role_required('Medico')
def modificar_ficha(request, ficha_id):
    ficha = get_object_or_404(FichaMedica, id=ficha_id)

    if request.method == 'POST':
        form = FichaMedicaForm(request.POST, instance=ficha)
        if form.is_valid():
            form.save()
            # Agregar mensaje de éxito
            messages.success(request, "La ficha médica ha sido modificada exitosamente.")
            return redirect('listar_fichas_medicas')
        else:
            # Agregar mensaje de error si hay problemas en el formulario
            messages.error(request, "Hubo errores en el formulario. Por favor, revisa los campos.")
    else:
        form = FichaMedicaForm(instance=ficha)

    return render(request, 'fichas_medicas/modificar_ficha.html', {'form': form, 'ficha': ficha})


@login_required
@role_required('Medico')
def eliminar_ficha(request, ficha_id):
    ficha = get_object_or_404(FichaMedica, id=ficha_id)

    if request.method == 'POST':
        ficha.delete()
        messages.success(request, "Ficha médica eliminada exitosamente.")
        return redirect('listar_fichas_medicas')  # Asegúrate de que 'listar_fichas' existe
    return render(request, 'fichas_medicas/listar_fichas.html', {'ficha': ficha})

@login_required
@role_required('Medico')
def filtrar_fichas_por_paciente(request, paciente_rut):
    """
    Filtrar fichas médicas de un paciente por su RUT.
    """
    fichas = FichaMedica.objects.filter(paciente__rut=paciente_rut)
    
    return render(request, 'fichas_medicas/filtrar_fichas.html', {
        'fichas': fichas,
        'paciente_rut': paciente_rut,
    })

@login_required
@role_required('Medico')
def medico_dashboard(request):
    medico = request.user.medico
    hora_actual = localtime(now())  # Hora actual en la zona local

    # Filtrar reservas de hoy y futuras
    reservas_hoy = Reserva.objects.filter(
        medico=medico,
        fecha_reserva__fecha_disponible__date=hora_actual.date(),
        fecha_reserva__fecha_disponible__gte=hora_actual - timedelta(minutes=5)  # Mostrar horas pasadas recientes
    ).order_by('fecha_reserva__fecha_disponible')

    logger.info(f"Reservas para hoy: {reservas_hoy.count()}")

    notificaciones = Notificacion.objects.filter(usuario=request.user, leido=False).order_by('-fecha_creacion')

    return render(request, 'core/medico.html', {
        'reservas_hoy': reservas_hoy,
        'notificaciones': notificaciones,
    })


@login_required
def marcar_notificacion_leida(request, notificacion_id):
    if request.method == 'POST':
        try:
            notificacion = Notificacion.objects.get(id=notificacion_id, usuario=request.user)
            notificacion.leido = True
            notificacion.save()
            return JsonResponse({"success": True, "message": "Notificación marcada como leída."})
        except Notificacion.DoesNotExist:
            return JsonResponse({"success": False, "message": "Notificación no encontrada."}, status=404)
    return JsonResponse({"success": False, "message": "Método no permitido."}, status=405)




@login_required
@role_required('Medico')
def obtener_notificaciones(request):
    # Debug: imprimir el usuario actual
    print(f"Usuario actual: {request.user}")

    # Filtra notificaciones no leídas para el usuario actual
    notificaciones = Notificacion.objects.filter(leido=False, usuario=request.user)

    # Debug: Imprimir las notificaciones
    print("Notificaciones encontradas:")
    for n in notificaciones:
        print(f"ID: {n.id}, Mensaje: {n.mensaje}, Fecha: {n.fecha_creacion}")

    # Devuelve las notificaciones en JSON
    data = [{"id": n.id, "mensaje": n.mensaje, "fecha_creacion": n.fecha_creacion} for n in notificaciones]
    return JsonResponse(data, safe=False)

def modificar_disponibilidad(request):
    if request.method == "POST":
        id = request.POST.get('disponibilidad_id')
        fecha = request.POST.get('fecha')
        hora = request.POST.get('hora')
        disponibilidad = Disponibilidad.objects.get(id=id)
        disponibilidad.fecha_disponible = f"{fecha} {hora}"
        disponibilidad.save()
        return redirect('gestionar_disponibilidades')


# Filtrar fichas médicas por paciente
@login_required
@role_required('Medico')
def filtrar_fichas_medicas(request):
    rut_query = request.GET.get('rut', '')  # Obtener el parámetro 'rut' de la URL
    fichas = FichaMedica.objects.all()

    if rut_query:
        fichas = fichas.filter(paciente__rut__icontains=rut_query)

    paginator = Paginator(fichas, 5)  # Paginación con 5 elementos por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'fichas_medicas/filtrar_fichas.html', {
        'fichas': page_obj,
        'rut_query': rut_query,  # Pasamos el RUT para mantener el filtro
    })


@login_required
@role_required('Medico')
def crear_ficha_medica(request, reserva_id):
    """
    Crear una nueva ficha médica asociada a una reserva, paciente y médico.
    """
    reserva = get_object_or_404(Reserva, id=reserva_id)

    # Asegurarse de que el médico actual está relacionado con la reserva
    if request.user.medico != reserva.medico:
        messages.error(request, "No tienes permiso para crear una ficha para esta reserva.")
        return redirect('medico_dashboard')

    if request.method == 'POST':
        form = FichaMedicaForm(request.POST)
        if form.is_valid():
            ficha = form.save(commit=False)
            ficha.paciente = reserva.paciente
            ficha.medico = request.user.medico
            ficha.reserva = reserva  # Asignar la reserva al formulario
            ficha.save()
            messages.success(request, "Ficha médica creada con éxito.")
            return redirect('medico_dashboard')
        else:
            messages.error(request, "Por favor corrige los errores en el formulario.")
    else:
        form = FichaMedicaForm()

    # Datos del paciente
    paciente = reserva.paciente
    hoy = date.today()

    # Calcular la edad solo si fecha_nacimiento está definida
    if paciente.fecha_nacimiento:
        edad = hoy.year - paciente.fecha_nacimiento.year - ((hoy.month, hoy.day) < (paciente.fecha_nacimiento.month, paciente.fecha_nacimiento.day))
    else:
        edad = "No registrada"

    # Datos del médico
    medico = request.user.medico
    especialidad = medico.especialidad.nombre if medico.especialidad else "No especificada"
    rut_medico = medico.user.username

    return render(request, 'fichas_medicas/crear_ficha_medica.html', {
        'form': form,
        'reserva': reserva,
        'paciente': paciente,
        'edad': edad,
        'medico_nombre': f"{medico.user.first_name} {medico.user.last_name}",
        'especialidad': especialidad,
        'rut_medico': rut_medico,
    })

@login_required
@role_required('Medico')
def gestionar_disponibilidades(request):
    medico = request.user.medico
    disponibilidades = Disponibilidad.objects.filter(medico=medico)

    if request.method == 'POST':
        form = DisponibilidadForm(request.POST)
        if form.is_valid():
            disponibilidad = form.save(commit=False)
            disponibilidad.medico = medico  # Asigna el médico al objeto
            disponibilidad.save()
            return redirect('gestionar_disponibilidades')  # Redirige después de guardar
        else:
            print(form.errors)  # Depura errores del formulario
    else:
        form = DisponibilidadForm()

    return render(request, 'fichas_medicas/gestionar_disponibilidades.html', {
        'form': form,
        'disponibilidades': disponibilidades,
    })


def obtener_reservas_activas(request):
    hora_actual = localtime(now())
    reservas = Reserva.objects.filter(fecha_reserva__fecha_disponible__gte=hora_actual)
    data = [
        {"id": r.id, "paciente": r.paciente.nombre, "hora": r.fecha_reserva.fecha_disponible.strftime('%H:%M')}
        for r in reservas
    ]
    return JsonResponse(data, safe=False)


@login_required
@admin_or_superuser_required
def crear_medico(request):
    if request.method == 'POST':
        form = MedicoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Médico registrado con éxito.")
            return redirect('listar_medicos')
    else:
        form = MedicoForm()

    return render(request, 'core/crear_medico.html', {'form': form})


@login_required
@admin_or_superuser_required
def crear_recepcionista(request):
    if request.method == 'POST':
        form = RecepcionistaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')  # Redirige al panel de administración personalizado
    else:
        form = RecepcionistaForm()
    return render(request, 'core/crear_recepcionista.html', {'form': form})

@login_required
@role_required('Medico')
def eliminar_disponibilidad(request, disponibilidad_id):
    disponibilidad = get_object_or_404(Disponibilidad, id=disponibilidad_id)
    if disponibilidad.medico == request.user.medico:
        disponibilidad.delete()
    return redirect('gestionar_disponibilidades')


@login_required
@role_required('Recepcionista')
def recepcionista_dashboard(request):
    """
    Dashboard para recepcionistas.
    """
    return render(request, 'core/recepcionista.html') 

@login_required
@role_required('Recepcionista')
def listar_pacientes(request):
    rut_query = request.GET.get('rut', '')
    pacientes = Paciente.objects.filter(rut__icontains=rut_query).order_by('nombre') if rut_query else Paciente.objects.all().order_by('nombre')
    paginator = Paginator(pacientes, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, 'pacientes/listar_pacientes.html', {'pacientes': page_obj, 'rut_query': rut_query})

# Listar pacientes
@login_required
@role_required('Recepcionista')
def listar_pacientes(request):
    rut_query = request.GET.get('rut', '')
    pacientes = Paciente.objects.filter(rut__icontains=rut_query).order_by('nombre') if rut_query else Paciente.objects.all().order_by('nombre')
    paginator = Paginator(pacientes, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, 'pacientes/listar_pacientes.html', {'pacientes': page_obj, 'rut_query': rut_query})

@login_required
@role_required('Recepcionista')
def recepcionista_dashboard(request):
    """
    Dashboard para recepcionistas.
    """
    # Verifica que el usuario tenga el grupo correcto
    if not request.user.groups.filter(name='Recepcionista').exists():
        return HttpResponseForbidden("No tienes permiso para acceder a esta página.")

    return render(request, 'core/recepcionista.html')  # Cambia la ruta si está en otro directorio


# Listar reservas
@login_required
@role_required('Recepcionista')
def listar_reservas(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    reservas = Reserva.objects.all().order_by('-fecha_reserva')

    if fecha_inicio and fecha_fin:
        try:
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            reservas = reservas.filter(fecha_reserva__fecha_disponible__range=[fecha_inicio_dt, fecha_fin_dt])
        except ValueError:
            return render(request, 'reservas/listar_reservas.html', {
                'error': 'Formato de fecha inválido. Use el formato AAAA-MM-DD.',
                'reservas': None,
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin,
            })

    # Verificar si el usuario pertenece al grupo 'Medico'
    es_medico = request.user.groups.filter(name='Medico').exists()

    paginator = Paginator(reservas, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'reservas/listar_reservas.html', {
        'reservas': page_obj,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'es_medico': es_medico,  # Pasar la verificación al template
    })

@login_required
@role_required('Recepcionista')
def crear_paciente(request):
    if request.method == 'POST':
        form = PacienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('recepcionista_dashboard')  # Ajusta según el nombre de tu URL de panel
    else:
        form = PacienteForm()

    return render(request, 'pacientes/crear_paciente.html', {'form': form})



@login_required
@role_required('Recepcionista')
def modificar_paciente(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)

    if request.method == 'POST':
        # Actualizar los datos del paciente
        paciente.nombre = request.POST.get('nombre')
        paciente.email = request.POST.get('email')
        paciente.telefono = request.POST.get('telefono')
        paciente.direccion = request.POST.get('direccion')
        paciente.save()

        # Mensaje de éxito
        messages.success(request, "Los datos del paciente se han actualizado exitosamente.")
        return redirect('listar_pacientes')  # Redirige al listado de pacientes

    return render(request, 'pacientes/modificar_paciente.html', {'paciente': paciente})



@login_required
@role_required('Recepcionista')
def eliminar_paciente(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)

    if request.method == 'POST':
        paciente.delete()
        messages.success(request, "Paciente eliminado exitosamente.")
        return redirect('listar_pacientes')  # Redirige a la lista de pacientes

    return redirect('listar_pacientes')  # Si no es POST, redirige igual

@login_required
@role_required('Recepcionista')
def crear_reserva(request):
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.paciente = form.cleaned_data['rut_paciente']
            reserva.fecha_reserva.ocupada = True
            reserva.fecha_reserva.save()
            reserva.save()

            # Ajustar la fecha a hora local
            fecha_local = localtime(reserva.fecha_reserva.fecha_disponible)

            # Crear notificación
            mensaje = f"Se ha registrado una nueva reserva para el paciente {reserva.paciente.nombre} para la fecha del {fecha_local.strftime('%d/%m/%Y %H:%M')}."
            Notificacion.objects.create(usuario=reserva.medico.user, mensaje=mensaje)

            messages.success(request, "Reserva creada exitosamente.")
            return redirect('listar_reservas')
        else:
            messages.error(request, "Hubo un error al crear la reserva. Verifique los datos.")
    else:
        form = ReservaForm()

    return render(request, 'reservas/crear_reserva.html', {'form': form})


@login_required
@role_required('Recepcionista')
def modificar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    especialidades = Especialidad.objects.all()
    medicos = Medico.objects.filter(especialidad=reserva.especialidad)
    disponibilidades = Disponibilidad.objects.filter(medico=reserva.medico, ocupada=False)

    if request.method == 'POST':
        especialidad_id = request.POST.get('especialidad')
        medico_id = request.POST.get('medico')
        fecha_reserva_id = request.POST.get('fecha_reserva')

        # Validar campos seleccionados
        if not especialidad_id or not medico_id or not fecha_reserva_id:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'reservas/modificar_reserva.html', {
                'reserva': reserva,
                'especialidades': especialidades,
                'medicos': medicos,
                'disponibilidades': disponibilidades
            })

        # Obtener instancias de los modelos seleccionados
        try:
            especialidad = Especialidad.objects.get(id=especialidad_id)
            medico = Medico.objects.get(id=medico_id, especialidad=especialidad)
            nueva_disponibilidad = Disponibilidad.objects.get(id=fecha_reserva_id, medico=medico, ocupada=False)
        except (Especialidad.DoesNotExist, Medico.DoesNotExist, Disponibilidad.DoesNotExist):
            messages.error(request, "Hubo un error al seleccionar los datos. Verifique las opciones.")
            return render(request, 'reservas/modificar_reserva.html', {
                'reserva': reserva,
                'especialidades': especialidades,
                'medicos': medicos,
                'disponibilidades': disponibilidades
            })

        # Liberar la disponibilidad anterior si se seleccionó una nueva
        if reserva.fecha_reserva != nueva_disponibilidad:
            reserva.fecha_reserva.ocupada = False
            reserva.fecha_reserva.save()
            nueva_disponibilidad.ocupada = True
            nueva_disponibilidad.save()

            # Crear notificación para el médico
            fecha_local = localtime(nueva_disponibilidad.fecha_disponible)
            mensaje = f"Se ha modificado la reserva para el paciente {reserva.paciente.nombre}. Nueva hora: {fecha_local.strftime('%d/%m/%Y %H:%M')}."
            Notificacion.objects.create(usuario=medico.user, mensaje=mensaje)

        # Actualizar los datos de la reserva
        reserva.especialidad = especialidad
        reserva.medico = medico
        reserva.fecha_reserva = nueva_disponibilidad
        reserva.motivo = request.POST.get('motivo', reserva.motivo)
        reserva.save()

        messages.success(request, "Reserva modificada exitosamente.")
        return redirect('listar_reservas')  # Redireccionar después de guardar

    # Contexto inicial si es GET
    return render(request, 'reservas/modificar_reserva.html', {
        'reserva': reserva,
        'especialidades': especialidades,
        'medicos': medicos,
        'disponibilidades': disponibilidades,
    })



@login_required
@role_required('Recepcionista')
def eliminar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if request.method == 'POST':
        reserva.fecha_reserva.ocupada = False
        reserva.fecha_reserva.save()

        # Ajustar la fecha a hora local
        fecha_local = localtime(reserva.fecha_reserva.fecha_disponible)

        # Crear notificación
        mensaje = f"Se ha eliminado la reserva para el paciente {reserva.paciente.nombre} programada para el {fecha_local.strftime('%d/%m/%Y %H:%M')}."
        Notificacion.objects.create(usuario=reserva.medico.user, mensaje=mensaje)

        reserva.delete()
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"error": "Método no permitido."}, status=405)






def api_medicos(request):
    especialidad_id = request.GET.get('especialidad_id')
    if not especialidad_id:
        return JsonResponse({'error': 'Se requiere el ID de la especialidad.'}, status=400)
    
    if not especialidad_id.isdigit():
        return JsonResponse({'error': 'El ID de la especialidad debe ser un número válido.'}, status=400)
    
    try:
        medicos = Medico.objects.filter(especialidad_id=especialidad_id)
        if not medicos.exists():
            return JsonResponse({'error': 'No hay médicos registrados para esta especialidad.'}, status=404)

        data = [{'id': medico.id, 'nombre': f"{medico.user.first_name} {medico.user.last_name}"} for medico in medicos]
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': f'Error inesperado: {str(e)}'}, status=500)



def api_disponibilidades(request):
    medico_id = request.GET.get('medico_id')
    if not medico_id:
        return JsonResponse({'error': 'Se requiere el ID del médico.'}, status=400)
    
    if not medico_id.isdigit():
        return JsonResponse({'error': 'El ID del médico debe ser un número válido.'}, status=400)

    try:
        medico = Medico.objects.get(id=medico_id)
        disponibilidades = Disponibilidad.objects.filter(
            medico=medico, ocupada=False, fecha_disponible__gte=now()
        )

        if not disponibilidades.exists():
            return JsonResponse({'error': 'No hay disponibilidades para este médico.'}, status=404)

        data = [
            {
                'id': disp.id,
                'fecha_hora': localtime(disp.fecha_disponible).strftime('%d/%m/%Y %H:%M')
            } for disp in disponibilidades
        ]
        return JsonResponse(data, safe=False)
    except Medico.DoesNotExist:
        return JsonResponse({'error': 'El médico no existe.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error inesperado: {str(e)}'}, status=500)


def api_validar_rut(request):
    rut = request.GET.get('rut')
    if not rut:
        return JsonResponse({'error': 'RUT no proporcionado.'}, status=400)
    
    # Valida formato del RUT
    if not re.match(r'^\d{7,8}-\d{1}$', rut):
        return JsonResponse({'error': 'El RUT debe estar en el formato correcto (12345678-9).'}, status=400)

    try:
        paciente = Paciente.objects.get(rut=rut)
        edad = paciente.edad if paciente.fecha_nacimiento else 'No registrada'

        return JsonResponse({
            'nombre': paciente.nombre,
            'edad': edad
        })
    except Paciente.DoesNotExist:
        return JsonResponse({'error': 'Paciente no encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error inesperado: {str(e)}'}, status=500)


from django.http import JsonResponse
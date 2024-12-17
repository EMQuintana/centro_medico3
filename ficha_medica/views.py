from django.shortcuts import render, get_object_or_404, redirect
from .models import FichaMedica, Paciente, Reserva, Disponibilidad, Medico, Especialidad, Recepcionista
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from ficha_medica.utils import role_required
from datetime import datetime, date
from django.http import JsonResponse
from ficha_medica.forms import FichaMedicaForm, DisponibilidadForm, ReservaForm, PacienteForm, MedicoForm, RecepcionistaForm
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.utils.timezone import make_aware, localtime, timezone, now
from django.contrib.auth.models import Group, User
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.core.cache import cache
from django.utils.dateformat import format
from django.core.exceptions import ValidationError

def admin_or_superuser_required(view_func):
    """
    Decorador que permite acceso solo a administradores o superusuarios.
    """
    return user_passes_test(lambda u: u.is_active and (u.is_staff or u.is_superuser))(view_func)

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
    current_time = now()

    # Obtener todas las reservas completas en vez de limitar los campos con 'values'
    reservas_hoy = Reserva.objects.filter(
        medico=medico,
        fecha_reserva__fecha_disponible__date=current_time.date(),
        fecha_reserva__fecha_disponible__gte=current_time
    ).select_related('paciente').order_by('fecha_reserva__fecha_disponible')

    # Recuperar notificaciones de CRUD de reservas (opcional)
    notificaciones = []
    for reserva in reservas_hoy:
        mensaje = cache.get(f"notificacion_reserva_{reserva.id}")
        if mensaje:
            notificaciones.append({'mensaje': mensaje, 'tipo': 'success'})
        mensaje_eliminada = cache.get(f"notificacion_reserva_eliminada_{reserva.id}")
        if mensaje_eliminada:
            notificaciones.append({'mensaje': mensaje_eliminada, 'tipo': 'error'})

    return render(request, 'core/medico.html', {
        'reservas_hoy': reservas_hoy,  # Enviar los objetos completos de Reserva
        'notificaciones': notificaciones
    })
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
    reservas_hoy = Reserva.objects.filter(
        medico=medico,
        fecha_reserva__fecha_disponible__date=date.today()  # Ajuste aquí
    )
    if request.method == 'POST':
        form = DisponibilidadForm(request.POST)
        if form.is_valid():
            disponibilidad = form.save(commit=False)
            disponibilidad.medico = medico
            disponibilidad.save()
            return redirect('gestionar_disponibilidades')
    else:
        form = DisponibilidadForm()

    return render(request, 'fichas_medicas/gestionar_disponibilidades.html', {
        'form': form,
        'disponibilidades': disponibilidades,
        'reservas_hoy': reservas_hoy,
    })



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
        rut_paciente = request.POST.get('rut_paciente')  # Obtén el RUT del paciente
        disponibilidad_id = request.POST.get('fecha_reserva')  # Obtén el ID de la disponibilidad seleccionada

        # Valida el paciente
        paciente = get_object_or_404(Paciente, rut=rut_paciente)

        # Valida la disponibilidad
        disponibilidad = get_object_or_404(Disponibilidad, id=disponibilidad_id)

        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.paciente = paciente  # Asigna el paciente a la reserva
            reserva.fecha_reserva = disponibilidad  # Asigna la disponibilidad seleccionada
            reserva.save()

            # Marca la disponibilidad como ocupada
            disponibilidad.ocupada = True
            disponibilidad.save()

            messages.success(request, f"Reserva creada exitosamente para {paciente.nombre}.")
            return redirect('listar_reservas')
        else:
            messages.error(request, "Hubo un error al crear la reserva.")
    else:
        form = ReservaForm()

    return render(request, 'reservas/crear_reserva.html', {'form': form})


@login_required
@role_required('Recepcionista')
def modificar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    medicos = Medico.objects.all()

    if request.method == 'POST':
        # Actualizar la información de la reserva
        medico_id = request.POST.get('medico')
        fecha_reserva_id = request.POST.get('fecha_reserva')
        motivo = request.POST.get('motivo')

        if medico_id and fecha_reserva_id:
            # Liberar la disponibilidad anterior
            reserva.fecha_reserva.ocupada = False
            reserva.fecha_reserva.save()

            # Asignar la nueva disponibilidad
            nueva_disponibilidad = get_object_or_404(Disponibilidad, id=fecha_reserva_id)
            nueva_disponibilidad.ocupada = True
            nueva_disponibilidad.save()

            # Actualizar la reserva
            reserva.medico_id = medico_id
            reserva.fecha_reserva = nueva_disponibilidad
            reserva.motivo = motivo
            reserva.save()

            return redirect('listar_reservas')

    context = {
        'reserva': reserva,
        'medicos': medicos,
    }
    return render(request, 'reservas/modificar_reserva.html', context)

@login_required
@role_required('Recepcionista')
def eliminar_reserva(request, reserva_id):
    if request.method == "POST":
        reserva = get_object_or_404(Reserva, id=reserva_id)
        # Liberar la disponibilidad asociada
        reserva.fecha_reserva.ocupada = False
        reserva.fecha_reserva.save()
        # Eliminar la reserva
        reserva.delete()
        return JsonResponse({"success": True})
    else:
        return JsonResponse({"error": "Método no permitido."}, status=405)





def api_medicos(request):
    especialidad_id = request.GET.get('especialidad_id')
    if especialidad_id:
        try:
            medicos = Medico.objects.filter(especialidad_id=especialidad_id)
            data = [{'id': medico.id, 'nombre': f"{medico.user.first_name} {medico.user.last_name}"} for medico in medicos]
        except Especialidad.DoesNotExist:
            data = {'error': 'Especialidad no encontrada.'}
    else:
        data = {'error': 'Se requiere el ID de la especialidad.'}
    return JsonResponse(data, safe=False)


def api_disponibilidades(request):
    medico_id = request.GET.get('medico_id')
    if medico_id:
        # Filtrar disponibilidades que no están ocupadas y cuya fecha no ha pasado
        disponibilidades = Disponibilidad.objects.filter(
            medico_id=medico_id, 
            ocupada=False, 
            fecha_disponible__gte=now()
        )
        data = [
            {
                'id': disp.id,
                'fecha_hora': localtime(disp.fecha_disponible).strftime('%d/%m/%Y %H:%M')
            } for disp in disponibilidades
        ]
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Se requiere el ID del médico.'}, status=400)

def api_validar_rut(request):
    rut = request.GET.get('rut')
    if not rut:
        return JsonResponse({'error': 'RUT no proporcionado.'}, status=400)

    try:
        paciente = Paciente.objects.get(rut=rut)
        if paciente.fecha_nacimiento:
            edad = paciente.edad
        else:
            edad = 'No registrada'
        return JsonResponse({
            'nombre': paciente.nombre,
            'edad': edad
        })
    except Paciente.DoesNotExist:
        return JsonResponse({'error': 'Paciente no encontrado.'}, status=404)

from django.http import JsonResponse
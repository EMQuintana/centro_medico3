from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import Medico, Recepcionista, FichaMedica, Reserva, Disponibilidad, Especialidad, Paciente
import re


# Función para validar el RUT
def validar_rut(rut):
    """
    Valida que el RUT esté en el formato correcto (12345678-9).
    """
    if not re.match(r'^\d{7,8}-\d{1}$', rut):
        raise ValidationError("El RUT debe estar en el formato 12345678-9.")
    return rut

def clean_rut(self):
    rut = self.cleaned_data.get('rut')
    if Paciente.objects.filter(rut=rut).exists():
        raise ValidationError("El RUT ingresado ya está registrado.")
    return rut


class MedicoForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    username = forms.CharField(label="RUT", validators=[validar_rut])
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput, required=False)

    class Meta:
        model = Medico
        fields = ['especialidad', 'telefono']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo inicializar si existe una instancia válida
        if self.instance.pk and hasattr(self.instance, 'user'):
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['username'].initial = self.instance.user.username

    def clean_username(self):
        username = self.cleaned_data['username']
        # Validar si el username ya existe en otro usuario
        user_id = getattr(self.instance.user, 'id', None) if self.instance.pk else None
        if User.objects.filter(username=username).exclude(id=user_id).exists():
            raise ValidationError("El RUT ingresado ya está registrado.")
        return username

    def save(self, commit=True):
        medico = super().save(commit=False)
        if not hasattr(self.instance, 'user') or not self.instance.user:
            # Crear un nuevo usuario si no existe
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                password=self.cleaned_data['password'],
            )
            medico.user = user
        else:
            # Actualizar el usuario existente
            user = self.instance.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.username = self.cleaned_data['username']
            if self.cleaned_data['password']:
                user.set_password(self.cleaned_data['password'])
            user.save()

        if commit:
            medico.save()
        return medico



class RecepcionistaForm(forms.ModelForm):
    first_name = forms.CharField(label="Nombre")
    last_name = forms.CharField(label="Apellido")
    username = forms.CharField(
        label="RUT",
        validators=[validar_rut],  # Validación personalizada
        help_text="Ingrese el RUT en el formato 12345678-9."
    )
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

    class Meta:
        model = Recepcionista
        fields = ['telefono', 'direccion', 'fecha_contratacion']

    def save(self, commit=True):
        recepcionista = super().save(commit=False)
        user = User.objects.create_user(
            username=self.cleaned_data['username'],  # RUT como username
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            password=self.cleaned_data['password']
        )
        recepcionista.user = user
        if commit:
            recepcionista.save()
        return recepcionista

class FichaMedicaForm(forms.ModelForm):
    class Meta:
        model = FichaMedica
        fields = ['diagnostico', 'tratamiento', 'observaciones']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['diagnostico'].widget.attrs.update({
            'placeholder': "Escribe el diagnóstico aquí"
        })
        self.fields['tratamiento'].widget.attrs.update({
            'placeholder': "Escribe el tratamiento aquí"
        })
        self.fields['observaciones'].widget.attrs.update({
            'placeholder': "Añade observaciones aquí (opcional)"
        })

class DisponibilidadForm(forms.ModelForm):
    class Meta:
        model = Disponibilidad
        fields = ['fecha_disponible']


class ReservaForm(forms.ModelForm):
    especialidad = forms.ModelChoiceField(
        queryset=Especialidad.objects.all(),
        label="Especialidad",
        required=True
    )
    medico = forms.ModelChoiceField(
        queryset=Medico.objects.none(),
        label="Médico",
        required=True
    )
    fecha_reserva = forms.ModelChoiceField(
        queryset=Disponibilidad.objects.none(),
        label="Horas Disponibles",
        required=True
    )
    rut_paciente = forms.CharField(
        label="RUT del Paciente",
        required=True,
        validators=[validar_rut],
        help_text="Ingrese el RUT en el formato 12345678-9."
    )

    class Meta:
        model = Reserva
        fields = ['fecha_reserva', 'motivo', 'especialidad', 'medico']

    fecha_reserva = forms.ModelChoiceField(
        queryset=Disponibilidad.objects.filter(ocupada=False),
        label="Fecha disponible",
        empty_label="Seleccione una fecha"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'especialidad' in self.data:
            try:
                especialidad_id = int(self.data.get('especialidad'))
                self.fields['medico'].queryset = Medico.objects.filter(especialidad_id=especialidad_id)
            except (ValueError, TypeError):
                pass
        if 'medico' in self.data:
            try:
                medico_id = int(self.data.get('medico'))
                self.fields['fecha_reserva'].queryset = Disponibilidad.objects.filter(medico_id=medico_id, ocupada=False)
            except (ValueError, TypeError):
                pass

    def clean_rut_paciente(self):
        rut = self.cleaned_data['rut_paciente']
        try:
            paciente = Paciente.objects.get(rut=rut)
        except Paciente.DoesNotExist:
            raise ValidationError("No se encontró un paciente con este RUT.")
        return paciente


class PacienteForm(forms.ModelForm):
    rut = forms.CharField(
        label="RUT",
        validators=[validar_rut],  # Validación personalizada
        help_text="Ingrese el RUT en el formato 12345678-9."
    )
    nombre = forms.CharField(label="Nombre completo")
    fecha_nacimiento = forms.DateField(
        label="Fecha de nacimiento",
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True,
    )
    direccion = forms.CharField(
        label="Dirección",
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False,
    )
    telefono = forms.CharField(
        label="Teléfono",
        required=False,
        help_text="Ingrese el número sin espacios ni caracteres especiales."
    )
    email = forms.EmailField(label="Correo electrónico", required=False)

    class Meta:
        model = Paciente
        fields = ['rut', 'nombre', 'fecha_nacimiento', 'direccion', 'telefono', 'email']
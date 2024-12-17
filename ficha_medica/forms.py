from django import forms
from datetime import datetime
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
        if self.instance.pk:  # Solo si el médico ya existe
            user = getattr(self.instance, 'user', None)
            if user:
                self.fields['first_name'].initial = user.first_name
                self.fields['last_name'].initial = user.last_name
                self.fields['username'].initial = user.username

    def clean_username(self):
        username = self.cleaned_data['username']
        user_id = getattr(self.instance.user, 'id', None) if hasattr(self.instance, 'user') else None
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
                password=self.cleaned_data['password'] or "default_password123"  # Asignar contraseña predeterminada si está vacía
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
    username = forms.CharField(label="RUT", validators=[validar_rut])
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

    class Meta:
        model = Recepcionista
        fields = ['telefono', 'direccion', 'fecha_contratacion']

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise ValidationError("El RUT ingresado ya está registrado.")
        return username

    def save(self, commit=True):
        try:
            recepcionista = super().save(commit=False)
            user = User.objects.create_user(
                username=self.cleaned_data['username'],
                first_name=self.cleaned_data['first_name'],
                last_name=self.cleaned_data['last_name'],
                password=self.cleaned_data['password']
            )
            recepcionista.user = user
            if commit:
                recepcionista.save()
            return recepcionista
        except IntegrityError:
            raise ValidationError("Error al guardar el recepcionista: el RUT ya existe en la base de datos.")



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
    def save(self, commit=True):
        try:
            return super().save(commit=commit)
        except IntegrityError:
            raise ValidationError("Error al guardar la ficha médica. Verifique los datos ingresados.")

class DisponibilidadForm(forms.ModelForm):
    fecha = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha")
    hora = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), label="Hora")

    class Meta:
        model = Disponibilidad
        fields = []

    def save(self, commit=True):
        try:
            disponibilidad = super().save(commit=False)
            fecha = self.cleaned_data['fecha']
            hora = self.cleaned_data['hora']
            disponibilidad.fecha_disponible = datetime.combine(fecha, hora)
            if commit:
                disponibilidad.save()
            return disponibilidad
        except IntegrityError:
            raise ValidationError("Error al guardar la disponibilidad. Verifique los datos.")



class ReservaForm(forms.ModelForm):
    especialidad = forms.ModelChoiceField(queryset=Especialidad.objects.all(), label="Especialidad")
    medico = forms.ModelChoiceField(queryset=Medico.objects.none(), label="Médico")
    fecha_reserva = forms.ModelChoiceField(queryset=Disponibilidad.objects.none(), label="Horas Disponibles")
    rut_paciente = forms.CharField(label="RUT del Paciente", validators=[validar_rut])

    class Meta:
        model = Reserva
        fields = ['fecha_reserva', 'motivo', 'especialidad', 'medico']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'especialidad' in self.data:
            try:
                especialidad_id = int(self.data.get('especialidad'))
                self.fields['medico'].queryset = Medico.objects.filter(especialidad_id=especialidad_id)
            except (ValueError, TypeError):
                pass

    def clean_rut_paciente(self):
        rut = self.cleaned_data['rut_paciente']
        try:
            return Paciente.objects.get(rut=rut)
        except Paciente.DoesNotExist:
            raise ValidationError("No se encontró un paciente con este RUT.")

    def save(self, commit=True):
        try:
            reserva = super().save(commit=False)
            reserva.paciente = self.cleaned_data['rut_paciente']
            if commit:
                reserva.save()
            return reserva
        except IntegrityError:
            raise ValidationError("Error al guardar la reserva. Verifique los datos ingresados.")




import re

class PacienteForm(forms.ModelForm):
    rut = forms.CharField(label="RUT", validators=[validar_rut])
    nombre = forms.CharField(label="Nombre completo")
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha de Nacimiento")
    direccion = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)
    telefono = forms.CharField(
        label="Teléfono", 
        required=False, 
        help_text="Ingrese solo números sin espacios ni guiones."
    )
    email = forms.EmailField(label="Correo electrónico", required=False)

    class Meta:
        model = Paciente
        fields = ['rut', 'nombre', 'fecha_nacimiento', 'direccion', 'telefono', 'email']

    def clean_rut(self):
        rut = self.cleaned_data['rut']
        if Paciente.objects.filter(rut=rut).exists():
            raise ValidationError("El RUT ya está registrado.")
        return rut

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono']
        if telefono and not re.match(r'^\d+$', telefono):
            raise ValidationError("El teléfono solo debe contener números.")
        return telefono

    def save(self, commit=True):
        try:
            return super().save(commit=commit)
        except IntegrityError:
            raise ValidationError("Error al guardar el paciente. Verifique los datos.")


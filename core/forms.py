from django import forms
from ficha_medica.models import FichaMedica, Paciente, Reserva

class FichaMedicaForm(forms.ModelForm):
    class Meta:
        model = FichaMedica
        fields = ['paciente', 'medico', 'diagnostico', 'tratamiento', 'observaciones']

class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = ['rut', 'nombre', 'direccion', 'telefono', 'email']

class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['recepcionista', 'paciente', 'fecha_reserva', 'motivo']

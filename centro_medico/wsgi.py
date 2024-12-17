"""
WSGI config for centro_medico project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'centro_medico.settings')

application = get_wsgi_application()

app= application



User = get_user_model()

username = "root"  # Cambia esto  # Cambia esto
password = "root123"  # Cambia esto por una contraseña segura

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, password=password)
    print("Superusuario creado exitosamente.")
else:
    print("El superusuario ya existe.")
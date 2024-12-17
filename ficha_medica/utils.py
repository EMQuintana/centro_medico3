from django.http import HttpResponseForbidden
import re
from django.core.exceptions import ValidationError


def role_required(role_name):
    """
    Decorador para verificar que un usuario pertenece a un grupo específico.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.groups.filter(name=role_name).exists():
                return HttpResponseForbidden(f"No tienes acceso al rol requerido: {role_name}.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

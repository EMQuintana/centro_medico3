from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Agrega una clase CSS al widget de un campo de formulario.
    """
    return field.as_widget(attrs={"class": css_class})
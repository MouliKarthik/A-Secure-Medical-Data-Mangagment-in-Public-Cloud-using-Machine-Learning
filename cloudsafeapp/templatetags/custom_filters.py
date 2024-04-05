from django import template

register = template.Library()


@register.filter
def as_text(value):
    return str(value)

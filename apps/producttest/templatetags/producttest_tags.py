from django import template

register = template.Library()


@register.filter
def is_supervisor_filter(user):
    return user.groups.filter(name="supervisor").exists()


@register.filter
def format_decimal(value):
    if value is None:
        return "0"
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value)


@register.filter
def thai_date(value):
    if not value:
        return "-"
    try:
        return value.strftime("%d/%m/%Y")
    except AttributeError:
        return str(value)

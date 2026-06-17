from django import template

register = template.Library()


@register.filter
def get_qty(quantities, pk):
    """Return quantity for a media type pk from a {str(pk): qty} dict. Defaults to 1."""
    try:
        return int(quantities.get(str(pk), 1))
    except (ValueError, TypeError):
        return 1

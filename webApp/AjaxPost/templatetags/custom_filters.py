from django import template

register = template.Library()

@register.filter
def range_inclusive(value):
	return range(value + 1)


@register.simple_tag
def define(val=None):
  return val+1


@register.filter
def add_value(value, arg):
    return str(value) + str(arg+1)
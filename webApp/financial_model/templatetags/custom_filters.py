from django import template

register = template.Library()

@register.simple_tag
def get_financial_model(financial_models, project_id):
		# Loop through financial models and return the one that matches the project_id and has the correct identifier
		for fm in financial_models:
				if fm.project_id == project_id and fm.identifier == "sponsor_production_choice":
						return fm
		return None

@register.filter
def thousands_separator(value):
	"""Format number with thousands separator and no decimals"""
	try:
		return f"{int(float(value)):,}"
	except (ValueError, TypeError):
		return value
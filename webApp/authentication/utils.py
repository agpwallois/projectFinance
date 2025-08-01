# utils.py - Fixed version
from authentication.models import Company

def get_user_company(user):
	"""
	Get the company associated with a user.
	Since User model has a direct company ForeignKey, check that first.
	"""
	# Check if user has company directly assigned
	if hasattr(user, 'company') and user.company:
		return user.company
	
	# Fallback: auto-detection by email domain
	if user.email:
		return Company.get_company_from_email(user.email)
	
	return None


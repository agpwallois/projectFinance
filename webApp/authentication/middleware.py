# middleware.py
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from .models import Company

User = get_user_model()

class CompanyVerificationMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response
		self.excluded_urls = [
			'/login/',
			'/logout/',
			'/register/',
			'/admin/',
			'/',
		]

	def __call__(self, request):
		if (request.user.is_authenticated and 
			not any(request.path.startswith(url) for url in self.excluded_urls)):
			
			# DEBUG: Let's see what's happening
			print(f"DEBUG MIDDLEWARE: User: {request.user.email}")
			print(f"DEBUG MIDDLEWARE: User company: {request.user.company}")
			print(f"DEBUG MIDDLEWARE: Path: {request.path}")
			
			# Check if user has a company - Fix the logic here
			if request.user.company is None:
				print("DEBUG MIDDLEWARE: No company found, attempting assignment")
				company = self.attempt_automatic_assignment(request.user)
				if not company:
					print("DEBUG MIDDLEWARE: Auto-assignment failed, logging out")
					# Log out the user properly
					logout(request)
					messages.error(request, 'Your account is not associated with any company. Please contact your administrator.')
					return redirect('login')  # Redirect to login instead of logout
				else:
					print(f"DEBUG MIDDLEWARE: Auto-assigned company: {company.name}")
					# Refresh the user object to get the updated company
					request.user.refresh_from_db()

		response = self.get_response(request)
		return response
	
	def attempt_automatic_assignment(self, user):
		"""
		Try to automatically assign a company based on email domain
		"""
		if user.email:
			domain = user.email.split('@')[1] if '@' in user.email else None
			if domain:
				company = Company.objects.filter(email_domain=domain).first()
				if company:
					print(f"DEBUG: Found company {company.name} for domain {domain}")
					# Assign company directly to user
					user.company = company
					user.save()
					return company
				else:
					print(f"DEBUG: No company found for domain {domain}")
		return None
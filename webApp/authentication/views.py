# views/auth_views.py
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from authentication.models import Company, User


def login_view(request):
	if request.method == 'POST':
		print(f"DEBUG LOGIN - POST data: {dict(request.POST)}")
		
		email = request.POST.get('email', '')
		password = request.POST.get('password', '')
		
		print(f"DEBUG LOGIN - Email: '{email}'")
		print(f"DEBUG LOGIN - Password provided: {'Yes' if password else 'No'}")
		
		if not email or not password:
			missing = []
			if not email:
				missing.append('Email')
			if not password:
				missing.append('Password')
			messages.error(request, f'Missing required fields: {", ".join(missing)}')
			return render(request, 'authentication/login.html')
		
		user = authenticate(request, email=email, password=password)
		
		if user is not None:
			# Check if user has company assigned
			if user.company:
				login(request, user)
				return redirect('project_list')
			else:
				# Auto-assign company based on email domain
				company = Company.get_company_from_email(user.email)
				if company:
					user.company = company
					user.save()
					login(request, user)
					return redirect('project_list')
				else:
					# Don't login the user if no company can be assigned
					messages.error(request, f'No company found for your email domain (@{user.email.split("@")[1]}). Please contact your administrator.')
		else:
			messages.error(request, 'Invalid email or password.')
	
	return render(request, 'authentication/login.html')


def logout_view(request):
	if request.user.is_authenticated:
		company_name = None
		if request.user.company:
			company_name = request.user.company.name
		
		logout(request)
		
		if company_name:
			messages.info(request, f'You have been logged out')
		else:
			messages.info(request, 'You have been logged out')
	
	return redirect('login')


def register_view(request):
	if request.method == 'POST':
		email = request.POST['email']
		password = request.POST['password']
		password_confirm = request.POST['password_confirm']
		
		# Basic validations
		if password != password_confirm:
			messages.error(request, 'Passwords do not match')
			return render(request, 'authentication/register.html')
		
		if User.objects.filter(email=email).exists():
			messages.error(request, 'Email already in use')
			return render(request, 'authentication/register.html')
		
		# Check company
		domain = email.split('@')[1] if '@' in email else None
		company = None
		if domain:
			company = Company.objects.filter(email_domain=domain).first()
		
		if not company:
			messages.error(request, f'No registered company for domain @{domain}. Contact administrator.')
			return render(request, 'authentication/register.html')
		
		# Create user with company directly assigned
		user = User.objects.create_user(
			email=email,
			password=password,
			company=company  # Assign company directly to user
		)
		
		# Auto login
		login(request, user)
		return redirect('project_list')
	
	return render(request, 'authentication/register.html')
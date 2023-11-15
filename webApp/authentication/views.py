from django.shortcuts import render
from . import forms
from django.contrib.auth import login, authenticate
from django.views.generic import View
from django.shortcuts import redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

class LoginPageView(View):
	template_name = 'authentication/login.html'
	form_class = forms.LoginForm

	def get(self, request):
		form = self.form_class()
		message = ''
		return render(request, self.template_name, context={'form': form, 'message': message})
		
	def post(self, request):
		form = self.form_class(request.POST)
		if form.is_valid():
			user = authenticate(
				email=form.cleaned_data['email'],
				password=form.cleaned_data['password'],
			)
			if user is not None:
				login(request, user)
				return redirect('/projects/')
		message = 'Invalid credentials.'
		return render(request, self.template_name, context={'form': form, 'message': message})





# authentication/forms.py
from django import forms

class LoginForm(forms.Form):
    email = forms.CharField(max_length=63, widget=forms.EmailInput, label='Email')
    password = forms.CharField(max_length=63, widget=forms.PasswordInput, label='Mot de passe')
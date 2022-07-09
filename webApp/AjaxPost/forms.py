from django import forms
from .models import SProject

class SProjectForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = ['name','genre','country']
	 
class TimelineForm(forms.ModelForm):
    class Meta:
     model = SProject
     fields = ['start_year','length','periodicity']

class RevenuesForm(forms.ModelForm):
    class Meta:
     model = SProject
     fields = ['revenues','inflation']

class OpexForm(forms.ModelForm):
    class Meta:
     model = SProject
     fields = ['opex']
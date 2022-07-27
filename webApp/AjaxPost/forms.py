from django import forms
from .models import SProject
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, HTML

class SProjectForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = ['name','genre','country']

PERIODICITY_CHOICES= [
	('3', 'Quarterly'),
	('6', 'Semi-annual'),
	]

class TimelineForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = ['start_construction','end_construction', 'operating_life','periodicity']
	 widgets = {
		'start_construction': forms.DateInput(
		attrs={'class': 'form-control', 
		   'placeholder': 'Select a date',
		   'type': 'date'
		  }),
		'end_construction': forms.DateInput(
		attrs={'class': 'form-control', 
		   'placeholder': 'Select a date',
		   'type': 'date'
		  }),
	}

class ProductionForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = [
	 'panels_capacity',
	 'annual_degradation',
	 'p50',
	 'p90_10y',
	 'P99_10y',
	 'availability', 
	 'seasonality_m1', 
	 'seasonality_m2',
	 'seasonality_m3',
	 'seasonality_m4',
	 'seasonality_m5',
	 'seasonality_m6',
	 'seasonality_m7',
	 'seasonality_m8',
	 'seasonality_m9',
	 'seasonality_m10', 
	 'seasonality_m11',
	 'seasonality_m12',
	 ]

class ConstructionForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = [
	 'costs_at_NTP',
	 'costs_at_FC',
	 'costs_m1',
	 'costs_m2',
	 'costs_m3',
	 'costs_m4',
	 'costs_m5',
	 'costs_m6',
	 'costs_m7',
	 'costs_m8',
	 'costs_m9',
	 'costs_m10',
	 'costs_m11',
	 'costs_m12',
	 ]

class RevenuesForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = [
	 'start_contract',
	 'end_contract',
	 'contract_price',
	 'contract_indexation_start_date',
     'contract_indexation',
	 ]
	 widgets = {
		'start_contract': forms.DateInput(
		attrs={'class': 'form-control', 
		   'placeholder': 'Select a date',
		   'type': 'date'
		  }),
		'end_contract': forms.DateInput(
		attrs={'class': 'form-control', 
		   'placeholder': 'Select a date',
		   'type': 'date'
		  }),
		'contract_indexation_start_date': forms.DateInput(
		attrs={'class': 'form-control', 
		   'placeholder': 'Select a date',
		   'type': 'date'
		  }),
	}


class OpexForm(forms.ModelForm):
	class Meta:
	 model = SProject
	 fields = ['opex']
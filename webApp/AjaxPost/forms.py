from django import forms
from .models import Project
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, HTML

PERIODICITY_CHOICES= [
	('3', 'Quarterly'),
	('6', 'Semi-annual'),
	]

class ProjectForm(forms.ModelForm):
	class Meta:
	 model = Project
	 fields = [
	 'start_construction',
	 'end_construction', 
	 'operating_life',
	 'periodicity',
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
	 'start_contract',
	 'end_contract',
	 'contract_price',
	 'contract_indexation_start_date',
	 'contract_indexation',
	 ]
	 
	def __init__(self, *args, **kwargs):
		super(ProjectForm, self).__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs['class'] = 'form'
		'''self.fields['name'].required = False
		self.fields['genre'].required = False
		self.fields['country'].required = False
		self.fields['opex'].required = False'''





class TimelineForm(forms.ModelForm):
	class Meta:
	 model = Project
	 fields = ['start_construction','end_construction', 'operating_life','periodicity']
	 widgets = {
		'start_construction': forms.DateInput(
		attrs={'class': 'form', 
		   'type': 'date',
		 }),
		'end_construction': forms.DateInput(
		attrs={'class': 'form', 
		   'type': 'date',
		}),
		'operating_life': forms.NumberInput(
		attrs={'class': 'form', 
		}),
	}
	periodicity = forms.ChoiceField(choices=PERIODICITY_CHOICES, widget=forms.RadioSelect)


class ProductionForm(forms.ModelForm):
	class Meta:
	 model = Project
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
	 widgets = {
		'panels_capacity': forms.NumberInput(
		attrs={'class': 'form', 

		}),
		'annual_degradation': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'p50': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'p90_10y': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'P99_10y': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'availability': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m1': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m2': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m3': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m4': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m5': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m6': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m7': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m8': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m9': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m10': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m11': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'seasonality_m12': forms.NumberInput(
		attrs={'class': 'form', 
		}),
	}

class ConstructionForm(forms.ModelForm):
	class Meta:
	 model = Project
	 fields = [
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
	 widgets = {
		'costs_at_NTP': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_at_FC': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m1': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m2': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m3': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m4': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m5': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m6': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m7': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m8': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m9': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m10': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m11': forms.NumberInput(
		attrs={'class': 'form', 
		}),
		'costs_m12': forms.NumberInput(
		attrs={'class': 'form', 
		}),
	}

class RevenuesForm(forms.ModelForm):
	class Meta:
	 model = Project
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
		   'type': 'date',
		  }),
		'end_contract': forms.DateInput(
		attrs={'class': 'form-control', 
		   'placeholder': 'Select a date',
		   'type': 'date',
		  }),
		'contract_indexation_start_date': forms.DateInput(
		attrs={'class': 'form-control', 
		   'placeholder': 'Select a date',
		   'type': 'date',
		  }),
		'contract_price': forms.NumberInput(
		attrs={'class': 'form-control', 
		  }),
	}


from django import forms
from .models import Project


PERIODICITY_CHOICES= [
	('3', 'Quarterly'),
	('6', 'Semi-annual'),
	]

PRODUCTION_CHOICES= [
	('1', 'P50'),
	('2', 'P90'),
	('3', 'P99'),
	]

ELECTRICITY_PRICES_CHOICES= [
	('1', 'Low'),
	('2', 'Medium'),
	('3', 'High'),
	]

class ProjectForm(forms.ModelForm):
	class Meta:
	 model = Project
	 fields = '__all__'
	 widgets = {
		'start_construction': forms.DateInput(attrs={'type': 'date',}),
		'end_construction': forms.DateInput(attrs={'type': 'date',}),
		'start_contract': forms.DateInput(attrs={'type': 'date',}),
		'end_contract': forms.DateInput(attrs={'type': 'date',}),
		'contract_indexation_start_date': forms.DateInput(attrs={'type': 'date',}),
		'price_elec_indexation_start_date': forms.DateInput(attrs={'type': 'date',}),
		'periodicity': forms.RadioSelect(choices=PERIODICITY_CHOICES),
		'opex_indexation_start_date': forms.DateInput(attrs={'type': 'date',}),
		'production_choice': forms.RadioSelect(choices=PRODUCTION_CHOICES),
		'price_elec_choice': forms.RadioSelect(choices=ELECTRICITY_PRICES_CHOICES),
	}
	 
	def __init__(self, *args, **kwargs):
		super(ProjectForm, self).__init__(*args, **kwargs)

		exclude_from_formatting = [self.fields['periodicity'],
								   self.fields['production_choice'],
								   self.fields['price_elec_choice'],]

		for field in self.fields.values():
			if field not in exclude_from_formatting:
				field.widget.attrs['class'] = 'form'


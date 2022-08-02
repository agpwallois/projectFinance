from django import forms
from .models import Project


PERIODICITY_CHOICES= [
	('3', 'Quarterly'),
	('6', 'Semi-annual'),
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

	}
	 
	def __init__(self, *args, **kwargs):
		super(ProjectForm, self).__init__(*args, **kwargs)
		for field in self.fields.values():
			if field != self.fields['periodicity']:
				field.widget.attrs['class'] = 'form'


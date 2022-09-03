from django import forms
from .models import Project
from dateutil.relativedelta import relativedelta

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

TECHNOLOGY_CHOICES= [
	('1', 'Solar'),
	('2', 'Wind'),
	]

COUNTRY_CHOICES= [
	('1', 'Italy'),
	('2', 'France'),
	('3', 'Spain'),
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
								   self.fields['price_elec_choice'],
					
						
								  
								   ]

		for field in self.fields.values():
			if field not in exclude_from_formatting:
				field.widget.attrs['class'] = 'form'

	def clean(self):
		cleaned_data = self.cleaned_data

		start_construction = cleaned_data.get('start_construction')
		end_construction = cleaned_data.get('end_construction')

		if end_construction<start_construction:
			self.add_error('end_construction','Construction end date should not occur before construction start date.')

		start_contract = cleaned_data.get('start_contract')
		end_contract = cleaned_data.get('end_contract')

		if end_contract<start_contract:
			self.add_error('end_contract','Contract end date should not occur before contract start date.')

		if start_contract<end_construction:
			self.add_error('start_contract','Contract start date should not occur before construction end date.')

		seasonality_m1 = cleaned_data.get('seasonality_m1')
		seasonality_m2 = cleaned_data.get('seasonality_m2')
		seasonality_m3 = cleaned_data.get('seasonality_m3')
		seasonality_m4 = cleaned_data.get('seasonality_m4')
		seasonality_m5 = cleaned_data.get('seasonality_m5')
		seasonality_m6 = cleaned_data.get('seasonality_m6')
		seasonality_m7 = cleaned_data.get('seasonality_m7')
		seasonality_m8 = cleaned_data.get('seasonality_m8')
		seasonality_m9 = cleaned_data.get('seasonality_m9')
		seasonality_m10 = cleaned_data.get('seasonality_m10')
		seasonality_m11 = cleaned_data.get('seasonality_m11')
		seasonality_m12 = cleaned_data.get('seasonality_m12')

		seasonality = [
		seasonality_m1,
		seasonality_m2,
		seasonality_m3,
		seasonality_m4,
		seasonality_m5,
		seasonality_m6,
		seasonality_m7,
		seasonality_m8,
		seasonality_m9, 
		seasonality_m10,
		seasonality_m11,
		seasonality_m12,
		]

		sum_seasonality = sum(seasonality)

		if sum_seasonality!=1:
			self.add_error('seasonality_m1','Sum of seasonality factors must be 1.')

		costs_m1 = cleaned_data.get('costs_m1')
		costs_m2 = cleaned_data.get('costs_m2')
		costs_m3 = cleaned_data.get('costs_m3')
		costs_m4 = cleaned_data.get('costs_m4')
		costs_m5 = cleaned_data.get('costs_m5')
		costs_m6 = cleaned_data.get('costs_m6')
		costs_m7 = cleaned_data.get('costs_m7')
		costs_m8 = cleaned_data.get('costs_m8')
		costs_m9 = cleaned_data.get('costs_m9')
		costs_m10 = cleaned_data.get('costs_m10')
		costs_m11 = cleaned_data.get('costs_m11')
		costs_m12 = cleaned_data.get('costs_m12')

		months_construction = end_construction.month - start_construction.month + 1

		if costs_m2>0 and 2>months_construction:
			self.add_error('costs_m2','Construction costs out of construction period')

		if costs_m3>0 and 3>months_construction:
			self.add_error('costs_m3','Construction costs out of construction period')
		
		if costs_m4>0 and 4>months_construction:
			self.add_error('costs_m4','Construction costs out of construction period')

		if costs_m5>0 and 5>months_construction:
			self.add_error('costs_m5','Construction costs out of construction period')

		if costs_m6>0 and 6>months_construction:
			self.add_error('costs_m6','Construction costs out of construction period')

		if costs_m7>0 and 7>months_construction:
			self.add_error('costs_m7','Construction costs out of construction period')

		if costs_m8>0 and 8>months_construction:
			self.add_error('costs_m8','Construction costs out of construction period')

		if costs_m9>0 and 9>months_construction:
			self.add_error('costs_m9','Construction costs out of construction period')

		if costs_m10>0 and 10>months_construction:
			self.add_error('costs_m10','Construction costs out of construction period')

		if costs_m11>0 and 11>months_construction:
			self.add_error('costs_m11','Construction costs out of construction period')

		if costs_m12>0 and 12>months_construction:
			self.add_error('costs_m12','Construction costs out of construction period')

		length_construction = relativedelta(end_construction, start_construction).years
		operating_life = cleaned_data.get('operating_life')
		debt_tenor = cleaned_data.get('debt_tenor')
		debt_max_tenor = length_construction+operating_life

		if debt_tenor>debt_max_tenor:
			self.add_error('debt_tenor','Debt tenor cannot exceed project life')

		return cleaned_data




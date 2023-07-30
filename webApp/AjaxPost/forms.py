from django import forms
from .models import Project
from dateutil.relativedelta import relativedelta
import math
import datetime
from django.core.exceptions import ValidationError

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


DEV_FEE_CHOICES= [
	('1', 'Yes'),
	('2', 'No'),
	]

EQUITY_CHOICES= [
	('1', 'Equity first'),
	('2', 'Prorata'),
	]


CALCULATION_DETAILS_CHOICES= [
	('1', 'Simplified'),
	('2', 'Detailed'),
	]


DSRA_CHOICES= [
	('1', '6 months'),
	('2', '12 months'),
	]

class ProjectForm(forms.ModelForm):
	calculation_type = forms.CharField(widget=forms.HiddenInput(), required=False)

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
		'devfee_choice': forms.RadioSelect(choices=DEV_FEE_CHOICES),
		'injection_choice': forms.RadioSelect(choices=EQUITY_CHOICES),
		'calculation_detail': forms.RadioSelect(choices=CALCULATION_DETAILS_CHOICES),
		'DSRA_choice': forms.RadioSelect(choices=DSRA_CHOICES),
		'sensi_production': forms.TextInput(attrs={'step': '5', 'type': 'range', 'value': '0', 'min': '-100', 'max': '100'}),
		'sensi_opex': forms.TextInput(attrs={'step': '5', 'type': 'range', 'value': '0', 'min': '-100', 'max': '100'}),
		'sensi_inflation': forms.TextInput(attrs={'step': '1', 'type': 'range', 'value': '0', 'min': '-3', 'max': '3'}),
		}
	 
	def __init__(self, *args, **kwargs):
		super(ProjectForm, self).__init__(*args, **kwargs)

		exclude_from_formatting = [self.fields['periodicity'],
								   self.fields['production_choice'],
								   self.fields['price_elec_choice'],
								   self.fields['devfee_choice'],
								   self.fields['injection_choice'],
								   self.fields['calculation_detail'],
								   self.fields['DSRA_choice'],
					
			
								   ]

		for field in self.fields.values():
			if field not in exclude_from_formatting:
				field.widget.attrs['class'] = 'form'

	

	def clean(self):
		cleaned_data = self.cleaned_data

		# Timeline
		start_construction = cleaned_data.get('start_construction')
		end_construction = cleaned_data.get('end_construction')


		difference = (end_construction - start_construction).days
		if difference>365*2:
			raise ValidationError(
				"Current maximum construction duration is 24 months."
			)


		if end_construction<start_construction:
			raise ValidationError(
				"Construction end date should not occur before construction start date."
			)

		# Offtake contract
		start_contract = cleaned_data.get('start_contract')
		end_contract = cleaned_data.get('end_contract')

		if end_contract<start_contract:
			self.add_error('end_contract','Contract end date should not occur before contract start date.')

		if start_contract<end_construction:
			self.add_error('start_contract','Contract start date should not occur before construction end date.')

		# Seasonality
		seasonality = []
		for i in range(1, 13):
			seasonality_value = cleaned_data.get(f'seasonality_m{i}')
			seasonality.append(seasonality_value)

		sum_seasonality = sum(seasonality)

		if sum_seasonality!=1:
			self.add_error('seasonality_m1','Sum of seasonality factors must be 100%.')


		length_construction = relativedelta(end_construction, start_construction).years
		operating_life = cleaned_data.get('operating_life')
		debt_tenor = cleaned_data.get('debt_tenor')
		debt_max_tenor = length_construction+operating_life



		if operating_life>40:
			raise ValidationError(
				"Current maximum operating duration is 40 years."
			)


		if debt_tenor>debt_max_tenor:
			self.add_error('debt_tenor','Debt tenor cannot exceed project life')


		# Liquidation
		liquidation = cleaned_data.get('liquidation')

		if liquidation<0:
			self.add_error('liquidation','Liquidation delay must be greater or equal to 0.')

		return cleaned_data




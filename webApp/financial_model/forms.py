from django import forms
from .model_project import Project
from dateutil.relativedelta import relativedelta
import math
from datetime import datetime
from django.core.exceptions import ValidationError




PERIODICITY_CHOICES= [
	('3', 'Quarterly'),
	('6', 'Semi-annual'),
	]

ELECTRICITY_PRICES_CHOICES= [
	('1', 'Low'),
	('2', 'Central'),
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

PRODUCTION_CHOICES= [
	('1', 'P90'),
	('2', 'P75'),
	('3', 'P50'),
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

		'price_elec_choice': forms.Select(choices=ELECTRICITY_PRICES_CHOICES),

		'devfee_choice': forms.RadioSelect(choices=DEV_FEE_CHOICES),
		'injection_choice': forms.RadioSelect(choices=EQUITY_CHOICES),
		'calculation_detail': forms.RadioSelect(choices=CALCULATION_DETAILS_CHOICES),
		'DSRA_choice': forms.RadioSelect(choices=DSRA_CHOICES),
		'production_choice': forms.Select(choices=PRODUCTION_CHOICES),

		'sponsor_production_choice': forms.Select(choices=PRODUCTION_CHOICES),
		'sponsor_price_elec_choice': forms.Select(choices=ELECTRICITY_PRICES_CHOICES),


		'lease_indexation_start_date': forms.DateInput(attrs={'type': 'date',}),


		'sensi_production': forms.TextInput(attrs={'step': '5', 'type': 'range', 'value': '0', 'min': '-30', 'max': '30'}),
		'sensi_inflation': forms.TextInput(attrs={'step': '1', 'type': 'range', 'value': '0', 'min': '-3', 'max': '3'}),
		'sensi_opex': forms.TextInput(attrs={'step': '5', 'type': 'range', 'value': '0', 'min': '-100', 'max': '100'}),

		'sensi_production_sponsor': forms.TextInput(attrs={'step': '5', 'type': 'range', 'value': '0', 'min': '-30', 'max': '30'}),
		'sensi_inflation_sponsor': forms.TextInput(attrs={'step': '1', 'type': 'range', 'value': '0', 'min': '-3', 'max': '3'}),
		'sensi_opex_sponsor': forms.TextInput(attrs={'step': '5', 'type': 'range', 'value': '0', 'min': '-100', 'max': '100'}),



		}
	 
	def __init__(self, *args, **kwargs):
		super(ProjectForm, self).__init__(*args, **kwargs)

		exclude_from_formatting = [self.fields['periodicity'],
								   self.fields['devfee_choice'],
								   self.fields['injection_choice'],
								   self.fields['calculation_detail'],
								   self.fields['DSRA_choice'],
								   self.fields['project_status'],
				
			
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
		operating_life = cleaned_data.get('operating_life')
		debt_tenor = cleaned_data.get('debt_tenor')
		

		operating_life_years = cleaned_data.get('operating_life')  # Convert 'operating_life' to an integer representing years

		# Calculate 'end_operations' by adding 'operating_life' years to 'end_construction' (accounting for leap years)
		end_operations = end_construction + relativedelta(years=operating_life_years)

		if end_contract<start_contract:
			self.add_error('end_contract','Contract end date should not occur before contract start date.')

		if start_contract<end_construction:
			self.add_error('start_contract','Contract start date should not occur before construction end date.')


		if end_contract>end_operations:
			self.add_error('end_contract','Contract end date should not occur after operations end date.')






		# Seasonality
		seasonality = []
		for i in range(1, 13):
			seasonality_value = cleaned_data.get(f'seasonality_m{i}')
			seasonality.append(seasonality_value)

		sum_seasonality = sum(seasonality)

		if sum_seasonality!=1:
			self.add_error('seasonality_m1','Sum of seasonality factors must be 100%.')


		length_construction = relativedelta(end_construction, start_construction).years

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




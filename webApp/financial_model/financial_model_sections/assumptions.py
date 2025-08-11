import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
import datetime
import calendar
import logging

logger = logging.getLogger(__name__)

class Assumptions:


	ELECTRICITY_PRICES_CHOICES= [
	('1', 'Low'),
	('2', 'Central'),
	('3', 'High'),
	]

	PRODUCTION_CHOICES= [
	('1', 'P90'),
	('2', 'P75'),
	('3', 'P50'),
	]

	ELECTRICITY_PRICES_CHOICES_DICT = dict(ELECTRICITY_PRICES_CHOICES)
	PRODUCTION_CHOICES_DICT = dict(PRODUCTION_CHOICES)

	def __init__(self, instance):
		self.instance = instance


	def initialize(self):
		# Set key project dates
		self._initialize_dates()

		# Define project periods
		self._initialize_periods()

		# Define flags for specific periods
		self._initialize_flags()

		# Process seasonality and construction costs assumptions
		self._initialize_seasonality()
		self._initialize_construction_costs()

		# Calculate tax rates
		self.instance.development_tax_rate = (
			self.instance.project.dev_tax_commune_tax +
			self.instance.project.dev_tax_department_tax
		)

		# Calculate electricity price dictionaries
		self._initialize_electricity_prices()

		# Set debt and financial assumptions
		self._initialize_debt_parameters()

		# Set production, DSRA, and other financial parameters
		self._initialize_production_and_other_parameters()

	def _initialize_dates(self):
		project = self.instance.project
		self.instance.COD = project.end_construction + datetime.timedelta(days=1)
		self.instance.end_of_operations = project.end_construction + relativedelta(years=project.operating_life)
		self.instance.liquidation_date = self.instance.end_of_operations + relativedelta(months=project.liquidation)
		debt_maturity_raw = project.start_construction + relativedelta(months=int(project.debt_tenor * 12) - 1)
		self.instance.debt_maturity = debt_maturity_raw.replace(
			day=calendar.monthrange(debt_maturity_raw.year, debt_maturity_raw.month)[1]
		)





		

	def _initialize_periods(self):
		project = self.instance.project
		self.instance.periods = {
			'contract': {'start': project.start_contract, 'end': project.end_contract},
			'contract_indexation': {'start': project.contract_indexation_start_date, 'end': project.end_contract},
			'merchant_indexation': {'start': project.price_elec_indexation_start_date, 'end': self.instance.end_of_operations},
			'lease_indexation': {'start': project.lease_indexation_start_date, 'end': self.instance.end_of_operations},
			'opex_indexation': {'start': project.opex_indexation_start_date, 'end': self.instance.end_of_operations},
			'debt_interest_construction': {'start': project.start_construction, 'end': project.end_construction},
			'debt_interest_operations': {'start': self.instance.COD, 'end': self.instance.debt_maturity},
			'operations': {'start': self.instance.COD, 'end': self.instance.end_of_operations},
		}

	def _initialize_flags(self):
		self.instance.flag_dict = {
			'construction_start': (self.instance.project.start_construction, self.instance.project.start_construction),
			'construction_end': (self.instance.project.end_construction, self.instance.project.end_construction),
			'construction': (self.instance.project.start_construction, self.instance.project.end_construction),
			'operations': (self.instance.COD, self.instance.end_of_operations),
			'contract': (self.instance.periods['contract']['start'], self.instance.periods['contract']['end']),
			'operations_end': (self.instance.end_of_operations, self.instance.end_of_operations),
			'liquidation': (self.instance.end_of_operations + datetime.timedelta(days=1), self.instance.liquidation_date),
			'liquidation_end': (self.instance.liquidation_date, self.instance.liquidation_date),
			'debt_amo': (self.instance.COD, self.instance.debt_maturity),
			'contract_indexation': (self.instance.periods['contract_indexation']['start'], self.instance.periods['contract']['end']),
			'merchant_indexation': (self.instance.periods['merchant_indexation']['start'], self.instance.end_of_operations),
			'lease_indexation': (self.instance.periods['lease_indexation']['start'], self.instance.end_of_operations),
			'opex_indexation': (self.instance.periods['opex_indexation']['start'], self.instance.end_of_operations),
		}

	def _initialize_seasonality(self):
		self.instance.seasonality_inp = [
			float(getattr(self.instance.project, f'seasonality_m{i}')) for i in range(1, 13)
		]

	def _initialize_construction_costs(self):
		project = self.instance.project
		delta = relativedelta(project.end_construction, project.start_construction)
		months = delta.years * 12 + delta.months + 1
		self.instance.construction_costs_assumptions = [
			float(getattr(project, f'costs_m{i}')) for i in range(1, months + 1)
		]

	def _initialize_electricity_prices(self):
		project = self.instance.project
		self.instance.price_elec_low = self._create_elec_price_dict('price_elec_low_y', project.end_construction, self.instance.liquidation_date)
		self.instance.price_elec_med = self._create_elec_price_dict('price_elec_med_y', project.end_construction, self.instance.liquidation_date)
		self.instance.price_elec_high = self._create_elec_price_dict('price_elec_high_y', project.end_construction, self.instance.liquidation_date)
		self.instance.price_elec_dict = np.array(list(self.instance.price_elec_low.keys()))

	def _create_elec_price_dict(self, prefix, construction_end, liquidation_date):
		years = range(construction_end.year, liquidation_date.year + 1)
		return {
			str(year): float(getattr(self.instance.project, f'{prefix}{i + 1}'))
			for i, year in enumerate(years)
		}

	def _initialize_debt_parameters(self):
		project = self.instance.project
		"""
		debt_components = [
			float(project.debt_margin),
			float(project.debt_swap_rate),
			float(project.debt_swap_margin),
			float(project.debt_reference_rate_buffer),
		]
		"""

		debt_components = float(project.debt_margin)
		self.instance.senior_debt_interest_rate = debt_components / 100
		self.instance.senior_debt_upfront_fee = float(project.debt_upfront_fee) / 100
		self.instance.senior_debt_commitment_fee = float(project.debt_commitment_fee) / 100

	def _initialize_production_and_other_parameters(self):
		project = self.instance.project
		self.instance.target_DSCR = float(project.debt_target_DSCR)
		self.instance.target_gearing = float(project.debt_gearing_max) / 100
		self.instance.dsra = 6 if int(project.DSRA_choice) == 1 else 12
		self.instance.iteration = 50
		self.instance.SHL_margin = float(project.SHL_margin) / 100
		self.instance.p50 = project.p50 / 1000
		self.instance.lender_production = project.production_choice
		self.instance.sponsor_production = project.sponsor_production_choice

		self.instance.lender_production_text = self.PRODUCTION_CHOICES_DICT.get(str(self.instance.lender_production))
		self.instance.sponsor_production_text = self.PRODUCTION_CHOICES_DICT.get(str(self.instance.sponsor_production))

		self.instance.price_elec_choice = project.price_elec_choice
		self.instance.sponsor_price_elec_choice = project.sponsor_price_elec_choice

		self.instance.lender_mkt_price_choice_text = self.ELECTRICITY_PRICES_CHOICES_DICT.get(str(self.instance.price_elec_choice))
		self.instance.sponsor_mkt_price_choice_text = self.ELECTRICITY_PRICES_CHOICES_DICT.get(str(self.instance.sponsor_price_elec_choice))

		self.instance.contract_price = float(project.contract_price)
		self.instance.periodicity = project.periodicity

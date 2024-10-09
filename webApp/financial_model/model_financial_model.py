from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
import datetime
from django.core.exceptions import ValidationError

from django import forms
from datetime import date
import calendar
from dateutil.relativedelta import relativedelta
import pandas as pd
import json
import numpy as np
from decimal import Decimal
from pyxirr import xirr
from dateutil.parser import ParserError
from dateutil import parser
import copy
from collections import defaultdict
from .model_project import Project


from .model_financial_model_helpers import (
	convert_to_list,
	calculate_tenor, 
	divide_with_condition, 
	find_last_payment_date, 
	date_converter, 
	create_IRR_curve,
	find_payback_date,
	calculate_ratio,
	compute_npv,
	determine_debt_constraint,
	calc_dsra_target,
	calc_dsra_funding,

	array_elec_prices,
	create_elec_price_dict,
	create_elec_price_dict_keys,
	format_date,
	calc_production_cumul,
	create_season_series,
	calc_years_from_base_dates,

	get_quarters,
	start_period_series,
	end_period_series,
	model_start_series,

	model_end_series,
	first_day_next_month,
	first_day_month,
	last_day_month,
)


class CustomJSONEncoder(json.JSONEncoder):
	def default(self, obj):

		if isinstance(obj, pd.Series):
			return obj.tolist()
		elif isinstance(obj, pd.Timestamp):
			return obj.strftime('%d/%m/%Y')
		elif isinstance(obj, Decimal):
			return float(obj)
		elif isinstance(obj, np.ndarray):
			return obj.tolist()
		elif isinstance(obj, np.integer):
			return int(obj)
		elif isinstance(obj, np.floating):
			return float(obj)
		elif isinstance(obj, np.bool_):
			return bool(obj)

		return super().default(obj)


class FinancialModel(models.Model):
	project = models.ForeignKey('Project', null=False, on_delete=models.CASCADE)
	financial_model = models.JSONField(default=dict, encoder=CustomJSONEncoder)
	senior_debt_amount = models.FloatField(default=1000.0)
	IRR = models.FloatField(default=10.0)
	identifier = models.CharField(max_length=255, default='default-identifier')
	valuation = models.FloatField(default=1000.0) 

	def update_model(self):
		self.init_static_variables()
		self.init_modifiable_variables()
		self.calc_financial_model()
		self.create_results()
		self.save()

	def init_static_variables(self):
		self.init_assumptions()
		self.init_dates_series()
		self.init_flags()
		self.init_days()
		self.init_time_series()
		self.init_seasonality_series()
		self.init_production()
		self.init_construction_costs_series()
		self.init_indexation_series()
		self.init_opex()

	def init_modifiable_variables(self):
		self.init_price_series()
		self.init_revenues()
		self.init_EBITDA()
		self.init_working_cap()

	def calc_financial_model(self):
		self.converg_variables()
		# Loop until convergence between the target debt amount / debt amount; target debt repayment schedule / debt repayment schedule
		for _ in range(self.iteration):
			self.update_senior_debt_amount_and_repayment()
			self.perform_calculations()

	def perform_calculations(self, with_debt_sizing_sculpting = True):
		self.calc_injections()
		self.calc_senior_debt()
		self.calc_total_uses()
		self.calc_depreciation()
		self.calc_income_statement()
		self.calc_CFS()
		if with_debt_sizing_sculpting:
			self.calc_senior_debt_size()
			self.calc_senior_debt_repayments()
		self.calc_DSRA()
		self.calc_accounts()
		self.calc_convergence_tests()

	def create_results(self):
		self.calc_balance_sheet()
		self.calc_ratios()
		self.calc_irr()
		self.calc_audit()
		self.calc_valuation()
		self.create_dashboard_results()
		self.create_dynamic_sidebar_data()
		self.format_charts_data()


	def init_assumptions(self):
		self.COD = self.project.end_construction + datetime.timedelta(days=1)

		self.end_of_operations = self.project.end_construction + relativedelta(years=self.project.operating_life)
		self.liquidation_date = self.end_of_operations + relativedelta(months=self.project.liquidation)

		self.debt_maturity_date = self.project.start_construction + relativedelta(months=+int(self.project.debt_tenor*12)-1)
		self.debt_maturity = self.debt_maturity_date.replace(day = calendar.monthrange(self.debt_maturity_date.year, self.debt_maturity_date.month)[1])

		self.periods = {
			'contract': {'start': self.project.start_contract, 'end': self.project.end_contract},
			'contract_indexation': {'start': self.project.contract_indexation_start_date, 'end': self.project.end_contract},
			'merchant_indexation': {'start': self.project.price_elec_indexation_start_date, 'end': self.end_of_operations},
			'lease_indexation': {'start': self.project.lease_indexation_start_date, 'end': self.end_of_operations},
			'opex_indexation': {'start': self.project.opex_indexation_start_date, 'end': self.end_of_operations},
			'debt_interest_construction': {'start': self.project.start_construction, 'end': self.project.end_construction},
			'debt_interest_operations': {'start': self.COD, 'end': self.debt_maturity},
			'operations': {'start': self.COD, 'end': self.end_of_operations},
		}

		# Define a dictionary that maps period names to their start and end dates
		self.flag_dict = {
			'construction_start': (self.project.start_construction, self.project.start_construction),
			'construction_end': (self.project.end_construction, self.project.end_construction),
			'construction': (self.project.start_construction, self.project.end_construction),
			'operations': (self.COD, self.end_of_operations),
			'contract': (self.periods['contract']['start'], self.periods['contract']['end']),
			'operations_end': (self.end_of_operations, self.end_of_operations),
			'liquidation': (self.end_of_operations + datetime.timedelta(days=1), self.liquidation_date),
			'liquidation_end': (self.liquidation_date, self.liquidation_date),
			'debt_amo': (self.COD, self.debt_maturity),
			'contract_indexation': (self.periods['contract_indexation']['start'], self.periods['contract']['end']),
			'merchant_indexation': (self.periods['merchant_indexation']['start'], self.end_of_operations),
			'lease_indexation': (self.periods['lease_indexation']['start'], self.end_of_operations),
			'opex_indexation': (self.periods['opex_indexation']['start'], self.end_of_operations),
			}

		self.seasonality_inp = [float(getattr(self.project, f'seasonality_m{i}')) for i in range(1, 13)]	



		self.construction_costs_assumptions = []
		delta = relativedelta(self.project.end_construction, self.project.start_construction)
		months = delta.years * 12 + delta.months + 1
		self.construction_costs_assumptions = [float(getattr(self.project, f'costs_m{i}')) for i in range(1, months + 1)]

		self.development_tax_rate = self.project.dev_tax_commune_tax + self.project.dev_tax_department_tax


		self.price_elec_low = create_elec_price_dict(self, 'price_elec_low_y', self.project.end_construction, self.liquidation_date)
		self.price_elec_med = create_elec_price_dict(self, 'price_elec_med_y', self.project.end_construction, self.liquidation_date)
		self.price_elec_high = create_elec_price_dict(self, 'price_elec_high_y', self.project.end_construction, self.liquidation_date)

		self.price_elec_dict = create_elec_price_dict_keys(self.price_elec_low)


		inp_all_in_interest = np.array([
			float(self.project.debt_margin),
			float(self.project.debt_swap_rate),
			float(self.project.debt_swap_margin),
			float(self.project.debt_reference_rate_buffer),
		])

		self.senior_debt_interest_rate = np.sum(inp_all_in_interest) / 100
		self.senior_debt_upfront_fee = float(self.project.debt_upfront_fee) / 100
		self.senior_debt_commitment_fee = float(self.project.debt_commitment_fee) / 100

		self.target_DSCR =  float(self.project.debt_target_DSCR)
		self.target_gearing =  float(self.project.debt_gearing_max) / 100


		self.dsra = 6 if int(self.project.DSRA_choice) == 1 else 12

		self.iteration = 30

		self.SHL_margin = float(self.project.SHL_margin)/100

		self.valuation_df = float(self.project.discount_factor_valuation)/100
	
		self.p50 = self.project.p50/1000

		self.contract_price = float(self.project.contract_price)

		self.installed_capacity = self.set_capacity()


	def init_dates_series(self):

		self.financial_model['dates'] = {}

		# Create a timeline for the model
		self.financial_model['dates']['model']	= {
				'start': model_start_series(self.project.periodicity, self.project.start_construction, self.project.end_construction, self.liquidation_date),
				'end': model_end_series(self.project.periodicity, self.project.start_construction, self.project.end_construction, self.liquidation_date),
			}

		# Create a timeline for each contract
		for period_name, period_dates in self.periods.items():
			self.financial_model['dates'][period_name] = {
				'start': start_period_series(self.financial_model['dates']['model']['start'], period_dates['start'], period_dates['end']),
				'end': end_period_series(self.financial_model['dates']['model']['end'], period_dates['start'], period_dates['end']),
			}


	def init_flags(self):


		model_end = pd.to_datetime(pd.Series(self.financial_model['dates']['model']['end']), format='%d/%m/%Y', dayfirst=True)
		model_start = pd.to_datetime(pd.Series(self.financial_model['dates']['model']['start']), format='%d/%m/%Y', dayfirst=True)

		# Create a dictionary that contains all the flags for the financial model
		self.financial_model['flags'] = {}
		for name, (start, end) in self.flag_dict.items():
			self.financial_model['flags'][name] = ((model_end >= pd.to_datetime(start)) * (model_start <= pd.to_datetime(end))).astype(int)

		self.financial_model['flags']['start_year'] = (model_start.dt.month == 1) * 1

	def init_days(self):


		self.financial_model['days'] = {}


		days_series_dict = {
		'model': {'flag': 1, 'start_dates': self.financial_model['dates']['model']['start'], 'end_dates': self.financial_model['dates']['model']['end']},
		'contract': {'flag': self.financial_model['flags']['contract'], 'start_dates': self.financial_model['dates']['contract']['start'], 'end_dates': self.financial_model['dates']['contract']['end']},
		'contract_indexation': {'flag': self.financial_model['flags']['contract_indexation'], 'start_dates': self.financial_model['dates']['contract_indexation']['start'], 'end_dates': self.financial_model['dates']['contract_indexation']['end']},
		'merchant_indexation': {'flag': self.financial_model['flags']['merchant_indexation'], 'start_dates': self.financial_model['dates']['merchant_indexation']['start'], 'end_dates': self.financial_model['dates']['merchant_indexation']['end']},
		'opex_indexation': {'flag': self.financial_model['flags']['opex_indexation'], 'start_dates': self.financial_model['dates']['opex_indexation']['start'], 'end_dates': self.financial_model['dates']['opex_indexation']['end']},
		'debt_interest_construction': {'flag': self.financial_model['flags']['construction'], 'start_dates': self.financial_model['dates']['debt_interest_construction']['start'], 'end_dates': self.financial_model['dates']['debt_interest_construction']['end']},
		'debt_interest_operations': {'flag': self.financial_model['flags']['debt_amo'], 'start_dates': self.financial_model['dates']['debt_interest_operations']['start'], 'end_dates': self.financial_model['dates']['debt_interest_operations']['end']},
		'operations': {'flag': self.financial_model['flags']['operations'], 'start_dates': self.financial_model['dates']['operations']['start'], 'end_dates': self.financial_model['dates']['operations']['end']},
		'lease_indexation': {'flag': self.financial_model['flags']['lease_indexation'], 'start_dates': self.financial_model['dates']['lease_indexation']['start'], 'end_dates': self.financial_model['dates']['lease_indexation']['end']},		
		}

		for key, value in days_series_dict.items():
			
			end_dates = pd.to_datetime(pd.Series(value['end_dates']), format='%d/%m/%Y', dayfirst=True)
			start_dates = pd.to_datetime(pd.Series(value['start_dates']), format='%d/%m/%Y', dayfirst=True)	

			self.financial_model['days'][key] = (((end_dates - start_dates).dt.days + 1) * value['flag'])

	def init_time_series(self):


		
		self.financial_model['time_series'] = {}

		self.financial_model['time_series']['days_in_year'] = pd.Series(self.financial_model['dates']['model']['end']).dt.is_leap_year * 366 + (1 - pd.Series(self.financial_model['dates']['model']['end']).dt.is_leap_year) * 365
		self.financial_model['time_series']['years_in_period'] = self.financial_model['days']['model'] / self.financial_model['time_series']['days_in_year']
		self.financial_model['time_series']['years_during_operations'] = self.financial_model['time_series']['years_in_period'] * self.financial_model['flags']['operations']
		self.financial_model['time_series']['quarters'] = get_quarters(self.financial_model['dates']['model']['end'])
		self.financial_model['time_series']['years_from_COD_eop'] = self.financial_model['time_series']['years_during_operations'].cumsum()
		self.financial_model['time_series']['years_from_COD_bop'] = self.financial_model['time_series']['years_from_COD_eop'] - self.financial_model['time_series']['years_during_operations']
		self.financial_model['time_series']['years_from_COD_avg'] = (self.financial_model['time_series']['years_from_COD_eop'] + self.financial_model['time_series']['years_from_COD_bop']) / 2
		self.financial_model['time_series']['series_end_period_year'] = pd.Series(self.financial_model['dates']['model']['end']).dt.year
		self.financial_model['time_series']['pct_in_operations_period'] = pd.Series(self.financial_model['days']['operations']) / pd.Series(self.financial_model['days']['model'])
		self.financial_model['time_series']['years_from_base_dates'] = calc_years_from_base_dates(self.financial_model['days'], self.financial_model['time_series']['days_in_year'])


		self.financial_model['time_series']['pct_in_contract_period'] = pd.Series(np.where(pd.Series(self.financial_model['days']['operations']) > 0, pd.Series(self.financial_model['days']['contract']) / pd.Series(self.financial_model['days']['operations']),0))  


	def init_seasonality_series(self):


		self.financial_model['seasonality'] = {}

		self.financial_model['seasonality'] = create_season_series(self.seasonality_inp, self.financial_model['dates'])

		self.create_capacity_series()

	def init_production(self, sensi_production = 0):


		self.financial_model['production'] = {}
		self.financial_model['production']['total'] = self.project.p90_10y/1000  * pd.Series(self.financial_model['seasonality']) * self.financial_model['capacity']['after_degradation'] * (1 + float(sensi_production))
		self.financial_model['production']['contract'] = self.financial_model['production']['total'] * self.financial_model['time_series']['pct_in_contract_period'] * self.financial_model['time_series']['pct_in_operations_period']
		self.financial_model['production']['contract_cumul_in_year'] = pd.Series(calc_production_cumul(self.financial_model['production']['contract'],self.financial_model['flags']['start_year']))
		"""self.financial_model['production']['capacity_factor'] = pd.Series(np.where(self.financial_model['days']['operations']>0,self.financial_model['production']['total']/((self.installed_capacity*self.financial_model['days']['operations']*24)/1000),0))"""

	def init_construction_costs_series(self):



		self.financial_model['construction_costs'] = {}
		self.financial_model['construction_costs']['total'] = np.hstack([self.construction_costs_assumptions,np.zeros(len(self.financial_model['flags']['operations']) - len(self.construction_costs_assumptions))]) * self.financial_model['flags']['construction']

		self.comp_local_taxes()

	def init_indexation_series(self, sensi_inflation = 0):


		# Create a dictionary to store the mapping between the index names and their corresponding columns
		index_columns = {
			'merchant': 'merchant_indexation',
			'contract': 'contract_indexation',
			'opex': 'opex_indexation',
			'lease': 'lease_indexation'
		}

		self.financial_model['indexation'] = {}

		# Iterate over the dictionary to create the indexation vectors
		for indice_name, column_name in index_columns.items():

			# Create the indexation vector for the current index
			indexation_rate = getattr(self.project, f'index_rate_{indice_name}') + sensi_inflation
			indexation_rate = float(indexation_rate)/100

			indexation_year = pd.Series(self.financial_model['time_series']['years_from_base_dates'][column_name])
			self.financial_model['indexation'][indice_name] = pd.Series((1 + indexation_rate) ** indexation_year).astype(float)


	def init_price_series(self):
		
		self.financial_model['price'] = {}

		self.financial_model['price']['merchant_real'] = pd.Series(array_elec_prices(self.financial_model['time_series']['series_end_period_year'], self.price_elec_low))

		self.financial_model['price']['merchant_nom'] = self.financial_model['price']['merchant_real'] * self.financial_model['indexation']['merchant']

		self.financial_model['price']['contract_real'] = pd.Series(self.contract_price * pd.Series(self.financial_model['flags']['contract'])).astype(float)

		self.financial_model['price']['contract_nom'] = self.financial_model['price']['contract_real'] * self.financial_model['indexation']['contract']


	def init_revenues(self):

		self.financial_model['revenues'] = {}

		self.financial_model['revenues']['contract'] = self.financial_model['production']['total'] * self.financial_model['price']['contract_nom'] / 1000 * self.financial_model['time_series']['pct_in_contract_period'] * self.financial_model['time_series']['pct_in_operations_period']
		self.financial_model['revenues']['merchant'] = self.financial_model['production']['total'] * self.financial_model['price']['merchant_nom'] / 1000 * (1- pd.Series(self.financial_model['time_series']['pct_in_contract_period'])) * self.financial_model['time_series']['pct_in_operations_period']
		self.financial_model['revenues']['total'] = self.financial_model['revenues']['contract'] + self.financial_model['revenues']['merchant']


	def init_opex(self, sensi_opex = 0):

		self.financial_model['opex'] = {}

		self.financial_model['opex']['operating_costs'] = self.project.opex * np.array(self.financial_model['indexation']['opex']) * np.array(self.financial_model['time_series']['years_during_operations']) * (1 + float(sensi_opex))
		self.financial_model['opex']['lease_costs'] = self.project.lease * np.array(self.financial_model['indexation']['lease']) * np.array(self.financial_model['time_series']['years_during_operations']) * (1 + float(sensi_opex))
		self.financial_model['opex']['total'] = self.financial_model['opex']['operating_costs'] + self.financial_model['opex']['lease_costs']
		

	def init_EBITDA(self):

		self.financial_model['EBITDA'] = {}

		self.financial_model['EBITDA']['EBITDA'] = self.financial_model['revenues']['total'] - self.financial_model['opex']['total']
		self.financial_model['EBITDA']['EBITDA_margin'] = np.where(self.financial_model['revenues']['total'] > 0, np.divide(self.financial_model['EBITDA']['EBITDA'], self.financial_model['revenues']['total']), 0)


	def init_working_cap(self):

		self.financial_model['working_cap'] = {}

		self.financial_model['working_cap']['revenues_in_period_paid'] = (1 - self.project.payment_delay_revenues / pd.Series(self.financial_model['days']['model'])) * self.financial_model['revenues']['total']
		self.financial_model['working_cap']['accounts_receivable_eop'] = self.financial_model['revenues']['total'] - self.financial_model['working_cap']['revenues_in_period_paid']
		self.financial_model['working_cap']['accounts_receivable_bop'] = np.roll(self.financial_model['working_cap']['accounts_receivable_eop'], 1)

		self.financial_model['working_cap']['costs_in_period_paid'] = (1 - self.project.payment_delay_costs / pd.Series(self.financial_model['days']['model'])) * self.financial_model['opex']['total']
		self.financial_model['working_cap']['accounts_payable_eop'] = self.financial_model['opex']['total'] - self.financial_model['working_cap']['costs_in_period_paid']
		self.financial_model['working_cap']['accounts_payable_bop'] = np.roll(self.financial_model['working_cap']['accounts_payable_eop'], 1)

		self.financial_model['working_cap']['cashflows_from_creditors'] = np.ediff1d(self.financial_model['working_cap']['accounts_receivable_eop'], to_begin=self.financial_model['working_cap']['accounts_receivable_eop'][0])
		self.financial_model['working_cap']['cashflows_from_debtors'] = np.ediff1d(self.financial_model['working_cap']['accounts_payable_eop'], to_begin=self.financial_model['working_cap']['accounts_payable_eop'][0])
		self.financial_model['working_cap']['working_cap_movement'] = self.financial_model['working_cap']['cashflows_from_debtors'] - self.financial_model['working_cap']['cashflows_from_creditors']
		


	def converg_variables(self):

			data_length = len(self.financial_model['dates']['model']['end'])

			self.optimised_devfee = 0

			self.development_fee = np.full(data_length, 0)

			self.financial_model['uses'] = {}
			self.financial_model['IS'] = {}
			
			self.financial_model['op_account'] = {}
			self.financial_model['SHL'] = {}
			self.financial_model['senior_debt'] = {}
			self.financial_model['CFS'] = {}
			self.financial_model['discount_factor'] = {}
			self.financial_model['BS'] = {}

			self.financial_model['distr_account'] = {}
			self.financial_model['debt_sizing'] = {}
			self.financial_model['share_capital'] = {}
			self.financial_model['audit'] = {}



			self.financial_model['uses']['total'] = self.financial_model['construction_costs']['total'] 
			self.financial_model['uses']['total_cumul'] = self.financial_model['uses']['total'].cumsum()

			self.financial_model['IS']['distributable_profit'] = np.full(data_length, 1)
			


			self.financial_model['SHL']['balance_bop'] = np.full(data_length, 1)
			self.financial_model['SHL']['interests_construction'] = np.full(data_length, 0)
			self.financial_model['SHL']['interests_operations'] = np.full(data_length, 0)
			

			self.financial_model['op_account']['balance_eop'] = np.full(data_length, 0)
				
			
			self.financial_model['DSRA'] = {}
			self.financial_model['DSRA']['dsra_bop'] = np.full(data_length, 0)
			self.financial_model['DSRA']['initial_funding'] = np.full(data_length, 0)
			self.financial_model['DSRA']['dsra_mov'] = np.full(data_length, 0)
			self.initial_funding_max = 0


			self.financial_model['debt_sizing']['target_debt_amount'] = self.financial_model['uses']['total']  * float(self.project.debt_gearing_max) / 100
			self.financial_model['senior_debt']['target_repayments'] = np.full(data_length, 0)


	def update_senior_debt_amount_and_repayment(self):
		self.senior_debt_amount = self.financial_model['debt_sizing']['target_debt_amount']
		self.financial_model['senior_debt']['repayments'] = self.financial_model['senior_debt']['target_repayments']



	def calc_injections(self):
		
		self.financial_model['injections'] = {}

		equity_amount = pd.Series(self.financial_model['uses']['total'])  - self.senior_debt_amount
		self.gearing_eff = (self.senior_debt_amount / pd.Series(self.financial_model['uses']['total']).sum())

		self.subgearing = float(self.project.subgearing)/100

		if self.project.injection_choice == 1:
			senior_debt_drawdowns_cumul = np.clip(pd.Series(self.financial_model['uses']['total_cumul']) * self.gearing_eff, None, self.senior_debt_amount)
			self.financial_model['injections']['senior_debt'] = np.ediff1d(senior_debt_drawdowns_cumul, to_begin=senior_debt_drawdowns_cumul[0])
			self.financial_model['injections']['equity'] = self.financial_model['uses']['total']  - self.financial_model['injections']['senior_debt']
			self.financial_model['injections']['share_capital'] = self.financial_model['injections']['equity'] * (1 - self.subgearing)
			self.financial_model['injections']['SHL'] = self.financial_model['injections']['equity'] * self.subgearing
			self.financial_model['injections']['total'] = self.financial_model['injections']['senior_debt'] + self.financial_model['injections']['equity']

		elif self.project.injection_choice == 2:
			senior_debt_drawdowns_cumul = np.clip(self.financial_model['uses']['total_cumul'] * self.gearing_eff, None, self.senior_debt_amount)
			self.financial_model['injections']['senior_debt'] = np.ediff1d(senior_debt_drawdowns_cumul, to_begin=senior_debt_drawdowns_cumul[0])
			self.financial_model['injections']['equity'] = self.financial_model['uses']['total']  - self.financial_model['injections']['senior_debt']
			self.financial_model['injections']['share_capital'] = self.financial_model['injections']['equity'] * (1 - self.subgearing)
			self.financial_model['injections']['SHL'] = self.financial_model['injections']['equity'] * self.subgearing

			self.financial_model['injections']['total'] = self.financial_model['injections']['senior_debt'] + self.financial_model['injections']['equity']

	def calc_senior_debt(self):

	
		self.financial_model['senior_debt']['balance_eop'] = (self.financial_model['injections']['senior_debt'] - self.financial_model['senior_debt']['repayments']).cumsum()
		self.financial_model['senior_debt']['balance_bop'] = self.financial_model['senior_debt']['balance_eop'] + self.financial_model['senior_debt']['repayments'] - self.financial_model['injections']['senior_debt']

		self.financial_model['senior_debt']['interests_construction'] = self.financial_model['senior_debt']['balance_bop'] * self.senior_debt_interest_rate * self.financial_model['days']['debt_interest_construction'] / 360
		self.financial_model['senior_debt']['interests_operations'] = self.financial_model['senior_debt']['balance_bop'] * self.senior_debt_interest_rate * self.financial_model['days']['debt_interest_operations'] / 360

		self.financial_model['senior_debt']['interests'] = self.financial_model['senior_debt']['interests_construction'] + self.financial_model['senior_debt']['interests_operations']

		self.financial_model['senior_debt']['upfront_fee'] = pd.Series(self.financial_model['flags']['construction_start']) * self.senior_debt_amount * self.senior_debt_upfront_fee

		self.financial_model['senior_debt']['senior_debt_available_eop'] = (self.senior_debt_amount - self.financial_model['senior_debt']['balance_bop']) * self.financial_model['flags']['construction']
		self.financial_model['senior_debt']['senior_debt_available_bop'] = self.financial_model['senior_debt']['senior_debt_available_eop'] + self.financial_model['injections']['senior_debt']

		self.financial_model['senior_debt']['commitment_fees'] = self.financial_model['senior_debt']['senior_debt_available_bop'] * self.senior_debt_commitment_fee * self.financial_model['days']['model']/360


	def calc_total_uses(self):

		"""
		self.capitalised_fees_cumul = (self.financial_model['senior_debt']['senior_debt_idc'] + self.financial_model['senior_debt']['upfront_fee'] + self.financial_model['senior_debt']['commitment_fees'] + self.SHL_interests_construction).cumsum()
		"""
		self.financial_model['uses']['construction'] = self.financial_model['construction_costs']['total']
		self.financial_model['uses']['development_fee'] = 0
		self.financial_model['uses']['senior_debt_idc_and_fees'] = self.financial_model['senior_debt']['interests_construction'] + self.financial_model['senior_debt']['upfront_fee'] + self.financial_model['senior_debt']['commitment_fees']   
		self.financial_model['uses']['reserves'] = self.financial_model['DSRA']['initial_funding']
		self.financial_model['uses']['local_taxes'] = self.financial_model['local_taxes']['total']

		self.financial_model['types'] = {}




		self.financial_model['uses']['total']  = np.array(self.financial_model['uses']['construction']) + np.array(self.financial_model['uses']['development_fee']) + np.array(self.financial_model['uses']['senior_debt_idc_and_fees']) + np.array(self.financial_model['uses']['reserves'])
		"""  """
		"""+ self.financial_model['uses']['local_taxes']"""
		self.financial_model['uses']['total_depreciable'] = np.array(self.financial_model['uses']['construction']) + np.array(self.financial_model['uses']['development_fee']) + np.array(self.financial_model['uses']['senior_debt_idc_and_fees']) + np.array(self.financial_model['SHL']['interests_construction'])
		"""+ self.financial_model['uses']['local_taxes']"""




	def calc_depreciation(self):

		"""self.financial_model['types']['total_depreciable'] = str(self.financial_model['uses']['total_depreciable'].dtype)
		self.financial_model['types']['years_during_operations'] = str(self.financial_model['time_series']['years_during_operations'].dtype)"""


		self.financial_model['IS']['depreciation'] = np.array(self.financial_model['uses']['total_depreciable']).sum() * np.array(self.financial_model['time_series']['years_during_operations']) / self.project.operating_life


	def calc_income_statement(self):


		self.corporate_income_tax_rate = float(self.project.corporate_income_tax)/100

		self.financial_model['IS']['EBIT'] = self.financial_model['EBITDA']['EBITDA'] - self.financial_model['IS']['depreciation']
		self.financial_model['IS']['EBT'] = self.financial_model['IS']['EBIT'] - self.financial_model['senior_debt']['interests_operations'] - self.financial_model['SHL']['interests_operations']
		
		self.financial_model['IS']['corporate_income_tax'] = np.clip(self.corporate_income_tax_rate * self.financial_model['IS']['EBT'], 0, None)
		self.financial_model['IS']['net_income'] = self.financial_model['IS']['EBT'] - self.financial_model['IS']['corporate_income_tax']
	

	def calc_CFS(self):

		self.financial_model['CFS']['cash_flows_operating'] = self.financial_model['EBITDA']['EBITDA'] + self.financial_model['working_cap']['working_cap_movement'] - self.financial_model['IS']['corporate_income_tax']
		self.financial_model['CFS']['cash_flows_investing'] = - (np.array(self.financial_model['uses']['construction']) + np.array(self.financial_model['uses']['development_fee'])) 
		"""+ self.financial_model['uses']['local_taxes']) """


		self.financial_model['CFS']['cash_flows_financing'] = - (self.financial_model['senior_debt']['upfront_fee'] + self.financial_model['senior_debt']['interests_construction'] + self.financial_model['senior_debt']['commitment_fees'] - self.financial_model['injections']['senior_debt'] - self.financial_model['injections']['equity']) 
		self.financial_model['CFS']['CFADS'] = self.financial_model['CFS']['cash_flows_operating'] + self.financial_model['CFS']['cash_flows_investing'] + self.financial_model['CFS']['cash_flows_financing']
		self.financial_model['CFS']['CFADS_amo'] = self.financial_model['CFS']['CFADS'] * self.financial_model['flags']['debt_amo']
		self.financial_model['CFS']['CFADS_operations'] = self.financial_model['CFS']['CFADS'] * self.financial_model['flags']['operations']

	def calc_senior_debt_size(self):
		
		self.financial_model['discount_factor']['avg_interest_rate'] = np.where(self.financial_model['days']['debt_interest_operations'] != 0,np.divide(self.financial_model['senior_debt']['interests_operations'], self.financial_model['senior_debt']['balance_bop'], out=np.zeros_like(self.financial_model['senior_debt']['interests_operations']), where=self.financial_model['senior_debt']['balance_bop'] != 0) / self.financial_model['days']['debt_interest_operations'] * 360,0)	
		self.financial_model['discount_factor']['discount_factor'] = np.where(self.financial_model['flags']['debt_amo'] == 1, (1 / (1 + (self.financial_model['discount_factor']['avg_interest_rate'] * self.financial_model['days']['debt_interest_operations'] / 360))), 1)
		self.financial_model['discount_factor']['discount_factor_cumul'] = self.financial_model['discount_factor']['discount_factor'].cumprod()

		self.financial_model['debt_sizing']['CFADS_amo'] = self.financial_model['CFS']['cash_flows_operating'] * self.financial_model['flags']['debt_amo']
		self.financial_model['debt_sizing']['target_DSCR'] = self.target_DSCR * self.financial_model['flags']['debt_amo']

		self.financial_model['debt_sizing']['target_DS'] = self.financial_model['debt_sizing']['CFADS_amo'] / self.target_DSCR
		self.financial_model['debt_sizing']['target_debt_DSCR'] = sum(self.financial_model['debt_sizing']['target_DS'] * self.financial_model['discount_factor']['discount_factor_cumul'])
		self.financial_model['debt_sizing']['target_debt_gearing'] = self.financial_model['uses']['total'].sum() * self.target_gearing
		self.financial_model['debt_sizing']['target_debt_amount'] = min(self.financial_model['debt_sizing']['target_debt_DSCR'] , self.financial_model['debt_sizing']['target_debt_gearing'])


	def calc_senior_debt_repayments(self):

		senior_debt_drawdowns_sum  = sum(self.financial_model['injections']['senior_debt'])				
		npv_CFADS = sum(self.financial_model['debt_sizing']['CFADS_amo'] * self.financial_model['discount_factor']['discount_factor_cumul'])
		DSCR_sculpting = npv_CFADS / senior_debt_drawdowns_sum if senior_debt_drawdowns_sum > 0 else 1

		self.financial_model['senior_debt']['target_repayments'] = np.maximum(0, np.minimum(self.financial_model['senior_debt']['balance_bop'], self.financial_model['debt_sizing']['CFADS_amo'] / DSCR_sculpting - self.financial_model['senior_debt']['interests_operations']))
		
		self.financial_model['senior_debt']['DS_effective'] = self.financial_model['senior_debt']['repayments'] + self.financial_model['senior_debt']['interests_operations']


	def calc_DSRA(self):

		self.financial_model['DSRA']['cash_available_for_dsra'] = np.maximum(self.financial_model['CFS']['CFADS_amo'] - self.financial_model['senior_debt']['DS_effective'], 0)
		self.financial_model['DSRA']['dsra_target'] = calc_dsra_target(self.dsra, self.project.periodicity, np.array(self.financial_model['senior_debt']['DS_effective'])) * np.array(self.financial_model['flags']['debt_amo'])
		self.financial_model['DSRA']['initial_funding'] = calc_dsra_funding(np.array(self.financial_model['DSRA']['dsra_target'])) * np.array(self.financial_model['flags']['construction_end'])
		self.financial_model['DSRA']['dsra_additions_available'] = np.minimum(self.financial_model['DSRA']['cash_available_for_dsra'], self.financial_model['DSRA']['dsra_target'])
		self.financial_model['DSRA']['dsra_additions_required'] = np.maximum(self.financial_model['DSRA']['dsra_target'] - self.financial_model['DSRA']['dsra_bop'], 0)
		self.financial_model['DSRA']['dsra_additions_required_available'] = np.minimum(self.financial_model['DSRA']['dsra_additions_available'], self.financial_model['DSRA']['dsra_additions_required'])
		self.financial_model['DSRA']['dsra_target'] = self.financial_model['DSRA']['dsra_target'] + self.financial_model['DSRA']['initial_funding']
		self.financial_model['DSRA']['dsra_eop'] = np.clip((self.financial_model['DSRA']['initial_funding'] + self.financial_model['DSRA']['dsra_additions_required_available']).cumsum(), 0, self.financial_model['DSRA']['dsra_target'])
		self.financial_model['DSRA']['dsra_eop_mov'] = np.ediff1d(self.financial_model['DSRA']['dsra_eop'], to_begin=self.financial_model['DSRA']['dsra_eop'][0])
		self.financial_model['DSRA']['dsra_additions'] = np.maximum(self.financial_model['DSRA']['dsra_eop_mov'], 0)
		self.financial_model['DSRA']['dsra_release'] = np.minimum(self.financial_model['DSRA']['dsra_eop_mov'], 0)
		self.financial_model['DSRA']['dsra_bop'] = np.roll(self.financial_model['DSRA']['dsra_eop'], 1)
		self.financial_model['DSRA']['dsra_mov'] =(self.financial_model['DSRA']['dsra_eop'] - self.financial_model['DSRA']['dsra_bop'])

		self.initial_funding_max = max(self.financial_model['DSRA']['initial_funding'])




	def calc_accounts(self):

		self.financial_model['distr_account']['cash_available_for_distribution'] = (self.financial_model['CFS']['CFADS'] - self.financial_model['senior_debt']['DS_effective'] - self.financial_model['DSRA']['dsra_mov'] - self.project.cash_min * np.array(self.financial_model['flags']['operations']))
		self.financial_model['distr_account']['transfers_distribution_account'] = self.financial_model['distr_account']['cash_available_for_distribution'].clip(lower=0)

		self.financial_model['op_account']['balance_eop'] = self.financial_model['distr_account']['cash_available_for_distribution']  - self.financial_model['distr_account']['transfers_distribution_account']

		"""
		+ initial_funding 
		"""
		
		self.financial_model['op_account']['balance_eop'] = np.roll(self.financial_model['op_account']['balance_eop'], 1)


		for i in range(self.iteration):
		
			self.financial_model['SHL']['interests_operations'] = np.array(self.financial_model['SHL']['balance_bop']) * self.SHL_margin * self.financial_model['days']['model'] / 360 * self.financial_model['flags']['operations']
			self.financial_model['SHL']['interests_construction'] = np.array(self.financial_model['SHL']['balance_bop']) * self.SHL_margin * self.financial_model['days']['model'] / 360 * self.financial_model['flags']['construction']

			self.financial_model['SHL']['interests_paid'] = np.minimum(self.financial_model['distr_account']['transfers_distribution_account'], self.financial_model['SHL']['interests_operations'])
			self.financial_model['distr_account']['cash_available_for_dividends'] = self.financial_model['distr_account']['transfers_distribution_account'] - self.financial_model['SHL']['interests_paid']
			self.financial_model['distr_account']['dividends_paid']  = np.minimum(self.financial_model['distr_account']['cash_available_for_dividends'], self.financial_model['IS']['distributable_profit'])
			
			self.financial_model['distr_account']['cash_available_for_SHL_repayments']  = self.financial_model['distr_account']['cash_available_for_dividends'] - self.financial_model['distr_account']['dividends_paid']
			self.financial_model['SHL']['repayments']  = np.minimum(self.financial_model['SHL']['balance_bop'], self.financial_model['distr_account']['cash_available_for_SHL_repayments'])
			
			self.financial_model['distr_account']['cash_available_for_redemption'] = self.financial_model['distr_account']['cash_available_for_SHL_repayments'] - self.financial_model['SHL']['repayments']

			self.financial_model['distr_account']['balance_eop'] = (self.financial_model['distr_account']['transfers_distribution_account'] - self.financial_model['SHL']['interests_paid'] - self.financial_model['distr_account']['dividends_paid'] - self.financial_model['SHL']['repayments']).cumsum()
			self.financial_model['distr_account']['balance_bop'] = self.financial_model['distr_account']['balance_eop'] - (self.financial_model['distr_account']['transfers_distribution_account'] - self.financial_model['SHL']['interests_paid'] - self.financial_model['distr_account']['dividends_paid'] - self.financial_model['SHL']['repayments'])
			
			self.financial_model['SHL']['balance_eop'] = (self.financial_model['injections']['SHL'] + self.financial_model['SHL']['interests_construction'] - self.financial_model['SHL']['repayments']).cumsum()
			self.financial_model['SHL']['balance_bop'] = self.financial_model['SHL']['balance_eop'] - (self.financial_model['injections']['SHL'] + self.financial_model['SHL']['interests_construction'] - self.financial_model['SHL']['repayments'])
			
			self.financial_model['IS']['retained_earnings_eop'] = (self.financial_model['IS']['net_income'] - self.financial_model['distr_account']['dividends_paid']).cumsum()
			self.financial_model['IS']['retained_earnings_bop'] = self.financial_model['IS']['retained_earnings_eop'] - (self.financial_model['IS']['net_income'] - self.financial_model['distr_account']['dividends_paid'])
			self.financial_model['IS']['distributable_profit'] = np.clip(self.financial_model['IS']['retained_earnings_bop'] + self.financial_model['IS']['net_income'], 0, None)

			self.financial_model['share_capital']['repayments'] = self.financial_model['distr_account']['balance_bop'] * self.financial_model['flags']['liquidation_end']
			self.financial_model['distr_account']['balance_eop'] = self.financial_model['distr_account']['balance_eop'] - self.financial_model['share_capital']['repayments']

			self.financial_model['share_capital']['balance_eop'] = (self.financial_model['injections']['share_capital'] - self.financial_model['share_capital']['repayments']).cumsum()
			self.financial_model['share_capital']['balance_bop'] = self.financial_model['share_capital']['balance_eop'] - (self.financial_model['injections']['share_capital'] - self.financial_model['share_capital']['repayments'])


	def calc_convergence_tests(self):

		debt_amount_not_converged = abs(self.senior_debt_amount - self.financial_model['debt_sizing']['target_debt_amount']) > 0.1
		difference = np.array(self.financial_model['senior_debt']['target_repayments']) - np.array(self.financial_model['senior_debt']['repayments'])
		debt_sculpting_not_converged = np.where(difference == 0, True, False)
		self.debt_sculpting_not_converged = np.any(np.logical_not(debt_sculpting_not_converged))
		 
		 
	def calc_balance_sheet(self):
		
		self.financial_model['BS']['PPE'] = ( 
			np.array(self.financial_model['construction_costs']['total']).cumsum() + 
			self.financial_model['uses']['senior_debt_idc_and_fees'].cumsum() + 
			self.financial_model['SHL']['interests_construction'].cumsum()	-
			self.financial_model['IS']['depreciation'].cumsum()

		)
		"""	self.financial_model['local_taxes']['total'].cumsum() +"""

		self.financial_model['BS']['total_assets'] = (
			self.financial_model['BS']['PPE'] + 
			self.financial_model['working_cap']['accounts_receivable_eop'] + 
			self.financial_model['DSRA']['dsra_eop'] + 
			self.financial_model['distr_account']['balance_eop'] + 
			self.financial_model['op_account']['balance_eop']
		)

		self.financial_model['BS']['total_liabilities'] = (
			self.financial_model['SHL']['balance_eop'] + 
			self.financial_model['share_capital']['balance_eop'] + 
			self.financial_model['IS']['retained_earnings_eop'] + 
			self.financial_model['senior_debt']['balance_eop'] + 
			self.financial_model['working_cap']['accounts_payable_eop']
		)


	def calc_ratios(self):
		self.financial_model['ratios'] = {}
		


		self.financial_model['ratios']['DSCR_effective'] = np.divide(np.array(self.financial_model['CFS']['CFADS_amo']), np.array(self.financial_model['senior_debt']['DS_effective']), out = np.zeros_like(np.array(self.financial_model['CFS']['CFADS_amo'])), where = np.array(self.financial_model['senior_debt']['DS_effective']) != 0)

		

		self.financial_model['ratios']['LLCR'] = calculate_ratio(np.array(self.financial_model['discount_factor']['avg_interest_rate']), self.financial_model['debt_sizing']['CFADS_amo'], self.financial_model['senior_debt']['balance_eop'], self.financial_model['dates']['model']['end'])

		self.financial_model['ratios']['PLCR'] = calculate_ratio(np.array(self.financial_model['discount_factor']['avg_interest_rate']), self.financial_model['CFS']['CFADS'], self.financial_model['senior_debt']['balance_eop'], self.financial_model['dates']['model']['end'])

		self.DSCR_avg = np.array(self.financial_model['ratios']['DSCR_effective'][np.array(self.financial_model['flags']['debt_amo']) == 1]).mean()
		self.DSCR_min = np.array(self.financial_model['ratios']['DSCR_effective'][np.array(self.financial_model['flags']['debt_amo']) == 1]).min()

		mask = (np.array(self.financial_model['flags']['debt_amo']) == 1)
		indices = np.where(mask)[0]
		indices_without_last = indices[:-1]

		self.LLCR_min = np.array(self.financial_model['ratios']['LLCR'][indices_without_last]).min()



	def calc_irr(self):

		self.financial_model['IRR'] = {}


		share_capital_cf = -self.financial_model['injections']['share_capital'] + self.financial_model['distr_account']['dividends_paid'] + self.financial_model['share_capital']['repayments']
		SHL_cf = -self.financial_model['injections']['SHL'] + self.financial_model['SHL']['interests_operations'] + self.financial_model['SHL']['repayments']
		self.equity_cf = share_capital_cf + SHL_cf
		equity_cf_cumul = self.equity_cf.cumsum()


		self.financial_model['IRR']['equity'] = xirr(pd.Series(pd.to_datetime(self.financial_model['dates']['model']['end'], dayfirst=True)).dt.date, self.equity_cf)
		self.IRR = self.financial_model['IRR']['equity'] * 100
		self.financial_model['IRR']['share_capital'] = xirr(pd.Series(pd.to_datetime(self.financial_model['dates']['model']['end'], dayfirst=True)).dt.date, share_capital_cf)
		self.financial_model['IRR']['SHL'] = xirr(pd.Series(pd.to_datetime(self.financial_model['dates']['model']['end'], dayfirst=True)).dt.date, SHL_cf)
	 
		project_cf_pre_tax = -self.financial_model['uses']['total'] + self.financial_model['EBITDA']['EBITDA']
		project_cf_post_tax = project_cf_pre_tax + self.financial_model['IS']['corporate_income_tax']
		
		self.financial_model['IRR']['project_pre_tax'] = xirr(pd.Series(pd.to_datetime(self.financial_model['dates']['model']['end'], dayfirst=True)).dt.date, project_cf_pre_tax)
		self.financial_model['IRR']['project_post_tax'] = xirr(pd.Series(pd.to_datetime(self.financial_model['dates']['model']['end'], dayfirst=True)).dt.date, project_cf_post_tax)

		debt_cash_flows = -self.financial_model['injections']['senior_debt'] + self.financial_model['senior_debt']['repayments'] + self.financial_model['senior_debt']['interests'] + self.financial_model['senior_debt']['upfront_fee'] + self.financial_model['senior_debt']['commitment_fees']
		self.financial_model['IRR']['senior_debt'] = xirr(pd.Series(pd.to_datetime(self.financial_model['dates']['model']['end'], dayfirst=True)).dt.date, debt_cash_flows)
		
		self.financial_model['IRR']['irr_curve'] = create_IRR_curve(self.equity_cf, self.financial_model['dates']['model']['end'])

		payback_date = find_payback_date(pd.Series(self.financial_model['dates']['model']['end']), equity_cf_cumul)

		try:
			payback_date = parser.parse(str(payback_date)).date()
			time_difference = payback_date - self.project.start_construction
			self.payback_time = round(time_difference.days / 365.25, 1)
			self.payback_date = payback_date.strftime("%d/%m/%Y")
		except ParserError:
			self.payback_date = "error"
			self.payback_time = "error"


		self.debt_constraint = determine_debt_constraint(self.financial_model['debt_sizing']['target_debt_DSCR'], self.financial_model['debt_sizing']['target_debt_gearing'])
		self.financial_model['gearing_during_finplan'] = self.financial_model['injections']['senior_debt'].cumsum()/(self.financial_model['injections']['equity'].cumsum()+self.financial_model['injections']['senior_debt'].cumsum())


	def calc_audit(self):

		self.financial_model['audit'] = {}

		self.financial_model['audit']['financing_plan'] = self.financial_model['uses']['total'] - self.financial_model['injections']['total']
		self.financial_model['audit']['balance_sheet'] = self.financial_model['BS']['total_assets'] - self.financial_model['BS']['total_liabilities']

		self.check_financing_plan = abs(sum(self.financial_model['uses']['total'] - self.financial_model['injections']['total'])) < 0.01
		self.check_balance_sheet = abs(sum(self.financial_model['BS']['total_assets'] - self.financial_model['BS']['total_liabilities'])) < 0.01

		final_repayment_date_debt = find_last_payment_date(self.financial_model['dates']['model']['end'], self.financial_model['senior_debt']['balance_bop'])
		final_repayment_date_debt = pd.to_datetime(final_repayment_date_debt, dayfirst=True).strftime("%Y-%m-%d %H:%M:%S")
		final_repayment_date_debt = parser.parse(final_repayment_date_debt).date()	


		self.tenor_debt = calculate_tenor(final_repayment_date_debt, self.project.start_construction)


		"""if self.senior_debt_amount > 0:
			self.average_debt_life = sum(x * y for x, y in zip(self.financial_model['time_series']['years_in_period'], self.financial_model['senior_debt']['balance_bop'])) / self.senior_debt_amount
			self.average_debt_life = round(self.average_debt_life,1)
		else:
			self.average_debt_life="""	



		self.financial_model['audit']['debt_maturity'] = (final_repayment_date_debt == self.debt_maturity)

		self.check_all = all([self.check_financing_plan, self.check_balance_sheet, self.financial_model['audit']['debt_maturity']]) 


	def format_charts_data(self):

		self.financial_model['charts'] = {}

		self.financial_model['charts']['senior_debt_draw_neg'] = - self.financial_model['injections']['senior_debt']
		self.financial_model['charts']['share_capital_inj_neg'] = - self.financial_model['injections']['share_capital']
		self.financial_model['charts']['shl_draw_neg'] = - self.financial_model['injections']['SHL']
		self.financial_model['charts']['share_capital_inj_and_repay'] = - self.financial_model['injections']['share_capital'] + self.financial_model['share_capital']['repayments']
		self.financial_model['charts']['shl_inj_and_repay'] = - self.financial_model['injections']['SHL'] + self.financial_model['SHL']['repayments']





	def calc_valuation(self):

		end_period = pd.Series(pd.to_datetime(self.financial_model['dates']['model']['end'], dayfirst=True))
		current_date = pd.Timestamp(datetime.datetime.now().date())
		time_since_today = end_period.apply(lambda date: (current_date - date).days)
		time_since_today = time_since_today.clip(lower=0)

		self.eqt_discount_factor = self.valuation_df
		self.eqt_discount_factor_less_1 = self.valuation_df-0.01
		self.eqt_discount_factor_plus_1 = self.valuation_df+0.01

		discount_factor_vector = np.where(time_since_today != 0, (1 / (1 + self.eqt_discount_factor)**(time_since_today/365)), 1)
		discount_factor_less_1_vector = np.where(time_since_today != 0, (1 / (1 + self.eqt_discount_factor_less_1)**(time_since_today/365)), 1)
		discount_factor_plus_1_vector = np.where(time_since_today != 0, (1 / (1 + self.eqt_discount_factor_plus_1)**(time_since_today/365)), 1)

		self.valuation = np.sum(self.equity_cf*discount_factor_vector)
		self.valuation_less_1 = np.sum(self.equity_cf*discount_factor_less_1_vector)
		self.valuation_plus_1 = np.sum(self.equity_cf*discount_factor_plus_1_vector)




	def apply_sensitivity(self, sensitivity_type):
		# Apply the sensitivity to the copy of the Base Case financial model
		if sensitivity_type == 'sensi_production':
			self.init_production(sensi_production = self.project.sensi_production/100)
		
		elif sensitivity_type == 'sensi_inflation':
			self.init_indexation_series(sensi_inflation = self.project.sensi_inflation/100)
		
		elif sensitivity_type == 'sensi_opex':
			self.init_opex(sensi_opex = self.project.sensi_opex/100)
		
		elif sensitivity_type == 'sponsor_production_choice':
			self.financial_model['production']['total'] = self.project.p90_10y/1000 * pd.Series(self.financial_model['seasonality']) * self.financial_model['capacity']['after_degradation']
		
		else:
			pass
		
		self.save()


	def recalc_financial_model(self):
		# Rerun the methods on which the sensititiy had an impact and recompute the financial model
		"""self.init_modifiable_variables()"""
		"""self.perform_calculations(with_debt_sizing_sculpting=False)
		self.create_results()"""
		

		self.init_assumptions()
		self.init_price_series()
		self.init_revenues()
		self.init_EBITDA()
		self.init_working_cap()
		self.perform_calculations(with_debt_sizing_sculpting=False)
		self.create_results()

		self.save()


	def save(self, *args, **kwargs):
		# Automatically convert types to lists in financial_model
		self.financial_model = convert_to_list(self.financial_model)
		super().save(*args, **kwargs)


	def __deepcopy__(self, memo):
		# Create a new instance of this class
		new_instance = self.__class__.__new__(self.__class__)

		# Copy all attributes from self to copied_instance
		memo[id(self)] = new_instance

		# Iterate over all attributes in self.__dict__
		for key, value in self.__dict__.items():
			# Deep copy each attribute, ensuring COD is copied as it is
			setattr(new_instance, key, copy.deepcopy(value, memo))

		return new_instance
	
	def extract_construction_values_for_charts(self):
		# Get the list of flags from the data
		flags = self.financial_model['flags']['construction']

		# List of paths to extract values from
		data_paths = {
			'dates_model_end': self.financial_model['dates']['model']['end'],
			'construction_costs_total': self.financial_model['construction_costs']['total'],
			'uses_total_cumul': self.financial_model['uses']['total_cumul'],
			'uses_senior_debt_idc_and_fees': self.financial_model['uses']['senior_debt_idc_and_fees'],
			'DSRA_initial_funding': self.financial_model['DSRA']['initial_funding'],
			'charts_share_capital_inj_neg': self.financial_model['charts']['share_capital_inj_neg'],
			'charts_shl_draw_neg': self.financial_model['charts']['shl_draw_neg'],
			'charts_senior_debt_draw_neg': self.financial_model['charts']['senior_debt_draw_neg'],
			'uses_total': self.financial_model['uses']['total'],
			'gearing_during_finplan': self.financial_model['gearing_during_finplan'],
		}

		# Initialize a dictionary to store extracted values
		extracted_values = {}

		for path_key, data in data_paths.items():
			# Ensure data is a list and filter it based on flags
			filtered_data = [data[i] for i in range(len(flags)) if flags[i] == 1]
			extracted_values[path_key] = filtered_data

		return extracted_values

	def extract_EoY_values_for_charts(self):
		# Define the keys that need processing
		required_keys = {
			'senior_debt': ['balance_eop', 'DS_effective'],
			'distr_account': ['balance_eop'],
			'IRR': ['irr_curve'],
			'ratios': ['DSCR_effective', 'LLCR', 'PLCR'],
			'IS': ['retained_earnings_bop'],
			'DSRA': ['dsra_bop'],
		}

		# Function to process each series for December 31st values
		def process_series(series, end_dates):
			values = defaultdict(float)
			for i, end_date in enumerate(end_dates):
				if i < len(series):
					# Check if the date is December 31st
					if end_date.day == 31 and end_date.month == 12:
						value = series[i]
						value = float(value) if isinstance(value, (int, float)) else 0.0
						values[end_date.year] = value
			return values

		# Start processing from the top level
		value_eoy = defaultdict(lambda: defaultdict(float))

		# Convert period end series to datetime
		period_end_series = pd.to_datetime(self.financial_model['dates']['model']['end'], format='%d/%m/%Y', dayfirst=True)

		# Iterate over required keys and their sub-keys
		for key, sub_keys in required_keys.items():
			for sub_key in sub_keys:
				# Check if key and sub_key exist in the financial model
				if key in self.financial_model and sub_key in self.financial_model[key]:
					series = self.financial_model[key][sub_key]

					# Process the series and store results in value_eoy
					value_eoy[key][sub_key] = process_series(series, period_end_series)

		# Convert defaultdict to a regular dictionary for output
		return dict(value_eoy)

	def calc_annual_sum_for_charts(self):
		# Define the keys that need processing
		required_keys = {
			'opex': ['total', 'lease_costs'],
			'revenues': ['contract', 'merchant'],
			'senior_debt': ['DS_effective', 'interests_operations', 'repayments'],
			'charts': ['share_capital_inj_and_repay', 'shl_inj_and_repay'],
			'distr_account': ['dividends_paid'],
			'IRR': ['irr_curve'],
			'ratios': ['DSCR_effective', 'LLCR', 'PLCR'],
			'injections': ['senior_debt'],
			'share_capital': ['repayments']
		}

		# Function to process each series and accumulate values by year
		def process_series(series, end_dates):
			values = defaultdict(float)
			for i, end_date in enumerate(end_dates):
				if i < len(series):
					value = series[i]
					value = float(value) if isinstance(value, (int, float)) else 0.0
					values[end_date.year] += value
			return values

		# Start processing from the top level
		year_sum = defaultdict(lambda: defaultdict(float))

		# Convert period end series to datetime
		period_end_series = pd.to_datetime(self.financial_model['dates']['model']['end'], format='%d/%m/%Y', dayfirst=True)

		# Iterate over required keys and their sub-keys
		for key, sub_keys in required_keys.items():

			for sub_key in sub_keys:
				# Check if key and sub_key exist in the financial model
				if key in self.financial_model and sub_key in self.financial_model[key]:
					series = self.financial_model[key][sub_key]
					
					# Process the series and store results in year_sum
					year_sum[key][sub_key] = process_series(series, period_end_series)

		# Convert defaultdict to regular dictionary for output
		return dict(year_sum)

	def create_dynamic_sidebar_data(self):

		self.financial_model['dict_sidebar'] = {
			'COD': date_converter(self.COD),
			'installed_capacity': self.installed_capacity,
			'end_of_operations': date_converter(self.end_of_operations),
			'sum_seasonality': f"{round((sum(self.seasonality_inp) * 100), 2)}%",
			'sum_construction_costs': sum(self.construction_costs_assumptions),
			'liquidation': date_converter(self.liquidation_date),
			'date_debt_maturity': date_converter(self.debt_maturity),
			'price_elec_dict': self.price_elec_dict,
		}



	def create_dashboard_results(self):

		self.financial_model['dict_uses_sources'] = {
			"Uses": {
				"Construction costs": sum(self.financial_model['construction_costs']['total']),
				"Development fee": 0,
				"Debt interests & fees": sum(self.financial_model['uses']['senior_debt_idc_and_fees']),
				"Upfront fee": sum(self.financial_model['senior_debt']['upfront_fee']),
				"Commitment fees": sum(self.financial_model['senior_debt']['commitment_fees']),
				"IDC": sum(self.financial_model['senior_debt']['interests_construction']),
				"Local taxes": sum(self.financial_model['local_taxes']['total']),
				"Development tax": sum(self.financial_model['local_taxes']['development_tax']),
				"Archeological tax": sum(self.financial_model['local_taxes']['archeological_tax']),
				"Initial DSRA funding": sum(self.financial_model['DSRA']['initial_funding']),
				"Total": sum(self.financial_model['uses']['total']),
			},
			"Sources": {
				"Equity": sum(self.financial_model['injections']['equity']),
				"Share capital": sum(self.financial_model['injections']['share_capital']),
				"Shareholder loan": sum(self.financial_model['injections']['SHL']),
				"Senior debt": sum(self.financial_model['injections']['senior_debt']),
				"Total": sum(self.financial_model['injections']['total']),
			},
		}



		self.financial_model['dict_results'] = {
			"Equity metrics": {
				"Share capital IRR": self.financial_model['IRR']['share_capital'],
				"Shareholder loan IRR": self.financial_model['IRR']['SHL'],
				"Equity IRR": self.financial_model['IRR']['equity'],
				"Payback date": self.payback_date, 
				"Payback time": self.payback_time, 
			},
			"Sensi": {
				"Min DSCR": self.DSCR_min,
				"Avg. DSCR": self.DSCR_avg,
				"Min LLCR": self.LLCR_min ,
				"Equity IRR": self.financial_model['IRR']['equity'],
				"Audit": self.check_all,
			},
			"Project IRR": {
				"Project IRR (pre-tax)": self.financial_model['IRR']['project_pre_tax'],
				"Project IRR (post-tax)": self.financial_model['IRR']['project_post_tax'],
			},
			"Debt metrics": {
				"Debt amount": self.senior_debt_amount,
				"Constraint": self.debt_constraint,
				"Effective gearing": self.gearing_eff,
				"Tenor (door-to-door)": self.tenor_debt,
				"Average DSCR": self.DSCR_avg,
				"Debt IRR": self.financial_model['IRR']['senior_debt'],
			},
			"Audit": {
				"Financing plan": self.check_financing_plan,
				"Balance sheet": self.check_balance_sheet,
				"Debt maturity": self.financial_model['audit']['debt_maturity'],
			},
			"Valuation": {
				f"{self.eqt_discount_factor_less_1 * 100:.2f}%": self.valuation_less_1,
				f"{self.eqt_discount_factor * 100:.2f}%": self.valuation,				
				f"{self.eqt_discount_factor_plus_1 * 100:.2f}%": self.valuation_plus_1,
			},

		}

		"""				"Average life": self.average_debt_life,


		"""















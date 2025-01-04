import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
import datetime
import calendar


class FinancialModelAssumptions:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):

		self.instance.COD = self.instance.project.end_construction + datetime.timedelta(days=1)
		self.instance.end_of_operations = self.instance.project.end_construction + relativedelta(years=self.instance.project.operating_life)
		self.instance.liquidation_date = self.instance.end_of_operations + relativedelta(months=self.instance.project.liquidation)

		self.instance.debt_maturity_date = self.instance.project.start_construction + relativedelta(months=+int(self.instance.project.debt_tenor*12)-1)
		self.instance.debt_maturity = self.instance.debt_maturity_date.replace(day = calendar.monthrange(self.instance.debt_maturity_date.year, self.instance.debt_maturity_date.month)[1])

		self.instance.periods = {
			'contract': {'start': self.instance.project.start_contract, 'end': self.instance.project.end_contract},
			'contract_indexation': {'start': self.instance.project.contract_indexation_start_date, 'end': self.instance.project.end_contract},
			'merchant_indexation': {'start': self.instance.project.price_elec_indexation_start_date, 'end': self.instance.end_of_operations},
			'lease_indexation': {'start': self.instance.project.lease_indexation_start_date, 'end': self.instance.end_of_operations},
			'opex_indexation': {'start': self.instance.project.opex_indexation_start_date, 'end': self.instance.end_of_operations},
			'debt_interest_construction': {'start': self.instance.project.start_construction, 'end': self.instance.project.end_construction},
			'debt_interest_operations': {'start': self.instance.COD, 'end': self.instance.debt_maturity},
			'operations': {'start': self.instance.COD, 'end': self.instance.end_of_operations},
		}

		# Define a dictionary that maps period names to their start and end dates
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

		self.instance.seasonality_inp = [float(getattr(self.instance.project, f'seasonality_m{i}')) for i in range(1, 13)]	

		self.instance.construction_costs_assumptions = []
		delta = relativedelta(self.instance.project.end_construction, self.instance.project.start_construction)
		months = delta.years * 12 + delta.months + 1
		self.instance.construction_costs_assumptions = [float(getattr(self.instance.project, f'costs_m{i}')) for i in range(1, months + 1)]

		self.instance.development_tax_rate = self.instance.project.dev_tax_commune_tax + self.instance.project.dev_tax_department_tax

		self.instance.price_elec_low = create_elec_price_dict(self, 'price_elec_low_y', self.instance.project.end_construction, self.instance.liquidation_date)
		self.instance.price_elec_med = create_elec_price_dict(self, 'price_elec_med_y', self.instance.project.end_construction, self.instance.liquidation_date)
		self.instance.price_elec_high = create_elec_price_dict(self, 'price_elec_high_y', self.instance.project.end_construction, self.instance.liquidation_date)

		self.instance.price_elec_dict = create_elec_price_dict_keys(self.instance.price_elec_low)

		inp_all_in_interest = np.array([
			float(self.instance.project.debt_margin),
			float(self.instance.project.debt_swap_rate),
			float(self.instance.project.debt_swap_margin),
			float(self.instance.project.debt_reference_rate_buffer),
		])

		self.instance.senior_debt_interest_rate = np.sum(inp_all_in_interest) / 100
		self.instance.senior_debt_upfront_fee = float(self.instance.project.debt_upfront_fee) / 100
		self.instance.senior_debt_commitment_fee = float(self.instance.project.debt_commitment_fee) / 100

		self.instance.target_DSCR =  float(self.instance.project.debt_target_DSCR)
		self.instance.target_gearing =  float(self.instance.project.debt_gearing_max) / 100

		self.instance.dsra = 6 if int(self.instance.project.DSRA_choice) == 1 else 12

		self.instance.iteration = 30

		self.instance.SHL_margin = float(self.instance.project.SHL_margin)/100
	
		self.instance.p50 = self.instance.project.p50/1000

		self.instance.contract_price = float(self.instance.project.contract_price)
		self.instance.periodicity = self.instance.project.periodicity
		self.instance.sensi_production = float(self.instance.project.periodicity)/100


def create_elec_price_dict(self, prefix, construction_end, liquidation_date):
	
	construction_end_year = construction_end.year
	liquidation_date_year = liquidation_date.year

	years = [str(year) for year in range(construction_end_year, liquidation_date_year+1)]

	dic_price_elec = {}

	for i, year in enumerate(years):
		key = f'{prefix}{i+1}'
		value = float(getattr(self.instance.project, key))
		dic_price_elec[year] = value

	return dic_price_elec



def create_elec_price_dict_keys(dic_price_elec):
	dic_price_elec_keys = np.array(list(dic_price_elec.keys()))
	return dic_price_elec_keys

import pandas as pd
import numpy as np


class FinancialModelTimes:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):

		self.instance.financial_model['time_series'] = {}

		self.instance.financial_model['time_series']['days_in_year'] = pd.Series(self.instance.financial_model['dates']['model']['end']).dt.is_leap_year * 366 + (1 - pd.Series(self.instance.financial_model['dates']['model']['end']).dt.is_leap_year) * 365
		self.instance.financial_model['time_series']['years_in_period'] = self.instance.financial_model['days']['model'] / self.instance.financial_model['time_series']['days_in_year']
		self.instance.financial_model['time_series']['years_during_operations'] = self.instance.financial_model['time_series']['years_in_period'] * self.instance.financial_model['flags']['operations']
		self.instance.financial_model['time_series']['quarters'] = get_quarters(self.instance.financial_model['dates']['model']['end'])
		self.instance.financial_model['time_series']['years_from_COD_eop'] = self.instance.financial_model['time_series']['years_during_operations'].cumsum()
		self.instance.financial_model['time_series']['years_from_COD_bop'] = self.instance.financial_model['time_series']['years_from_COD_eop'] - self.instance.financial_model['time_series']['years_during_operations']
		self.instance.financial_model['time_series']['years_from_COD_avg'] = (self.instance.financial_model['time_series']['years_from_COD_eop'] + self.instance.financial_model['time_series']['years_from_COD_bop']) / 2
		self.instance.financial_model['time_series']['series_end_period_year'] = pd.Series(self.instance.financial_model['dates']['model']['end']).dt.year
		self.instance.financial_model['time_series']['pct_in_operations_period'] = pd.Series(self.instance.financial_model['days']['operations']) / pd.Series(self.instance.financial_model['days']['model'])
		self.instance.financial_model['time_series']['years_from_base_dates'] = calc_years_from_base_dates(self.instance.financial_model['days'], self.instance.financial_model['time_series']['days_in_year'])

		self.instance.financial_model['time_series']['pct_in_contract_period'] = pd.Series(np.where(pd.Series(self.instance.financial_model['days']['operations']) > 0, pd.Series(self.instance.financial_model['days']['contract']) / pd.Series(self.instance.financial_model['days']['operations']), 0))



def get_quarters(date_list):
	date_series = pd.Series(date_list)
	quarters = pd.to_datetime(date_series, format='%Y-%m-%d').dt.quarter
	return quarters


def calc_years_from_base_dates(days_series, days_in_year):
	
	keys = ['contract_indexation', 'merchant_indexation', 'opex_indexation', 'lease_indexation']
	
	years_from_base_dates = {}
	for key in keys:
		years = (days_series[key] / days_in_year).cumsum()
		years_from_base_dates[key] = years

	return years_from_base_dates



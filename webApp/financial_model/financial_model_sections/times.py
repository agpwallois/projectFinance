import pandas as pd
import numpy as np

import logging

logger = logging.getLogger(__name__)


class Times:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self):
		self._initialize_time_series()
		self._calculate_days_in_year()
		self._calculate_years_in_period()
		self._calculate_years_during_operations()
		self._calculate_quarters()
		self._calculate_years_from_cod()
		self._calculate_series_end_period_year()
		self._calculate_pct_in_operations_period()
		self._calculate_years_from_base_dates()
		self._calculate_pct_in_contract_period()
		self._calculate_year_allocations()

	def _initialize_time_series(self):
		"""Ensure the 'time_series' section exists."""
		if 'time_series' not in self.financial_model:
			self.financial_model['time_series'] = {}

	def _calculate_days_in_year(self):
		"""Calculate the number of days in each year."""
		dates_end = pd.Series(self.financial_model['dates']['model']['end'])
		is_leap_year = dates_end.dt.is_leap_year
		days_in_year = is_leap_year * 366 + (~is_leap_year) * 365
		# Ensure int64 dtype for consistency
		self.financial_model['time_series']['days_in_year'] = days_in_year.astype('int64')

	def _calculate_years_in_period(self):
		"""Calculate the number of years in each period."""
		days_model = self.financial_model['days']['model']
		days_in_year = self.financial_model['time_series']['days_in_year']
		# Use np.where to handle division by zero
		self.financial_model['time_series']['years_in_period'] = np.where(
			days_in_year != 0,
			days_model / days_in_year,
			0
		)

	def _calculate_years_during_operations(self):
		"""Calculate the number of years during operations."""
		years_in_period = self.financial_model['time_series']['years_in_period']
		flags_operations = self.financial_model['flags']['operations']
		self.financial_model['time_series']['years_during_operations'] = years_in_period * flags_operations

	def _calculate_quarters(self):
		"""Calculate the quarter of each period."""
		dates_end = self.financial_model['dates']['model']['end']
		self.financial_model['time_series']['quarters'] = get_quarters(dates_end)

	def _calculate_years_from_cod(self):
		"""Calculate years from COD (start and end)."""
		years_during_operations = self.financial_model['time_series']['years_during_operations']
		self.financial_model['time_series']['years_from_COD_eop'] = years_during_operations.cumsum()
		self.financial_model['time_series']['years_from_COD_bop'] = (
			self.financial_model['time_series']['years_from_COD_eop'] - years_during_operations
		)
		self.financial_model['time_series']['years_from_COD_avg'] = (
			self.financial_model['time_series']['years_from_COD_eop'] +
			self.financial_model['time_series']['years_from_COD_bop']
		) / 2

	def _calculate_series_end_period_year(self):
		"""Calculate the year of the end period for each series."""
		dates_end = pd.Series(self.financial_model['dates']['model']['end'])
		self.financial_model['time_series']['series_end_period_year'] = dates_end.dt.year

	def _calculate_pct_in_operations_period(self):
		"""Calculate the percentage of days in the operations period."""
		days_operations = pd.Series(self.financial_model['days']['operations'])
		days_model = pd.Series(self.financial_model['days']['model'])
		# Handle division by zero
		self.financial_model['time_series']['pct_in_operations_period'] = np.where(
			days_model != 0,
			days_operations / days_model,
			0
		)

	def _calculate_years_from_base_dates(self):
		"""Calculate years from base dates for specific keys."""
		days_series = self.financial_model['days']
		days_in_year = self.financial_model['time_series']['days_in_year']
		self.financial_model['time_series']['years_from_base_dates'] = calc_years_from_base_dates(
			days_series, days_in_year
		)

	def _calculate_pct_in_contract_period(self):
		"""Calculate the percentage of days in the contract period."""
		days_operations = pd.Series(self.financial_model['days']['operations'])
		days_contract = pd.Series(self.financial_model['days']['contract'])
		self.financial_model['time_series']['pct_in_contract_period'] = np.where(
			days_operations > 0,
			days_contract / days_operations,
			0
		)
	
	def _calculate_year_allocations(self):
		"""
		Calculate the percentage allocation of each period across calendar years.
		This is used to properly allocate financial flows when periods span multiple years.
		"""
		if 'year_boundaries' not in self.financial_model['dates']:
			# If year boundaries haven't been calculated, skip this
			return
		
		year_boundaries = self.financial_model['dates']['year_boundaries']
		days_per_year = year_boundaries['days_per_year']
		
		# Calculate percentage allocations for each period
		year_allocations = []
		
		for period_days in days_per_year:
			# Calculate total days in the period
			total_days = sum(period_days.values())
			
			# Calculate percentage for each year
			if total_days > 0:
				year_percentages = {
					year: days / total_days 
					for year, days in period_days.items()
				}
			else:
				year_percentages = {}
			
			year_allocations.append(year_percentages)
		
		# Store the allocations
		self.financial_model['time_series']['year_allocations'] = year_allocations
		self.financial_model['time_series']['years_spanned'] = year_boundaries['years_spanned']
		self.financial_model['time_series']['days_per_year'] = days_per_year
	
		"""logger.error(self.financial_model['time_series']['year_allocations'])"""

def get_quarters(date_list):
	"""Return the quarter for each date in the list."""
	date_series = pd.Series(date_list)
	return pd.to_datetime(date_series, format='%Y-%m-%d').dt.quarter


def calc_years_from_base_dates(days_series, days_in_year):
	"""Calculate cumulative years from base dates for specific keys."""
	keys = ['contract_indexation', 'merchant_indexation', 'opex_indexation', 'lease_indexation']
	years_from_base_dates = {}

	for key in keys:
		years = days_series[key] / days_in_year
		years_from_base_dates[key] = years.cumsum()

	return years_from_base_dates

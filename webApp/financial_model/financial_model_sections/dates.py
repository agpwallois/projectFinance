import math
import calendar
import datetime
import logging
from typing import Dict, Any

import pandas as pd
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class Dates:
	"""
	A class responsible for initializing and managing the date ranges
	used in a financial model. It calculates start/end dates for both
	construction and operation periods, as well as per-period timelines.
	"""

	def __init__(self, instance: Any) -> None:
		"""
		Initialize the Dates with the main project instance.

		Args:
			instance: Main object containing project data, periods, and
					 the financial_model dictionary to be updated.
		"""
		self.instance = instance

	def initialize(self) -> None:
		"""
		Initializes the financial model's date ranges by:
			1. Creating model-wide start/end date ranges.
			2. Creating per-period start/end date ranges.
			3. Creating year boundaries for each period.
		"""
		self.instance.financial_model['dates'] = {}

		# Initialize model-wide date ranges
		model_dates = self._initialize_model_dates()
		self.instance.financial_model['dates']['model'] = model_dates

		# Initialize dates for each named period
		for period_name, period_dates in self.instance.periods.items():
			self.instance.financial_model['dates'][period_name] = self._initialize_period_dates(
				model_dates['start'],
				model_dates['end'],
				period_dates
			)
		
		# Calculate year boundaries for each period
		self.instance.financial_model['dates']['year_boundaries'] = self._calculate_year_boundaries(
			model_dates['start'],
			model_dates['end']
		)

		"""logger.error(self.instance.financial_model['dates']['year_boundaries'])"""

	def _initialize_model_dates(self) -> Dict[str, pd.Series]:
		"""
		Initializes the model-wide start and end dates.

		Returns:
			A dictionary containing two pd.Series: 'start' and 'end'.
		"""
		return {
			'start': self._calculate_model_start_dates(
				self.instance.project.periodicity,
				self.instance.project.start_construction,
				self.instance.project.end_construction,
				self.instance.liquidation_date
			),
			'end': self._calculate_model_end_dates(
				self.instance.project.periodicity,
				self.instance.project.start_construction,
				self.instance.project.end_construction,
				self.instance.liquidation_date
			),
		}

	def _initialize_period_dates(
		self,
		model_start_dates: pd.Series,
		model_end_dates: pd.Series,
		period_dates: Dict[str, str]
	) -> Dict[str, pd.Series]:
		"""
		Initializes the start and end dates for a specific period by filtering
		the global model dates to the period’s date window.

		Args:
			model_start_dates: Global model start dates (pd.Series).
			model_end_dates: Global model end dates (pd.Series).
			period_dates: Dict containing 'start' and 'end' as strings.

		Returns:
			A dictionary with 'start' and 'end' pd.Series for the period.
		"""
		return {
			'start': self._filter_dates(model_start_dates, period_dates['start'], period_dates['end']),
			'end': self._filter_dates(model_end_dates, period_dates['start'], period_dates['end']),
		}

	def _calculate_model_start_dates(
		self,
		periodicity: int,
		construction_start: datetime.date,
		construction_end: datetime.date,
		liquidation_date: datetime.date
	) -> pd.Series:
		"""Calculate start dates matching the end dates exactly"""
		
		# Start exactly at construction_start, not first of month
		first_construction_period_start = construction_start
		construction_end_month = self._first_day_of_month(construction_end)
		
		# First period starts at construction_start
		construction_start_dates = [pd.Timestamp(first_construction_period_start)]
		
		# Subsequent construction periods start on the 1st of each month
		current_month = self._first_day_of_month(construction_start) + relativedelta(months=1)
		while current_month <= construction_end_month:
			construction_start_dates.append(pd.Timestamp(current_month))
			current_month = current_month + relativedelta(months=1)
		
		construction_start_dates = pd.Series(construction_start_dates)
		
		# Operations start immediately after construction
		first_operations_start = construction_end + datetime.timedelta(days=1)
		
		# Calculate minimum first operations end date (must be AFTER construction_end + periodicity)
		min_first_operations_end = construction_end + relativedelta(months=periodicity)
		
		if periodicity == 6:  # Semi-annual
			year = min_first_operations_end.year
			month = min_first_operations_end.month
			
			# Find the next semi-annual end (30/06 or 31/12) that's AFTER min_first_operations_end
			if month <= 6:
				first_ops_end = datetime.date(year, 6, 30)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year, 12, 31)
			else:
				first_ops_end = datetime.date(year, 12, 31)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year + 1, 6, 30)
			
			# Generate all operations start dates
			operations_start_dates = [first_operations_start]
			
			# Add subsequent semi-annual starts
			current_end = first_ops_end
			while current_end < liquidation_date:
				# Next start is day after current end
				next_start = current_end + datetime.timedelta(days=1)
				if next_start <= liquidation_date:
					operations_start_dates.append(next_start)
				
				# Move to next semi-annual end
				if current_end.month == 6:
					current_end = datetime.date(current_end.year, 12, 31)
				else:
					current_end = datetime.date(current_end.year + 1, 6, 30)
			
			operations_start_dates = pd.Series([pd.Timestamp(d) for d in operations_start_dates])
		
		elif periodicity == 3:  # Quarterly
			year = min_first_operations_end.year
			month = min_first_operations_end.month
			
			# Find the next quarterly end (31/03, 30/06, 30/09, 31/12) that's AFTER min_first_operations_end
			if month <= 3:
				first_ops_end = datetime.date(year, 3, 31)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year, 6, 30)
			elif month <= 6:
				first_ops_end = datetime.date(year, 6, 30)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year, 9, 30)
			elif month <= 9:
				first_ops_end = datetime.date(year, 9, 30)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year, 12, 31)
			else:
				first_ops_end = datetime.date(year, 12, 31)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year + 1, 3, 31)
			
			# Generate all operations start dates
			operations_start_dates = [first_operations_start]
			
			# Add subsequent quarterly starts
			current_end = first_ops_end
			while current_end < liquidation_date:
				# Next start is day after current end
				next_start = current_end + datetime.timedelta(days=1)
				if next_start <= liquidation_date:
					operations_start_dates.append(next_start)
				
				# Move to next quarterly end
				if current_end.month == 3:
					current_end = datetime.date(current_end.year, 6, 30)
				elif current_end.month == 6:
					current_end = datetime.date(current_end.year, 9, 30)
				elif current_end.month == 9:
					current_end = datetime.date(current_end.year, 12, 31)
				else:  # December
					current_end = datetime.date(current_end.year + 1, 3, 31)
			
			operations_start_dates = pd.Series([pd.Timestamp(d) for d in operations_start_dates])
		
		else:
			operations_start_dates = pd.Series([], dtype='datetime64[ns]')
		
		# Combine: construction + operations (no separate transition)
		all_start_dates = pd.concat([
			pd.Series(construction_start_dates), 
			operations_start_dates
		])
		
		"""logger.error(f"Start dates: {all_start_dates.reset_index(drop=True)}")"""
		return all_start_dates.reset_index(drop=True)


	def _calculate_model_end_dates(
		self,
		periodicity: int,
		construction_start: datetime.date,
		construction_end: datetime.date,
		liquidation_date: datetime.date
	) -> pd.Series:
		"""Calculate end dates matching the start dates exactly"""
		
		# Build construction end dates
		construction_end_dates = []
		
		# First period ends at the last day of construction_start's month
		first_period_end = self._last_day_of_month(construction_start)
		construction_end_dates.append(first_period_end)
		
		# Subsequent periods end at month-end until we reach construction_end
		current_date = self._first_day_of_month(construction_start) + relativedelta(months=1)
		construction_end_month = self._first_day_of_month(construction_end)
		
		while current_date < construction_end_month:
			month_end = self._last_day_of_month(current_date)
			construction_end_dates.append(month_end)
			current_date = current_date + relativedelta(months=1)
		
		# Final construction period ends exactly at construction_end
		if construction_end_month.month == construction_end.month and construction_end_month.year == construction_end.year:
			construction_end_dates.append(construction_end)
		
		construction_end_dates = pd.Series([pd.Timestamp(d) for d in construction_end_dates])
		
		# Calculate minimum first operations end date
		min_first_operations_end = construction_end + relativedelta(months=periodicity)
		
		if periodicity == 6:  # Semi-annual
			year = min_first_operations_end.year
			month = min_first_operations_end.month
			
			if month <= 6:
				first_ops_end = datetime.date(year, 6, 30)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year, 12, 31)
			else:
				first_ops_end = datetime.date(year, 12, 31)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year + 1, 6, 30)
			
			# Generate all operations end dates
			operations_end_dates = []
			current_end = first_ops_end
			
			while current_end <= liquidation_date:
				if current_end < liquidation_date:
					operations_end_dates.append(current_end)
				else:
					# Last period ends on liquidation date
					operations_end_dates.append(liquidation_date)
					break
				
				# Move to next semi-annual end
				if current_end.month == 6:
					next_end = datetime.date(current_end.year, 12, 31)
				else:
					next_end = datetime.date(current_end.year + 1, 6, 30)
				
				# Check if we've reached or passed liquidation
				if next_end >= liquidation_date:
					operations_end_dates.append(liquidation_date)
					break
				else:
					current_end = next_end
			
			operations_end_dates = pd.Series([pd.Timestamp(d) for d in operations_end_dates])
		
		elif periodicity == 3:  # Quarterly
			year = min_first_operations_end.year
			month = min_first_operations_end.month
			
			if month <= 3:
				first_ops_end = datetime.date(year, 3, 31)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year, 6, 30)
			elif month <= 6:
				first_ops_end = datetime.date(year, 6, 30)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year, 9, 30)
			elif month <= 9:
				first_ops_end = datetime.date(year, 9, 30)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year, 12, 31)
			else:
				first_ops_end = datetime.date(year, 12, 31)
				if first_ops_end <= min_first_operations_end:
					first_ops_end = datetime.date(year + 1, 3, 31)
			
			# Generate all operations end dates
			operations_end_dates = []
			current_end = first_ops_end
			
			while current_end <= liquidation_date:
				if current_end < liquidation_date:
					operations_end_dates.append(current_end)
				else:
					# Last period ends on liquidation date
					operations_end_dates.append(liquidation_date)
					break
				
				# Move to next quarterly end
				if current_end.month == 3:
					next_end = datetime.date(current_end.year, 6, 30)
				elif current_end.month == 6:
					next_end = datetime.date(current_end.year, 9, 30)
				elif current_end.month == 9:
					next_end = datetime.date(current_end.year, 12, 31)
				else:  # December
					next_end = datetime.date(current_end.year + 1, 3, 31)
				
				# Check if we've reached or passed liquidation
				if next_end >= liquidation_date:
					operations_end_dates.append(liquidation_date)
					break
				else:
					current_end = next_end
			
			operations_end_dates = pd.Series([pd.Timestamp(d) for d in operations_end_dates])
		
		else:
			operations_end_dates = pd.Series([], dtype='datetime64[ns]')
		
		# Combine: construction + operations
		all_end_dates = pd.concat([
			construction_end_dates, 
			operations_end_dates
		])
		
		"""logger.error(f"End dates: {all_end_dates.reset_index(drop=True)}")"""
		return all_end_dates.reset_index(drop=True)


	def _first_day_of_next_month(self, date: datetime.date, periodicity: int) -> datetime.date:
		"""
		Calculates the first day of the next month after a specified date,
		adjusted by the given periodicity.

		Args:
			date: The base date from which to calculate.
			periodicity: The frequency in months by which to move.

		Returns:
			A datetime.date object representing the first day of the target month,
			minus 1 day (per the original logic).
		"""
		return (date.replace(day=1)
				+ relativedelta(months=periodicity)
				+ datetime.timedelta(days=-1))

	@staticmethod
	def _first_day_of_month(date: datetime.date) -> datetime.date:
		"""
		Returns the first day of the month for a given date.
		"""
		return date.replace(day=1)

	@staticmethod
	def _last_day_of_month(date: datetime.date) -> datetime.date:
		"""
		Returns the last day of the month for a given date.
		"""
		day = calendar.monthrange(date.year, date.month)[1]
		return date.replace(day=day)

	@staticmethod
	def _filter_dates(
		timeline_list: pd.Series,
		start_date: str,
		end_date: str
	) -> pd.Series:
		"""
		Clips a list (pd.Series) of dates to be within a specified start and end date.

		Args:
			timeline_list: The original list (or Series) of dates.
			start_date: The lower bound (inclusive) of the clip range as a string.
			end_date: The upper bound (inclusive) of the clip range as a string.

		Returns:
			A pd.Series where all dates are clipped to be within [start_date, end_date].
		"""
		timeline_series = pd.to_datetime(pd.Series(timeline_list), dayfirst=True)
		return timeline_series.clip(lower=pd.Timestamp(start_date), upper=pd.Timestamp(end_date))
	
	def _calculate_year_boundaries(self, start_dates: pd.Series, end_dates: pd.Series) -> Dict[str, list]:
		"""
		Calculate year boundaries for each period to identify which calendar years each period spans.
		
		Args:
			start_dates: Series of period start dates
			end_dates: Series of period end dates
			
		Returns:
			Dictionary containing:
			- 'years_spanned': List of lists, each containing the years a period spans
			- 'days_per_year': List of dicts, each mapping year to days in that year for the period
		"""
		years_spanned = []
		days_per_year = []
		
		for i in range(len(start_dates)):
			start = pd.Timestamp(start_dates.iloc[i])
			end = pd.Timestamp(end_dates.iloc[i])
			
			# Find all years this period spans
			period_years = list(range(start.year, end.year + 1))
			years_spanned.append(period_years)
			
			# Calculate days in each year for this period
			period_days = {}
			for year in period_years:
				# Year boundaries
				year_start = pd.Timestamp(year, 1, 1)
				year_end = pd.Timestamp(year, 12, 31)
				
				# Clip period to year boundaries
				period_start_in_year = max(start, year_start)
				period_end_in_year = min(end, year_end)
				
				# Calculate days (inclusive)
				days = (period_end_in_year - period_start_in_year).days + 1
				period_days[year] = days
			
			days_per_year.append(period_days)
		
		return {
			'years_spanned': years_spanned,
			'days_per_year': days_per_year
		}

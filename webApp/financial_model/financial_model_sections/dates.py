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
		"""
		Calculates the start dates for the financial model. This includes:
		- A monthly range from construction start to construction end (freq='MS').
		- A single date right after construction, plus a repeated range up to liquidation.

		Args:
			periodicity: Integer representing the frequency (in months) for operations.
			construction_start: Date when construction starts.
			construction_end: Date when construction ends.
			liquidation_date: Date when liquidation occurs.

		Returns:
			A pd.Series of datetime64[ns] containing all start dates.
		"""
		months_to_add = math.floor(periodicity / 3)
		frequency_string = f"{periodicity}MS"

		first_day_construction = self._first_day_of_month(construction_start)
		last_day_construction = self._last_day_of_month(construction_end)

		# Date used to figure out the next operational period
		first_operations_end = (
			last_day_construction + datetime.timedelta(days=1)
			+ relativedelta(months=months_to_add)
			+ pd.tseries.offsets.QuarterEnd() * months_to_add
		)

		# Single date right after construction
		first_operations_date = pd.Series([pd.Timestamp(last_day_construction + datetime.timedelta(days=1))])
		second_operations_date = first_operations_end + datetime.timedelta(days=1)

		last_day_liquidation = self._last_day_of_month(liquidation_date)

		# Construct date ranges
		construction_range = pd.date_range(first_day_construction, last_day_construction, freq='MS')
		operations_range = pd.date_range(second_operations_date, last_day_liquidation, freq=frequency_string)

		all_start_dates = pd.concat([pd.Series(construction_range), first_operations_date, pd.Series(operations_range)])
		return all_start_dates.reset_index(drop=True)

	def _calculate_model_end_dates(
		self,
		periodicity: int,
		construction_start: datetime.date,
		construction_end: datetime.date,
		liquidation_date: datetime.date
	) -> pd.Series:
		"""
		Calculates the end dates for the financial model. This includes:
		- A monthly range for the construction phase (freq='M').
		- A range from the first operational period up to a date that accounts
		  for the specified periodicity beyond liquidation.

		Args:
			periodicity: Integer representing the frequency (in months) for operations.
			construction_start: Date when construction starts.
			construction_end: Date when construction ends.
			liquidation_date: Date when liquidation occurs.

		Returns:
			A pd.Series of datetime64[ns] containing all end dates.
		"""
		months_to_add = math.floor(periodicity / 3)
		frequency_string = f"{periodicity}M"

		first_day_construction = self._first_day_of_month(construction_start)
		last_day_construction = self._last_day_of_month(construction_end)

		# The end of the first operational period
		first_operations_end = (
			last_day_construction + datetime.timedelta(days=1)
			+ relativedelta(months=months_to_add)
			+ pd.tseries.offsets.QuarterEnd() * months_to_add
		)

		# Determine how far we extend beyond liquidation based on periodicity
		last_day_liquidation_plus_freq = self._first_day_of_next_month(liquidation_date, periodicity)

		end_construction_dates = pd.date_range(first_day_construction, last_day_construction, freq='M')
		end_operations_dates = pd.date_range(first_operations_end, last_day_liquidation_plus_freq, freq=frequency_string)

		all_end_dates = pd.concat([pd.Series(end_construction_dates), pd.Series(end_operations_dates)])
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

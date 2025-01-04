import math
import calendar
import datetime
from dateutil.relativedelta import relativedelta
import pandas as pd


class FinancialModelDates:
	def __init__(self, instance):
		self.instance = instance


	def initialize(self):
		self.instance.financial_model['dates'] = {}

		model_dates = self._initialize_model_dates()
		self.instance.financial_model['dates']['model'] = model_dates

		# Initialize dates for each period
		for period_name, period_dates in self.instance.periods.items():
			self.instance.financial_model['dates'][period_name] = self._initialize_period_dates(
				model_dates['start'], model_dates['end'], period_dates
			)

	def _initialize_model_dates(self):
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

	def _initialize_period_dates(self, model_start_dates, model_end_dates, period_dates):
		return {
			'start': self._filter_dates(model_start_dates, period_dates['start'], period_dates['end']),
			'end': self._filter_dates(model_end_dates, period_dates['start'], period_dates['end']),
		}

	def _calculate_model_start_dates(self, periodicity, construction_start, construction_end, liquidation_date):
		"""Calculates the start dates for the financial model."""
		months_to_add = math.floor(int(periodicity) / 3)
		frequency_string = str(periodicity) + "MS"

		first_day_construction_start = self._first_day_of_month(construction_start)
		last_day_construction_end = self._last_day_of_month(construction_end)
		first_operations_end_date = last_day_construction_end + datetime.timedelta(days=1) + relativedelta(
			months=+months_to_add) + pd.tseries.offsets.QuarterEnd() * months_to_add

		first_operations_date = last_day_construction_end + datetime.timedelta(days=1)
		first_operations_date = pd.Timestamp(first_operations_date)
		first_operations_date = pd.Series(first_operations_date)
		second_operations_date = first_operations_end_date + datetime.timedelta(days=1)
		last_day_liquidation_end = self._last_day_of_month(liquidation_date)
		start_construction_dates = pd.Series(
			pd.date_range(first_day_construction_start, last_day_construction_end, freq='MS'))
		start_operations_dates = pd.Series(
			pd.date_range(second_operations_date, last_day_liquidation_end, freq=frequency_string))
		all_start_dates = pd.concat(
			[start_construction_dates, first_operations_date, start_operations_dates],
			ignore_index=True)

		return all_start_dates

	def _calculate_model_end_dates(self, periodicity, construction_start, construction_end, liquidation_date):
		"""Calculates the end dates for the financial model."""
		months_to_add = math.floor(int(periodicity) / 3)
		frequency_string = str(periodicity) + "M"

		first_day_construction_start = self._first_day_of_month(construction_start)
		last_day_construction_end = self._last_day_of_month(construction_end)
		first_operations_end_date = last_day_construction_end + datetime.timedelta(days=1) + relativedelta(
			months=+months_to_add) + pd.tseries.offsets.QuarterEnd() * months_to_add

		last_day_liquidation_plus_freq = self._first_day_of_next_month(liquidation_date, periodicity)
		end_operations_dates = pd.Series(
			pd.date_range(first_operations_end_date, last_day_liquidation_plus_freq, freq=frequency_string))
		end_construction_dates = pd.Series(
			pd.date_range(first_day_construction_start, last_day_construction_end, freq='M'))
		all_end_dates = pd.concat([end_construction_dates, end_operations_dates], ignore_index=True)

		return all_end_dates

	def _filter_dates(self, date_series, start_date, end_date):
		"""Filters a series of dates based on a start and end date."""
		return self._clip_dates(date_series, start_date, end_date)

	def _first_day_of_next_month(self, date, periodicity):
		"""Calculates the first day of the next month after a specified date."""
		first_day_next_month = date.replace(day=1) + relativedelta(months=int(periodicity)) + datetime.timedelta(days=-1)
		return first_day_next_month

	def _first_day_of_month(self, date):
		"""Returns the first day of the month for a given date."""
		return date.replace(day=1)

	def _last_day_of_month(self, date):
		"""Returns the last day of the month for a given date."""
		last_day = date.replace(day=calendar.monthrange(date.year, date.month)[1])
		return last_day

	def _clip_dates(self, timeline_list, start_date, end_date):
		"""Clips a list of dates to be within a specified start and end date."""
		# Convert the timeline list to a pandas Series of Timestamps with specified date format
		timeline_series = pd.to_datetime(pd.Series(timeline_list), format='%d/%m/%Y', dayfirst=True)

		# Use the clip method to restrict the dates to the specified range
		clipped_timeline = timeline_series.clip(lower=pd.Timestamp(start_date), upper=pd.Timestamp(end_date))

		return clipped_timeline
import pandas as pd
import calendar
import numpy as np
from typing import Dict, List, Optional


class FinancialModelProduction:
	def __init__(self, instance):
		self.instance = instance
		

	def initialize(self, model_type: str, sensi_production: float = 0) -> None:
		"""
		Initialize the financial model with production metrics.
		
		Args:
			model_type: Type of model ('lender' or other)
			sensi_production: Production sensitivity factor
		"""
		self._initialize_capacity()
		self._initialize_seasonality()
		self._initialize_production(model_type, sensi_production)
		
	def _initialize_capacity(self) -> None:
		"""Initialize capacity series."""
		# Store the capacity data from instance into our financial model
		self.instance.create_capacity_series()
		self.instance.financial_model['capacity'] = self.instance.financial_model.get('capacity', {})
		
		# Ensure after_degradation exists
		if 'after_degradation' not in self.instance.financial_model['capacity']:
			raise ValueError("Capacity series is missing 'after_degradation' data. Please ensure create_capacity_series() properly initializes this value.")
		
	def _initialize_seasonality(self) -> None:
		"""Initialize seasonality series based on input and dates."""

		self.instance.financial_model['seasonality'] = {}
		self.instance.financial_model['seasonality'] = SeasonalityCalculator.create_season_series(
			self.instance.seasonality_inp,
			self.instance.financial_model['dates']
		)
		
	def _initialize_production(self, model_type: str, sensi_production: float) -> None:
		"""Initialize production metrics."""
		production_mapping = {
			1: self.instance.project.p90_10y,
			2: self.instance.project.p75,
			3: self.instance.project.p50
		}
		
		choice = (self.instance.project.production_choice 
				 if model_type not in {'sponsor', 'sensi_production_sponsor', 'sensi_inflation_sponsor', 'sensi_opex_sponsor'} 
				 else self.instance.project.sponsor_production_choice)
		
		production_volume = production_mapping.get(choice, self.instance.project.p90_10y) / 1000
		
		self._calculate_total_production(production_volume, sensi_production)
		self._calculate_contract_production()
		self._calculate_cumulative_production()
		
	def _calculate_total_production(self, production_volume: float, sensi_production: float) -> None:
		"""Calculate total production based on various factors."""
		if 'after_degradation' not in self.instance.financial_model['capacity']:
			raise ValueError("Missing capacity degradation data. Please initialize capacity first.")
			
		self.instance.financial_model['production'] = {}

		self.instance.financial_model['production']['total'] = (
			production_volume
			* pd.Series(self.instance.financial_model['seasonality'])
			* self.instance.financial_model['capacity']['after_degradation']
			* (1 + float(sensi_production))
		)
		
	def _calculate_contract_production(self) -> None:
		"""Calculate contract production."""
		self.instance.financial_model['production']['contract'] = (
			self.instance.financial_model['production']['total']
			* self.instance.financial_model['time_series']['pct_in_contract_period']
			* self.instance.financial_model['time_series']['pct_in_operations_period']
		)
		
	def _calculate_cumulative_production(self) -> None:
		"""Calculate cumulative production within a year."""
		self.instance.financial_model['production']['contract_cumul_in_year'] = pd.Series(
			ProductionCalculator.calculate_cumulative_production(
				self.instance.financial_model['production']['contract'],
				self.instance.financial_model['flags']['start_year']
			)
		)

		# Uncomment and complete if capacity factor calculation is needed
		# self.financial_model['production']['capacity_factor'] = pd.Series(
		#     np.where(
		#         self.financial_model['days']['operations'] > 0,
		#         self.financial_model['production']['total'] / (
		#             (self.installed_capacity * self.financial_model['days']['operations'] * 24) / 1000
		#         ),
		#         0
		#     )
		# )


class SeasonalityCalculator:
	@staticmethod
	def create_season_series(seasonality: pd.Series, dates_series: Dict) -> List[float]:
		"""
		Create seasonality series based on dates and seasonality input.
		
		Args:
			seasonality: Seasonality factors
			dates_series: Dictionary containing start and end dates
			
		Returns:
			List of seasonality factors for each period
		"""
		data = {
			'start': dates_series['model']['start'],
			'end': dates_series['model']['end']
		}
		df = pd.DataFrame(data)
		df_seasonality_result = pd.DataFrame(columns=dates_series['model']['end'])
		
		for index, row in df.iterrows():
			dates_in_period = pd.date_range(
				start=row['start'],
				end=row['end']
			).values.astype('datetime64[D]').tolist()
			
			for month in range(1, 13):
				days_in_month = SeasonalityCalculator._calculate_days_in_month(
					dates_in_period, month)
				df_seasonality_result.loc[month, row['end']] = days_in_month
				
		df_seasonality_result = df_seasonality_result.mul(seasonality, axis=0)
		return df_seasonality_result.sum(axis=0).values.tolist()
	
	@staticmethod
	def _calculate_days_in_month(dates_in_period: List, month: int) -> float:
		"""Calculate the proportion of days in a given month."""
		count = sum(1 for value in dates_in_period if value.month == month)
		if not count:
			return 0
		
		total_days = calendar.monthrange(dates_in_period[0].year, month)[1]
		return count / total_days



class ProductionCalculator:
	@staticmethod
	def calculate_cumulative_production(
		production: np.ndarray,
		start_calendar_year: np.ndarray
	) -> np.ndarray:
		"""
		Calculate cumulative production within each calendar year.
		
		Args:
			production: Array of production values
			start_calendar_year: Array indicating start of calendar years
			
		Returns:
			Array of cumulative production values
		"""
		cumulative_production = np.zeros_like(production)
		
		for i in range(len(production)):
			if start_calendar_year[i] == 1:
				cumulative_production[i] = production[i]
			else:
				cumulative_production[i] = cumulative_production[i - 1] + production[i]
				
		return cumulative_production





import numpy as np
import pandas as pd
import calendar
from typing import Dict, List
from functools import lru_cache

class Production:
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
		self.instance.financial_model['seasonality'] = SeasonalityCalculator.create_season_series_optimized(
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

		# Convert to numpy arrays for faster computation
		seasonality_array = np.array(self.instance.financial_model['seasonality'])
		capacity_array = np.array(self.instance.financial_model['capacity']['after_degradation'])
		
		# Debug logging
		import logging
		logger = logging.getLogger(__name__)
		
		# Vectorized calculation
		self.instance.financial_model['production']['total'] = pd.Series(
			production_volume * seasonality_array * capacity_array * (1 + float(sensi_production))
		)
		
	def _calculate_contract_production(self) -> None:
		"""Calculate contract production."""
		# Convert to numpy for faster computation
		total_prod = np.array(self.instance.financial_model['production']['total'])
		pct_contract = np.array(self.instance.financial_model['time_series']['pct_in_contract_period'])
		pct_operations = np.array(self.instance.financial_model['time_series']['pct_in_operations_period'])
		
		self.instance.financial_model['production']['contract'] = pd.Series(
			total_prod * pct_contract * pct_operations
		)
		
	def _calculate_cumulative_production(self) -> None:
		"""Calculate cumulative production within a year."""
		production_array = np.array(self.instance.financial_model['production']['contract'])
		start_year_array = np.array(self.instance.financial_model['flags']['start_year'])
		
		self.instance.financial_model['production']['contract_cumul_in_year'] = pd.Series(
			ProductionCalculator.calculate_cumulative_production_optimized(
				production_array,
				start_year_array
			)
		)


class SeasonalityCalculator:
	@staticmethod
	@lru_cache(maxsize=128)
	def _get_month_days(year: int, month: int) -> int:
		"""Cache month days calculation."""
		return calendar.monthrange(year, month)[1]
	
	@staticmethod
	def create_season_series_optimized(seasonality: pd.Series, dates_series: Dict) -> List[float]:
		"""
		Optimized seasonality series creation using vectorized operations.
		
		Args:
			seasonality: Seasonality factors
			dates_series: Dictionary containing start and end dates
			
		Returns:
			List of seasonality factors for each period
		"""
		# Parse dates with explicit dayfirst=True to handle DD/MM/YYYY format
		start_dates = pd.to_datetime(dates_series['model']['start'], dayfirst=True)
		end_dates = pd.to_datetime(dates_series['model']['end'], dayfirst=True)
		
		n_periods = len(start_dates)
		seasonality_matrix = np.zeros((12, n_periods))
		
		# Vectorized approach
		for i in range(n_periods):
			date_range = pd.date_range(start=start_dates.iloc[i], end=end_dates.iloc[i], freq='D')
			
			# Count days per month using vectorized operations
			months = date_range.month
			years = date_range.year
			
			# Group by year-month to handle periods spanning multiple years correctly
			year_months = list(zip(years, months))
			unique_year_months = list(set(year_months))
			
			for year, month in unique_year_months:
				# Count days for this specific year-month combination
				count = sum(1 for y, m in year_months if y == year and m == month)
				total_days_in_month = calendar.monthrange(year, month)[1]
				seasonality_matrix[month-1, i] = count / total_days_in_month
		
		# Apply seasonality factors using broadcasting
		seasonality_array = np.array(seasonality)[:, np.newaxis]
		weighted_seasonality = seasonality_matrix * seasonality_array
		
		return weighted_seasonality.sum(axis=0).tolist()
		
	@staticmethod
	def create_season_series(seasonality: pd.Series, dates_series: Dict) -> List[float]:
		"""
		Original method kept for backward compatibility.
		"""
		return SeasonalityCalculator.create_season_series_optimized(seasonality, dates_series)
	
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
	def calculate_cumulative_production_optimized(
		production: np.ndarray,
		start_calendar_year: np.ndarray
	) -> np.ndarray:
		"""
		Optimized cumulative production calculation using numpy operations.
		
		Args:
			production: Array of production values
			start_calendar_year: Array indicating start of calendar years
			
		Returns:
			Array of cumulative production values
		"""
		# Find reset points where new years start
		reset_points = np.where(start_calendar_year == 1)[0]
		
		if len(reset_points) == 0:
			# No resets, simple cumulative sum
			return np.cumsum(production)
		
		cumulative_production = np.zeros_like(production)
		
		# Process each segment between resets
		start_idx = 0
		for reset_idx in reset_points:
			if reset_idx > start_idx:
				# Calculate cumulative sum for this segment
				segment = production[start_idx:reset_idx]
				cumulative_production[start_idx:reset_idx] = np.cumsum(segment)
			start_idx = reset_idx
		
		# Handle the last segment
		if start_idx < len(production):
			segment = production[start_idx:]
			cumulative_production[start_idx:] = np.cumsum(segment)
			
		return cumulative_production
	
	@staticmethod
	def calculate_cumulative_production(
		production: np.ndarray,
		start_calendar_year: np.ndarray
	) -> np.ndarray:
		"""
		Original method kept for backward compatibility.
		"""
		return ProductionCalculator.calculate_cumulative_production_optimized(
			production, start_calendar_year
		)
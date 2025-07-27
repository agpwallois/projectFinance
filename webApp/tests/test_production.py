import unittest
from unittest.mock import Mock, MagicMock, patch
import numpy as np
import pandas as pd
from datetime import date, datetime
import calendar

from financial_model.financial_model_sections.production import (
	Production, SeasonalityCalculator, ProductionCalculator
)


class TestProduction(unittest.TestCase):
	"""Test cases for the Production class."""
	
	def setUp(self):
		"""Set up test fixtures."""
		self.mock_instance = Mock()
		self.mock_instance.financial_model = {}
		self.mock_instance.seasonality_inp = pd.Series([1.0] * 12)  # Uniform seasonality
		self.mock_instance.project = Mock()
		self.mock_instance.project.p90_10y = 8760  # MWh/year
		self.mock_instance.project.p75 = 9000
		self.mock_instance.project.p50 = 9500
		self.mock_instance.project.production_choice = 1
		self.mock_instance.project.sponsor_production_choice = 2
		
		self.production = Production(self.mock_instance)
		
	def test_initialize_capacity_success(self):
		"""Test successful capacity initialization."""
		# Mock create_capacity_series to set up capacity data
		def mock_create_capacity():
			self.mock_instance.financial_model['capacity'] = {
				'after_degradation': pd.Series([100, 99, 98])
			}
		self.mock_instance.create_capacity_series = mock_create_capacity
		
		self.production._initialize_capacity()
		
		self.assertIn('capacity', self.mock_instance.financial_model)
		self.assertIn('after_degradation', self.mock_instance.financial_model['capacity'])
		
	def test_initialize_capacity_missing_degradation(self):
		"""Test capacity initialization fails when after_degradation is missing."""
		# Mock create_capacity_series without after_degradation
		def mock_create_capacity():
			self.mock_instance.financial_model['capacity'] = {}
		self.mock_instance.create_capacity_series = mock_create_capacity
		
		with self.assertRaises(ValueError) as context:
			self.production._initialize_capacity()
		
		self.assertIn("after_degradation", str(context.exception))
		
	@patch.object(SeasonalityCalculator, 'create_season_series_optimized')
	def test_initialize_seasonality(self, mock_seasonality):
		"""Test seasonality initialization."""
		mock_seasonality.return_value = [1.0, 1.1, 0.9, 1.0]
		self.mock_instance.financial_model['dates'] = {
			'model': {
				'start': pd.Series(['01/01/2024', '01/02/2024']),
				'end': pd.Series(['31/01/2024', '29/02/2024'])
			}
		}
		
		self.production._initialize_seasonality()
		
		mock_seasonality.assert_called_once_with(
			self.mock_instance.seasonality_inp,
			self.mock_instance.financial_model['dates']
		)
		self.assertEqual(self.mock_instance.financial_model['seasonality'], [1.0, 1.1, 0.9, 1.0])
		
	def test_initialize_production_lender_model(self):
		"""Test production initialization for lender model."""
		# Setup required data
		self.mock_instance.financial_model['capacity'] = {
			'after_degradation': pd.Series([100, 99, 98])
		}
		self.mock_instance.financial_model['seasonality'] = [1.0, 1.0, 1.0]
		self.mock_instance.financial_model['time_series'] = {
			'pct_in_contract_period': pd.Series([1.0, 1.0, 1.0]),
			'pct_in_operations_period': pd.Series([1.0, 1.0, 1.0])
		}
		self.mock_instance.financial_model['flags'] = {
			'start_year': pd.Series([1, 0, 0])
		}
		
		self.production._initialize_production('lender', 0.0)
		
		# Check production values (should use p90_10y = 8760 / 1000 = 8.76)
		expected_total = pd.Series([8.76 * 100, 8.76 * 99, 8.76 * 98])
		pd.testing.assert_series_equal(
			self.mock_instance.financial_model['production']['total'],
			expected_total
		)
		
	def test_initialize_production_sponsor_model(self):
		"""Test production initialization for sponsor model."""
		# Setup required data
		self.mock_instance.financial_model['capacity'] = {
			'after_degradation': pd.Series([100, 99, 98])
		}
		self.mock_instance.financial_model['seasonality'] = [1.0, 1.0, 1.0]
		self.mock_instance.financial_model['time_series'] = {
			'pct_in_contract_period': pd.Series([1.0, 1.0, 1.0]),
			'pct_in_operations_period': pd.Series([1.0, 1.0, 1.0])
		}
		self.mock_instance.financial_model['flags'] = {
			'start_year': pd.Series([1, 0, 0])
		}
		
		self.production._initialize_production('sponsor', 0.0)
		
		# Check production values (should use p75 = 9000 / 1000 = 9.0)
		expected_total = pd.Series([9.0 * 100, 9.0 * 99, 9.0 * 98])
		pd.testing.assert_series_equal(
			self.mock_instance.financial_model['production']['total'],
			expected_total
		)
		
	def test_calculate_total_production_with_sensitivity(self):
		"""Test total production calculation with sensitivity factor."""
		self.mock_instance.financial_model['capacity'] = {
			'after_degradation': pd.Series([100, 99, 98])
		}
		self.mock_instance.financial_model['seasonality'] = [1.0, 1.1, 0.9]
		
		# 10% sensitivity increase
		self.production._calculate_total_production(10.0, 0.1)
		
		expected = pd.Series([
			10.0 * 1.0 * 100 * 1.1,  # base * seasonality * capacity * (1 + sensi)
			10.0 * 1.1 * 99 * 1.1,
			10.0 * 0.9 * 98 * 1.1
		])
		pd.testing.assert_series_equal(
			self.mock_instance.financial_model['production']['total'],
			expected
		)
		
	def test_calculate_total_production_missing_capacity(self):
		"""Test total production calculation fails without capacity data."""
		self.mock_instance.financial_model['capacity'] = {}
		
		with self.assertRaises(ValueError) as context:
			self.production._calculate_total_production(10.0, 0.0)
		
		self.assertIn("capacity degradation data", str(context.exception))
		
	def test_calculate_contract_production(self):
		"""Test contract production calculation."""
		self.mock_instance.financial_model['production'] = {
			'total': pd.Series([100, 110, 120])
		}
		self.mock_instance.financial_model['time_series'] = {
			'pct_in_contract_period': pd.Series([1.0, 0.5, 0.0]),
			'pct_in_operations_period': pd.Series([1.0, 1.0, 1.0])
		}
		
		self.production._calculate_contract_production()
		
		expected = pd.Series([100 * 1.0 * 1.0, 110 * 0.5 * 1.0, 120 * 0.0 * 1.0])
		pd.testing.assert_series_equal(
			self.mock_instance.financial_model['production']['contract'],
			expected
		)
		
	@patch.object(ProductionCalculator, 'calculate_cumulative_production_optimized')
	def test_calculate_cumulative_production(self, mock_calc):
		"""Test cumulative production calculation."""
		mock_calc.return_value = np.array([100, 200, 300, 100, 200], dtype=np.int64)
		
		self.mock_instance.financial_model['production'] = {
			'contract': pd.Series([100, 100, 100, 100, 100])
		}
		self.mock_instance.financial_model['flags'] = {
			'start_year': pd.Series([1, 0, 0, 1, 0])
		}
		
		self.production._calculate_cumulative_production()
		
		mock_calc.assert_called_once()
		pd.testing.assert_series_equal(
			self.mock_instance.financial_model['production']['contract_cumul_in_year'],
			pd.Series([100, 200, 300, 100, 200], dtype=np.int64)
		)
			
	def test_full_initialization_flow(self):
		"""Test complete initialization flow."""
		# Mock all required methods
		self.mock_instance.create_capacity_series = Mock()
		self.mock_instance.financial_model = {
			'capacity': {'after_degradation': pd.Series([100, 99])},
			'dates': {
				'model': {
					'start': pd.Series(['01/01/2024', '01/02/2024']),
					'end': pd.Series(['31/01/2024', '29/02/2024'])
				}
			},
			'time_series': {
				'pct_in_contract_period': pd.Series([1.0, 1.0]),
				'pct_in_operations_period': pd.Series([1.0, 1.0])
			},
			'flags': {
				'start_year': pd.Series([1, 0])
			}
		}
		
		with patch.object(SeasonalityCalculator, 'create_season_series_optimized', 
						 return_value=[1.0, 1.0]):
			self.production.initialize('lender', 0.0)
		
		# Verify all components were initialized
		self.assertIn('production', self.mock_instance.financial_model)
		self.assertIn('total', self.mock_instance.financial_model['production'])
		self.assertIn('contract', self.mock_instance.financial_model['production'])
		self.assertIn('contract_cumul_in_year', self.mock_instance.financial_model['production'])


class TestSeasonalityCalculator(unittest.TestCase):
	"""Test cases for SeasonalityCalculator class."""
	
	def setUp(self):
		"""Set up test fixtures."""
		self.seasonality = pd.Series([1.0, 1.1, 1.2, 1.0, 0.9, 0.8, 0.8, 0.9, 1.0, 1.1, 1.2, 1.0])
		
	def test_get_month_days(self):
		"""Test month days calculation."""
		# Test regular month
		self.assertEqual(SeasonalityCalculator._get_month_days(2024, 1), 31)
		
		# Test February in leap year
		self.assertEqual(SeasonalityCalculator._get_month_days(2024, 2), 29)
		
		# Test February in non-leap year
		self.assertEqual(SeasonalityCalculator._get_month_days(2023, 2), 28)
		
	def test_create_season_series_single_month(self):
		"""Test seasonality for periods within single months."""
		dates_series = {
			'model': {
				'start': pd.Series(['01/01/2024', '01/02/2024']),
				'end': pd.Series(['31/01/2024', '29/02/2024'])
			}
		}
		
		result = SeasonalityCalculator.create_season_series_optimized(
			self.seasonality, dates_series
		)
		
		# January has full month, February has full month
		self.assertEqual(len(result), 2)
		self.assertAlmostEqual(result[0], 1.0)  # January seasonality
		self.assertAlmostEqual(result[1], 1.1)  # February seasonality
		
	def test_create_season_series_partial_months(self):
		"""Test seasonality for periods spanning partial months."""
		dates_series = {
			'model': {
				'start': pd.Series(['15/01/2024', '01/02/2024']),
				'end': pd.Series(['31/01/2024', '23/02/2024'])
			}
		}
		
		result = SeasonalityCalculator.create_season_series_optimized(
			self.seasonality, dates_series
		)
		
		self.assertEqual(len(result), 2)
		self.assertAlmostEqual(result[0], 0.5483870967)  # January seasonality
		self.assertAlmostEqual(result[1], 0.8724137931)  # February seasonality        

		
	def test_calculate_days_in_month(self):
		"""Test days in month calculation."""
		dates_in_period = [
			datetime(2024, 1, 15),
			datetime(2024, 1, 16),
			datetime(2024, 1, 17)
		]
		
		result = SeasonalityCalculator._calculate_days_in_month(dates_in_period, 1)
		
		# 3 days out of 31 in January
		self.assertAlmostEqual(result, 3/31)
		
	def test_calculate_days_in_month_no_days(self):
		"""Test days in month calculation with no matching days."""
		dates_in_period = [
			datetime(2024, 1, 15),
			datetime(2024, 1, 16)
		]
		
		result = SeasonalityCalculator._calculate_days_in_month(dates_in_period, 2)
		
		self.assertEqual(result, 0)


class TestProductionCalculator(unittest.TestCase):
	"""Test cases for ProductionCalculator class."""
	
	def test_cumulative_production_no_resets(self):
		"""Test cumulative production without year resets."""
		production = np.array([10, 20, 30, 40])
		start_calendar_year = np.array([0, 0, 0, 0])
		
		result = ProductionCalculator.calculate_cumulative_production_optimized(
			production, start_calendar_year
		)
		
		expected = np.array([10, 30, 60, 100])
		np.testing.assert_array_equal(result, expected)
		
	def test_cumulative_production_with_resets(self):
		"""Test cumulative production with year resets."""
		production = np.array([10, 20, 30, 40, 50])
		start_calendar_year = np.array([1, 0, 0, 1, 0])
		
		result = ProductionCalculator.calculate_cumulative_production_optimized(
			production, start_calendar_year
		)
		
		# Reset at index 0 and 3
		expected = np.array([10, 30, 60, 40, 90])
		np.testing.assert_array_equal(result, expected)
		
	def test_cumulative_production_empty_array(self):
		"""Test cumulative production with empty arrays."""
		production = np.array([])
		start_calendar_year = np.array([])
		
		result = ProductionCalculator.calculate_cumulative_production_optimized(
			production, start_calendar_year
		)
		
		expected = np.array([])
		np.testing.assert_array_equal(result, expected)
		
	def test_cumulative_production_single_element(self):
		"""Test cumulative production with single element."""
		production = np.array([100])
		start_calendar_year = np.array([1])
		
		result = ProductionCalculator.calculate_cumulative_production_optimized(
			production, start_calendar_year
		)
		
		expected = np.array([100])
		np.testing.assert_array_equal(result, expected)
		
	def test_cumulative_production_all_resets(self):
		"""Test cumulative production where every period is a reset."""
		production = np.array([10, 20, 30])
		start_calendar_year = np.array([1, 1, 1])
		
		result = ProductionCalculator.calculate_cumulative_production_optimized(
			production, start_calendar_year
		)
		
		# Each value stands alone
		expected = np.array([10, 20, 30])
		np.testing.assert_array_equal(result, expected)
		
	def test_backward_compatibility(self):
		"""Test that old method calls the optimized version."""
		production = np.array([10, 20])
		start_calendar_year = np.array([1, 0])
		
		with patch.object(ProductionCalculator, 'calculate_cumulative_production_optimized') as mock:
			mock.return_value = np.array([10, 30])
			
			result = ProductionCalculator.calculate_cumulative_production(
				production, start_calendar_year
			)
			
			mock.assert_called_once_with(production, start_calendar_year)
			np.testing.assert_array_equal(result, np.array([10, 30]))



if __name__ == '__main__':
	unittest.main()
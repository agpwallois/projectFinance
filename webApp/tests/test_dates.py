import unittest
import pandas as pd
import datetime
from unittest.mock import MagicMock, patch
import sys
import os
import django
from django.test import TestCase
from django.conf import settings

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webApp.settings')
django.setup()

from financial_model.financial_model_sections.dates import Dates


class TestDates(TestCase):
    """Comprehensive tests for the Dates class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock instance with required attributes
        self.mock_instance = MagicMock()
        self.mock_instance.financial_model = {}
        self.mock_instance.periods = {
            'construction': {'start': '2024-01-01', 'end': '2024-12-31'},
            'operations': {'start': '2025-01-01', 'end': '2030-12-31'}
        }
        
        # Mock project attributes
        self.mock_instance.project = MagicMock()
        self.mock_instance.project.periodicity = 6  # Semi-annual
        self.mock_instance.project.start_construction = datetime.date(2024, 1, 15)
        self.mock_instance.project.end_construction = datetime.date(2024, 12, 15)
        self.mock_instance.liquidation_date = datetime.date(2030, 6, 30)
        
        # Initialize the Dates instance
        self.dates_manager = Dates(self.mock_instance)
    
    def test_init(self):
        """Test the __init__ method"""
        dates_manager = Dates(self.mock_instance)
        self.assertEqual(dates_manager.instance, self.mock_instance)
    
    def test_initialize(self):
        """Test the initialize method"""
        self.dates_manager.initialize()
        
        # Check that the dates dictionary was created
        self.assertIn('dates', self.mock_instance.financial_model)
        dates_dict = self.mock_instance.financial_model['dates']
        
        # Check that model dates were created
        self.assertIn('model', dates_dict)
        self.assertIn('start', dates_dict['model'])
        self.assertIn('end', dates_dict['model'])
        
        # Check that period dates were created
        self.assertIn('construction', dates_dict)
        self.assertIn('operations', dates_dict)
        
        # Verify that each period has start and end dates
        for period_name in self.mock_instance.periods.keys():
            self.assertIn('start', dates_dict[period_name])
            self.assertIn('end', dates_dict[period_name])
    
    def test_initialize_model_dates(self):
        """Test the _initialize_model_dates method"""
        result = self.dates_manager._initialize_model_dates()
        
        # Check structure
        self.assertIsInstance(result, dict)
        self.assertIn('start', result)
        self.assertIn('end', result)
        
        # Check that results are pandas Series
        self.assertIsInstance(result['start'], pd.Series)
        self.assertIsInstance(result['end'], pd.Series)
        
        # Check that series are not empty
        self.assertGreater(len(result['start']), 0)
        self.assertGreater(len(result['end']), 0)
    
    def test_initialize_period_dates(self):
        """Test the _initialize_period_dates method"""
        # Create mock model dates
        model_start = pd.Series([
            pd.Timestamp('2024-01-01'),
            pd.Timestamp('2024-06-01'),
            pd.Timestamp('2025-01-01'),
            pd.Timestamp('2026-01-01')
        ])
        model_end = pd.Series([
            pd.Timestamp('2024-05-31'),
            pd.Timestamp('2024-12-31'),
            pd.Timestamp('2025-12-31'),
            pd.Timestamp('2026-12-31')
        ])
        
        period_dates = {'start': '2024-06-01', 'end': '2025-12-31'}
        
        result = self.dates_manager._initialize_period_dates(
            model_start, model_end, period_dates
        )
        
        # Check structure
        self.assertIsInstance(result, dict)
        self.assertIn('start', result)
        self.assertIn('end', result)
        
        # Check that results are pandas Series
        self.assertIsInstance(result['start'], pd.Series)
        self.assertIsInstance(result['end'], pd.Series)
    
    def test_calculate_model_start_dates(self):
        """Test the _calculate_model_start_dates method"""
        periodicity = 6
        construction_start = datetime.date(2024, 1, 15)
        construction_end = datetime.date(2024, 12, 15)
        liquidation_date = datetime.date(2030, 6, 30)
        
        result = self.dates_manager._calculate_model_start_dates(
            periodicity, construction_start, construction_end, liquidation_date
        )
        
        # Check that result is a pandas Series
        self.assertIsInstance(result, pd.Series)
        
        # Check that it's not empty
        self.assertGreater(len(result), 0)
        
        # Check that the first date corresponds to construction start (first day of month)
        expected_first_date = pd.Timestamp('2024-01-01')
        self.assertEqual(result.iloc[0], expected_first_date)
        
        # Check that all dates are in chronological order
        self.assertTrue(result.is_monotonic_increasing)
    
    def test_calculate_model_end_dates(self):
        """Test the _calculate_model_end_dates method"""
        periodicity = 6
        construction_start = datetime.date(2024, 1, 15)
        construction_end = datetime.date(2024, 12, 15)
        liquidation_date = datetime.date(2030, 6, 30)
        
        result = self.dates_manager._calculate_model_end_dates(
            periodicity, construction_start, construction_end, liquidation_date
        )
        
        # Check that result is a pandas Series
        self.assertIsInstance(result, pd.Series)
        
        # Check that it's not empty
        self.assertGreater(len(result), 0)
        
        # Check that all dates are in chronological order
        self.assertTrue(result.is_monotonic_increasing)
    
    def test_first_day_of_next_month(self):
        """Test the _first_day_of_next_month method"""
        test_date = datetime.date(2024, 6, 15)
        periodicity = 6
        
        result = self.dates_manager._first_day_of_next_month(test_date, periodicity)
        
        # Expected: first day of month 6 months later, minus 1 day
        expected = datetime.date(2024, 12, 1) - datetime.timedelta(days=1)
        self.assertEqual(result, expected)
        
        # Test with different periodicity
        result_quarterly = self.dates_manager._first_day_of_next_month(test_date, 3)
        expected_quarterly = datetime.date(2024, 9, 1) - datetime.timedelta(days=1)
        self.assertEqual(result_quarterly, expected_quarterly)
    
    def test_first_day_of_month(self):
        """Test the _first_day_of_month static method"""
        test_cases = [
            (datetime.date(2024, 6, 15), datetime.date(2024, 6, 1)),
            (datetime.date(2024, 12, 31), datetime.date(2024, 12, 1)),
            (datetime.date(2024, 2, 29), datetime.date(2024, 2, 1)),  # Leap year
            (datetime.date(2024, 1, 1), datetime.date(2024, 1, 1))   # Already first day
        ]
        
        for input_date, expected in test_cases:
            with self.subTest(input_date=input_date):
                result = Dates._first_day_of_month(input_date)
                self.assertEqual(result, expected)
    
    def test_last_day_of_month(self):
        """Test the _last_day_of_month static method"""
        test_cases = [
            (datetime.date(2024, 6, 15), datetime.date(2024, 6, 30)),
            (datetime.date(2024, 2, 15), datetime.date(2024, 2, 29)),  # Leap year
            (datetime.date(2023, 2, 15), datetime.date(2023, 2, 28)),  # Non-leap year
            (datetime.date(2024, 12, 1), datetime.date(2024, 12, 31)),
            (datetime.date(2024, 4, 30), datetime.date(2024, 4, 30))   # Already last day
        ]
        
        for input_date, expected in test_cases:
            with self.subTest(input_date=input_date):
                result = Dates._last_day_of_month(input_date)
                self.assertEqual(result, expected)
    
    def test_filter_dates(self):
        """Test the _filter_dates static method"""
        # Create test timeline
        timeline = pd.Series([
            pd.Timestamp('2024-01-01'),
            pd.Timestamp('2024-06-01'),
            pd.Timestamp('2024-12-01'),
            pd.Timestamp('2025-06-01'),
            pd.Timestamp('2025-12-01')
        ])
        
        start_date = '2024-06-01'
        end_date = '2025-06-01'
        
        result = Dates._filter_dates(timeline, start_date, end_date)
        
        # Check that result is a pandas Series
        self.assertIsInstance(result, pd.Series)
        
        # Check that all dates are within the specified range
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        
        for date in result:
            self.assertGreaterEqual(date, start_ts)
            self.assertLessEqual(date, end_ts)
    
    def test_filter_dates_edge_cases(self):
        """Test _filter_dates with edge cases"""
        timeline = pd.Series([
            pd.Timestamp('2024-01-01'),
            pd.Timestamp('2024-06-01'),
            pd.Timestamp('2024-12-01')
        ])
        
        # Test with start date after all timeline dates
        result_future = Dates._filter_dates(
            timeline, '2025-01-01', '2025-12-01'
        )
        # All dates should be clipped to start date
        for date in result_future:
            self.assertEqual(date, pd.Timestamp('2025-01-01'))
        
        # Test with end date before all timeline dates
        result_past = Dates._filter_dates(
            timeline, '2023-01-01', '2023-12-01'
        )
        # All dates should be clipped to end date
        for date in result_past:
            self.assertEqual(date, pd.Timestamp('2023-12-01'))
    
    def test_integration_with_different_periodicities(self):
        """Test the class with different periodicity values"""
        periodicities = [3, 6, 12]  # Quarterly, semi-annual, annual
        
        for periodicity in periodicities:
            with self.subTest(periodicity=periodicity):
                # Update mock instance
                self.mock_instance.project.periodicity = periodicity
                
                # Test model date calculations
                start_dates = self.dates_manager._calculate_model_start_dates(
                    periodicity,
                    self.mock_instance.project.start_construction,
                    self.mock_instance.project.end_construction,
                    self.mock_instance.liquidation_date
                )
                
                end_dates = self.dates_manager._calculate_model_end_dates(
                    periodicity,
                    self.mock_instance.project.start_construction,
                    self.mock_instance.project.end_construction,
                    self.mock_instance.liquidation_date
                )
                
                # Basic checks
                self.assertIsInstance(start_dates, pd.Series)
                self.assertIsInstance(end_dates, pd.Series)
                self.assertGreater(len(start_dates), 0)
                self.assertGreater(len(end_dates), 0)
    
    def test_date_consistency(self):
        """Test that start dates are always before corresponding end dates"""
        start_dates = self.dates_manager._calculate_model_start_dates(
            6,
            self.mock_instance.project.start_construction,
            self.mock_instance.project.end_construction,
            self.mock_instance.liquidation_date
        )
        
        end_dates = self.dates_manager._calculate_model_end_dates(
            6,
            self.mock_instance.project.start_construction,
            self.mock_instance.project.end_construction,
            self.mock_instance.liquidation_date
        )
        
        # Check that we have the same number of start and end dates
        self.assertEqual(len(start_dates), len(end_dates))
        
        # Check that each start date is before its corresponding end date
        for i in range(len(start_dates)):
            self.assertLess(start_dates.iloc[i], end_dates.iloc[i])
    
    def test_empty_periods(self):
        """Test behavior with empty periods dictionary"""
        self.mock_instance.periods = {}
        self.dates_manager.initialize()
        
        # Should still have model dates
        self.assertIn('model', self.mock_instance.financial_model['dates'])
        
        # Should not have any period-specific dates
        dates_dict = self.mock_instance.financial_model['dates']
        self.assertEqual(len(dates_dict), 1)  # Only 'model'


def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
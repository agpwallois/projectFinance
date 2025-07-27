import unittest
import pandas as pd
import datetime
from unittest.mock import MagicMock
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

from financial_model.financial_model_sections.days import Days


class TestDays(TestCase):
    """Comprehensive tests for the Days class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock instance with required structure
        self.mock_instance = MagicMock()
        self.mock_instance.financial_model = {
            'dates': {
                'model': {
                    'start': pd.Series([
                        pd.Timestamp('2024-01-01'),
                        pd.Timestamp('2024-07-01'),
                        pd.Timestamp('2025-01-01')
                    ]),
                    'end': pd.Series([
                        pd.Timestamp('2024-06-30'),
                        pd.Timestamp('2024-12-31'),
                        pd.Timestamp('2025-06-30')
                    ])
                },
                'contract': {
                    'start': pd.Series([
                        pd.Timestamp('2024-01-01'),
                        pd.Timestamp('2024-07-01')
                    ]),
                    'end': pd.Series([
                        pd.Timestamp('2024-06-30'),
                        pd.Timestamp('2024-12-31')
                    ])
                },
                'contract_indexation': {
                    'start': pd.Series([pd.Timestamp('2024-01-01')]),
                    'end': pd.Series([pd.Timestamp('2024-12-31')])
                },
                'merchant_indexation': {
                    'start': pd.Series([pd.Timestamp('2024-01-01')]),
                    'end': pd.Series([pd.Timestamp('2024-12-31')])
                },
                'opex_indexation': {
                    'start': pd.Series([pd.Timestamp('2024-01-01')]),
                    'end': pd.Series([pd.Timestamp('2024-12-31')])
                },
                'debt_interest_construction': {
                    'start': pd.Series([pd.Timestamp('2024-01-01')]),
                    'end': pd.Series([pd.Timestamp('2024-06-30')])
                },
                'debt_interest_operations': {
                    'start': pd.Series([pd.Timestamp('2024-07-01')]),
                    'end': pd.Series([pd.Timestamp('2024-12-31')])
                },
                'operations': {
                    'start': pd.Series([pd.Timestamp('2024-07-01')]),
                    'end': pd.Series([pd.Timestamp('2024-12-31')])
                },
                'lease_indexation': {
                    'start': pd.Series([pd.Timestamp('2024-01-01')]),
                    'end': pd.Series([pd.Timestamp('2024-12-31')])
                }
            },
            'flags': {
                'contract': pd.Series([1, 1]),
                'contract_indexation': pd.Series([1]),
                'merchant_indexation': pd.Series([0]),  # Not active
                'opex_indexation': pd.Series([1]),
                'construction': pd.Series([1]),
                'debt_amo': pd.Series([1]),
                'operations': pd.Series([1]),
                'lease_indexation': pd.Series([1])
            }
        }
        
        # Initialize the Days instance
        self.days_manager = Days(self.mock_instance)
    
    def test_init(self):
        """Test the __init__ method"""
        days_manager = Days(self.mock_instance)
        self.assertEqual(days_manager.instance, self.mock_instance)
    
    def test_initialize(self):
        """Test the initialize method"""
        self.days_manager.initialize()
        
        # Check that the days dictionary was created
        self.assertIn('days', self.mock_instance.financial_model)
        days_dict = self.mock_instance.financial_model['days']
        
        # Check that all expected period types were created
        expected_periods = [
            'model', 'contract', 'contract_indexation', 'merchant_indexation',
            'opex_indexation', 'debt_interest_construction', 'debt_interest_operations',
            'operations', 'lease_indexation'
        ]
        
        for period in expected_periods:
            self.assertIn(period, days_dict)
            self.assertIsInstance(days_dict[period], pd.Series)
    
    def test_initialize_day_calculations(self):
        """Test that initialize correctly calculates day counts"""
        self.days_manager.initialize()
        days_dict = self.mock_instance.financial_model['days']
        
        # Test model period calculations
        # Period 1: 2024-01-01 to 2024-06-30 = 182 days (leap year)
        # Period 2: 2024-07-01 to 2024-12-31 = 184 days
        # Period 3: 2025-01-01 to 2025-06-30 = 181 days
        model_days = days_dict['model']
        self.assertEqual(model_days.iloc[0], 182)  # Jan 1 to Jun 30, 2024 (leap year)
        self.assertEqual(model_days.iloc[1], 184)  # Jul 1 to Dec 31, 2024
        self.assertEqual(model_days.iloc[2], 181)  # Jan 1 to Jun 30, 2025
        
        # Test contract period calculations (should be same as model for first two periods)
        contract_days = days_dict['contract']
        self.assertEqual(contract_days.iloc[0], 182)  # Jan 1 to Jun 30, 2024
        self.assertEqual(contract_days.iloc[1], 184)  # Jul 1 to Dec 31, 2024
    
    def test_initialize_with_flags(self):
        """Test that flags are properly applied in day calculations"""
        # Set merchant_indexation flag to 0 (inactive)
        self.mock_instance.financial_model['flags']['merchant_indexation'] = pd.Series([0])
        
        self.days_manager.initialize()
        days_dict = self.mock_instance.financial_model['days']
        
        # merchant_indexation should have 0 days due to flag
        merchant_days = days_dict['merchant_indexation']
        self.assertEqual(merchant_days.iloc[0], 0)  # 366 days * 0 flag = 0
        
        # contract_indexation should have actual days (flag = 1)
        contract_indexation_days = days_dict['contract_indexation']
        self.assertEqual(contract_indexation_days.iloc[0], 366)  # Full year 2024 (leap year)
    
    def test_build_days_series_dict(self):
        """Test the _build_days_series_dict method"""
        result = self.days_manager._build_days_series_dict()
        
        # Check structure
        self.assertIsInstance(result, dict)
        
        # Check that all expected keys are present
        expected_keys = [
            'model', 'contract', 'contract_indexation', 'merchant_indexation',
            'opex_indexation', 'debt_interest_construction', 'debt_interest_operations',
            'operations', 'lease_indexation'
        ]
        
        for key in expected_keys:
            self.assertIn(key, result)
            
            # Check structure of each entry
            entry = result[key]
            self.assertIn('flag', entry)
            self.assertIn('start_dates', entry)
            self.assertIn('end_dates', entry)
    
    def test_build_days_series_dict_content(self):
        """Test the content of _build_days_series_dict method"""
        result = self.days_manager._build_days_series_dict()
        
        # Test model entry
        model_entry = result['model']
        self.assertEqual(model_entry['flag'], 1)
        pd.testing.assert_series_equal(
            model_entry['start_dates'],
            self.mock_instance.financial_model['dates']['model']['start']
        )
        pd.testing.assert_series_equal(
            model_entry['end_dates'],
            self.mock_instance.financial_model['dates']['model']['end']
        )
        
        # Test contract entry
        contract_entry = result['contract']
        pd.testing.assert_series_equal(
            contract_entry['flag'],
            self.mock_instance.financial_model['flags']['contract']
        )
        
        # Test debt_interest_construction entry
        debt_construction_entry = result['debt_interest_construction']
        pd.testing.assert_series_equal(
            debt_construction_entry['flag'],
            self.mock_instance.financial_model['flags']['construction']
        )
    
    def test_parse_dates_with_timestamps(self):
        """Test _parse_dates with Timestamp objects"""
        timestamp_series = pd.Series([
            pd.Timestamp('2024-01-01'),
            pd.Timestamp('2024-06-30'),
            pd.Timestamp('2024-12-31')
        ])
        
        result = Days._parse_dates(timestamp_series)
        
        # Should return the same timestamps
        pd.testing.assert_series_equal(result, timestamp_series, check_names=False)
        self.assertIsInstance(result, pd.Series)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result))
    
    def test_parse_dates_with_date_strings(self):
        """Test _parse_dates with date strings in dd/mm/yyyy format"""
        date_strings = pd.Series(['01/01/2024', '30/06/2024', '31/12/2024'])
        
        result = Days._parse_dates(date_strings)
        
        # Check that dates were parsed correctly
        expected = pd.Series([
            pd.Timestamp('2024-01-01'),
            pd.Timestamp('2024-06-30'),
            pd.Timestamp('2024-12-31')
        ])
        
        pd.testing.assert_series_equal(result, expected, check_names=False)
        self.assertIsInstance(result, pd.Series)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result))
    
    def test_parse_dates_with_mixed_formats(self):
        """Test _parse_dates with mixed date formats"""
        mixed_dates = pd.Series([
            '01/01/2024',
            pd.Timestamp('2024-06-30'),
            '31/12/2024'
        ])
        
        result = Days._parse_dates(mixed_dates)
        
        # Should handle mixed formats correctly
        expected = pd.Series([
            pd.Timestamp('2024-01-01'),
            pd.Timestamp('2024-06-30'),
            pd.Timestamp('2024-12-31')
        ])
        
        pd.testing.assert_series_equal(result, expected, check_names=False)
    
    def test_parse_dates_empty_series(self):
        """Test _parse_dates with empty series"""
        empty_series = pd.Series([], dtype=object)
        
        result = Days._parse_dates(empty_series)
        
        self.assertIsInstance(result, pd.Series)
        self.assertEqual(len(result), 0)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result))
    
    def test_leap_year_calculation(self):
        """Test day calculations for leap year scenarios"""
        # Set up dates that span a leap year
        self.mock_instance.financial_model['dates']['model']['start'] = pd.Series([
            pd.Timestamp('2024-01-01'),  # Leap year
            pd.Timestamp('2023-01-01')   # Non-leap year
        ])
        self.mock_instance.financial_model['dates']['model']['end'] = pd.Series([
            pd.Timestamp('2024-12-31'),  # Leap year - 366 days
            pd.Timestamp('2023-12-31')   # Non-leap year - 365 days
        ])
        
        self.days_manager.initialize()
        days_dict = self.mock_instance.financial_model['days']
        
        # Check leap year calculation
        model_days = days_dict['model']
        self.assertEqual(model_days.iloc[0], 366)  # 2024 is a leap year
        self.assertEqual(model_days.iloc[1], 365)  # 2023 is not a leap year
    
    def test_single_day_period(self):
        """Test calculation for single-day periods"""
        # Set up single day periods
        self.mock_instance.financial_model['dates']['contract']['start'] = pd.Series([
            pd.Timestamp('2024-06-15')
        ])
        self.mock_instance.financial_model['dates']['contract']['end'] = pd.Series([
            pd.Timestamp('2024-06-15')
        ])
        self.mock_instance.financial_model['flags']['contract'] = pd.Series([1])
        
        self.days_manager.initialize()
        days_dict = self.mock_instance.financial_model['days']
        
        # Single day should equal 1
        contract_days = days_dict['contract']
        self.assertEqual(contract_days.iloc[0], 1)
    
    def test_zero_flag_multiplication(self):
        """Test that zero flags result in zero days"""
        # Set all flags to 0
        for flag_key in self.mock_instance.financial_model['flags']:
            self.mock_instance.financial_model['flags'][flag_key] = pd.Series([0])
        
        self.days_manager.initialize()
        days_dict = self.mock_instance.financial_model['days']
        
        # All periods except model should have 0 days
        for period_name, days_series in days_dict.items():
            if period_name == 'model':
                # Model always uses flag = 1
                self.assertGreater(days_series.iloc[0], 0)
            else:
                # All other periods should be 0 due to zero flags
                self.assertEqual(days_series.iloc[0], 0)



def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
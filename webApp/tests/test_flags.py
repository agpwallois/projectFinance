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

from financial_model.financial_model_sections.flags import Flags


class TestFlags(TestCase):
    """Comprehensive tests for the Flags class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock instance with required structure
        self.mock_instance = MagicMock()
        self.mock_instance.financial_model = {
            'dates': {
                'model': {
                    'start': pd.Series([
                        pd.Timestamp('2024-01-01'),  # Construction start
                        pd.Timestamp('2024-07-01'),  # Construction mid
                        pd.Timestamp('2025-01-01'),  # Operations start
                        pd.Timestamp('2025-07-01'),  # Operations early
                        pd.Timestamp('2026-01-01'),  # Operations mid
                        pd.Timestamp('2026-07-01'),  # Operations mid
                        pd.Timestamp('2027-01-01'),  # Operations late
                        pd.Timestamp('2027-07-01'),  # Operations late
                        pd.Timestamp('2028-01-01'),  # Post-operations
                        pd.Timestamp('2028-07-01')   # Post-operations
                    ]),
                    'end': pd.Series([
                        pd.Timestamp('2024-06-30'),  # Construction start
                        pd.Timestamp('2024-12-31'),  # Construction end
                        pd.Timestamp('2025-06-30'),  # Operations start
                        pd.Timestamp('2025-12-31'),  # Operations early
                        pd.Timestamp('2026-06-30'),  # Operations mid
                        pd.Timestamp('2026-12-31'),  # Operations mid
                        pd.Timestamp('2027-06-30'),  # Operations late
                        pd.Timestamp('2027-12-31'),  # Operations end
                        pd.Timestamp('2028-06-30'),  # Post-operations
                        pd.Timestamp('2028-12-31')   # Post-operations
                    ])
                }
            }
        }
        
        # Mock flag_dict with various date ranges
        self.mock_instance.flag_dict = {
            'construction': ('2024-01-01', '2024-12-31'),
            'operations': ('2025-01-01', '2028-12-28'),
            'contract': ('2025-01-01', '2026-06-30'),
            'contract_indexation': ('2024-01-01', '2026-06-30'),
            'merchant_indexation': ('2024-06-15', '2028-12-31'), 
            'opex_indexation': ('2024-06-03', '2028-12-31'),
            'debt_amo': ('2025-01-01', '2026-06-30'),
            'lease_indexation': ('2024-01-01', '2028-12-31')
        }
        
        # Initialize the Flags instance
        self.flags_manager = Flags(self.mock_instance)
    
    def test_init(self):
        """Test the __init__ method"""
        flags_manager = Flags(self.mock_instance)
        self.assertEqual(flags_manager.instance, self.mock_instance)
        self.assertEqual(flags_manager.financial_model, self.mock_instance.financial_model)
    
    def test_initialize(self):
        """Test the initialize method workflow"""
        self.flags_manager.initialize()
        
        # Check that flags dictionary was created
        self.assertIn('flags', self.mock_instance.financial_model)
        flags_dict = self.mock_instance.financial_model['flags']
        
        # Check that all flags from flag_dict were created
        for flag_name in self.mock_instance.flag_dict.keys():
            self.assertIn(flag_name, flags_dict)
            self.assertIsInstance(flags_dict[flag_name], pd.Series)
        
        # Check that start_year flag was created
        self.assertIn('start_year', flags_dict)
        self.assertIsInstance(flags_dict['start_year'], pd.Series)
    
    def test_parse_model_dates(self):
        """Test the _parse_model_dates method"""
        model_start, model_end = self.flags_manager._parse_model_dates()
        
        # Check that results are pandas Series
        self.assertIsInstance(model_start, pd.Series)
        self.assertIsInstance(model_end, pd.Series)
        
        # Check that they contain datetime data
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(model_start))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(model_end))
        
        # Check lengths match original data
        self.assertEqual(len(model_start), 10)
        self.assertEqual(len(model_end), 10)
        


    def test_parse_model_dates_with_string_dates(self):
        """Test _parse_model_dates with string date inputs"""
        # Set up string dates in dd/mm/yyyy format
        self.mock_instance.financial_model['dates']['model']['start'] = pd.Series([
            '01/01/2024',
            '01/07/2024'
        ])
        self.mock_instance.financial_model['dates']['model']['end'] = pd.Series([
            '30/06/2024',
            '31/12/2024'
        ])
        
        model_start, model_end = self.flags_manager._parse_model_dates()
        
        # Check that string dates were parsed correctly
        self.assertEqual(model_start.iloc[0], pd.Timestamp('2024-01-01'))
        self.assertEqual(model_start.iloc[1], pd.Timestamp('2024-07-01'))
        self.assertEqual(model_end.iloc[0], pd.Timestamp('2024-06-30'))
        self.assertEqual(model_end.iloc[1], pd.Timestamp('2024-12-31'))

    def test_initialize_flags_new_dict(self):
        """Test _initialize_flags when flags dict doesn't exist"""
        # Remove flags from financial_model
        if 'flags' in self.mock_instance.financial_model:
            del self.mock_instance.financial_model['flags']
        
        self.flags_manager._initialize_flags()
        
        # Check that flags dict was created
        self.assertIn('flags', self.mock_instance.financial_model)
        self.assertIsInstance(self.mock_instance.financial_model['flags'], dict)

    
    def test_initialize_flags_existing_dict(self):
        """Test _initialize_flags when flags dict already exists"""
        # Pre-populate flags dict
        self.mock_instance.financial_model['flags'] = {'existing_flag': pd.Series([1, 0])}
        
        self.flags_manager._initialize_flags()
        
        # Check that existing flags are preserved
        self.assertIn('flags', self.mock_instance.financial_model)
        self.assertIn('existing_flag', self.mock_instance.financial_model['flags'])
        pd.testing.assert_series_equal(
            self.mock_instance.financial_model['flags']['existing_flag'],
            pd.Series([1, 0])
        )

    def test_set_flag_values(self):
        """Test the _set_flag_values method"""
        model_start, model_end = self.flags_manager._parse_model_dates()
        self.flags_manager._initialize_flags()
        self.flags_manager._set_flag_values(model_start, model_end)
        
        flags_dict = self.mock_instance.financial_model['flags']
        
        # Test construction flag (2024-01-01 to 2024-12-31)
        # Should be active for periods that overlap with this range
        construction_flags = flags_dict['construction']
        self.assertEqual(construction_flags.iloc[0], 1)  # 2024-01-01 to 2024-06-30 - overlaps
        self.assertEqual(construction_flags.iloc[1], 1)  # 2024-07-01 to 2024-12-31 - overlaps
        self.assertEqual(construction_flags.iloc[2], 0)  # 2025-01-01 to 2025-06-30 - no overlap
        self.assertEqual(construction_flags.iloc[3], 0)  # 2025-07-01 to 2025-12-31 - no overlap
        self.assertEqual(construction_flags.iloc[4], 0)  # 2026-01-01 to 2026-06-30 - no overlap
        self.assertEqual(construction_flags.iloc[5], 0)  # 2026-07-01 to 2026-12-31 - no overlap
        self.assertEqual(construction_flags.iloc[6], 0)  # 2027-01-01 to 2027-06-30 - no overlap
        self.assertEqual(construction_flags.iloc[7], 0)  # 2027-07-01 to 2027-12-31 - no overlap
        self.assertEqual(construction_flags.iloc[8], 0)  # 2028-01-01 to 2028-06-30 - no overlap
        self.assertEqual(construction_flags.iloc[9], 0)  # 2028-07-01 to 2028-12-31 - no overlap
        
        # Test operations flag (2025-01-01 to 2028-12-28)
        operations_flags = flags_dict['operations']
        self.assertEqual(operations_flags.iloc[0], 0)  # 2024-01-01 to 2024-06-30 - no overlap
        self.assertEqual(operations_flags.iloc[1], 0)  # 2024-07-01 to 2024-12-31 - no overlap
        self.assertEqual(operations_flags.iloc[2], 1)  # 2025-01-01 to 2025-06-30 - overlaps
        self.assertEqual(operations_flags.iloc[3], 1)  # 2025-07-01 to 2025-12-31 - overlaps
        self.assertEqual(operations_flags.iloc[4], 1)  # 2026-01-01 to 2026-06-30 - overlaps
        self.assertEqual(operations_flags.iloc[5], 1)  # 2026-07-01 to 2026-12-31 - overlaps
        self.assertEqual(operations_flags.iloc[6], 1)  # 2027-01-01 to 2027-06-30 - overlaps
        self.assertEqual(operations_flags.iloc[7], 1)  # 2027-07-01 to 2027-12-31 - overlaps
        self.assertEqual(operations_flags.iloc[8], 1)  # 2028-01-01 to 2028-06-30 - overlaps
        self.assertEqual(operations_flags.iloc[9], 1)  # 2028-07-01 to 2028-12-31 - no overlap (ends 2028-12-28)
        
        # Test merchant_indexation flag (2024-06-15 to 2028-12-31)
        # Should be active for most periods that overlap with this range
        merchant_flags = flags_dict['merchant_indexation']
        self.assertEqual(merchant_flags.iloc[0], 1)  # 2024-01-01 to 2024-06-30 - overlaps (contains 2024-06-15)
        self.assertEqual(merchant_flags.iloc[1], 1)  # 2024-07-01 to 2024-12-31 - overlaps
        self.assertEqual(merchant_flags.iloc[2], 1)  # 2025-01-01 to 2025-06-30 - overlaps
        self.assertEqual(merchant_flags.iloc[3], 1)  # 2025-07-01 to 2025-12-31 - overlaps
        self.assertEqual(merchant_flags.iloc[4], 1)  # 2026-01-01 to 2026-06-30 - overlaps
        self.assertEqual(merchant_flags.iloc[5], 1)  # 2026-07-01 to 2026-12-31 - overlaps
        self.assertEqual(merchant_flags.iloc[6], 1)  # 2027-01-01 to 2027-06-30 - overlaps
        self.assertEqual(merchant_flags.iloc[7], 1)  # 2027-07-01 to 2027-12-31 - overlaps
        self.assertEqual(merchant_flags.iloc[8], 1)  # 2028-01-01 to 2028-06-30 - overlaps
        self.assertEqual(merchant_flags.iloc[9], 1)  # 2028-07-01 to 2028-12-31 - overlaps
        
        # Test contract flag (2025-01-01 to 2026-06-30)
        contract_flags = flags_dict['contract']
        self.assertEqual(contract_flags.iloc[0], 0)  # 2024-01-01 to 2024-06-30 - no overlap
        self.assertEqual(contract_flags.iloc[1], 0)  # 2024-07-01 to 2024-12-31 - no overlap
        self.assertEqual(contract_flags.iloc[2], 1)  # 2025-01-01 to 2025-06-30 - overlaps
        self.assertEqual(contract_flags.iloc[3], 1)  # 2025-07-01 to 2025-12-31 - overlaps
        self.assertEqual(contract_flags.iloc[4], 1)  # 2026-01-01 to 2026-06-30 - overlaps
        self.assertEqual(contract_flags.iloc[5], 0)  # 2026-07-01 to 2026-12-31 - no overlap
        self.assertEqual(contract_flags.iloc[6], 0)  # 2027-01-01 to 2027-06-30 - no overlap
        self.assertEqual(contract_flags.iloc[7], 0)  # 2027-07-01 to 2027-12-31 - no overlap
        self.assertEqual(contract_flags.iloc[8], 0)  # 2028-01-01 to 2028-06-30 - no overlap
        self.assertEqual(contract_flags.iloc[9], 0)  # 2028-07-01 to 2028-12-31 - no overlap

    def test_set_flag_values_edge_cases(self):
        """Test _set_flag_values with edge cases"""
        # Test with exact boundary matches
        self.mock_instance.flag_dict = {
            'exact_start': ('2024-01-01', '2024-01-01'),  # Single day at start
            'exact_end': ('2024-06-30', '2024-06-30'),    # Single day at end
            'partial_overlap_start': ('2023-12-01', '2024-03-01'),  # Overlaps start
            'partial_overlap_end': ('2024-05-01', '2024-08-01')     # Overlaps end
        }
        
        model_start, model_end = self.flags_manager._parse_model_dates()
        self.flags_manager._initialize_flags()
        self.flags_manager._set_flag_values(model_start, model_end)
        
        flags_dict = self.mock_instance.financial_model['flags']
        
        # exact_start should be active for first period only
        exact_start_flags = flags_dict['exact_start']
        self.assertEqual(exact_start_flags.iloc[0], 1)  # Includes 2024-01-01
        self.assertEqual(exact_start_flags.iloc[1], 0)  # Doesn't include 2024-01-01
        
        # exact_end should be active for first period only
        exact_end_flags = flags_dict['exact_end']
        self.assertEqual(exact_end_flags.iloc[0], 1)  # Includes 2024-06-30
        self.assertEqual(exact_end_flags.iloc[1], 0)  # Doesn't include 2024-06-30
    
    def test_set_start_year_flag(self):
        """Test the _set_start_year_flag method"""
        model_start, model_end = self.flags_manager._parse_model_dates()
        self.flags_manager._initialize_flags()
        self.flags_manager._set_start_year_flag(model_start)
        
        flags_dict = self.mock_instance.financial_model['flags']
        start_year_flags = flags_dict['start_year']
        
        # Check that January starts get flag = 1, others get flag = 0
        self.assertEqual(start_year_flags.iloc[0], 1)  # 2024-01-01 - January
        self.assertEqual(start_year_flags.iloc[1], 0)  # 2024-07-01 - July
        self.assertEqual(start_year_flags.iloc[2], 1)  # 2025-01-01 - January
        self.assertEqual(start_year_flags.iloc[3], 0)  # 2025-07-01 - July
        self.assertEqual(start_year_flags.iloc[4], 1)  # 2026-01-01 - January
        self.assertEqual(start_year_flags.iloc[5], 0)  # 2026-07-01 - July
        self.assertEqual(start_year_flags.iloc[6], 1)  # 2027-01-01 - January
        self.assertEqual(start_year_flags.iloc[7], 0)  # 2027-07-01 - July
        self.assertEqual(start_year_flags.iloc[8], 1)  # 2028-01-01 - January
        self.assertEqual(start_year_flags.iloc[9], 0)  # 2028-07-01 - July
    
    def test_flag_values_data_types(self):
        """Test that all flag values are integers (0 or 1)"""
        self.flags_manager.initialize()
        flags_dict = self.mock_instance.financial_model['flags']
        
        for flag_name, flag_series in flags_dict.items():
            with self.subTest(flag_name=flag_name):
                # Check that all values are integers
                self.assertTrue(pd.api.types.is_integer_dtype(flag_series))
                
                # Check that all values are 0 or 1
                unique_values = flag_series.unique()
                for value in unique_values:
                    self.assertIn(value, [0, 1])
    
    def test_full_integration(self):
        """Test the complete workflow integration"""
        # Test with realistic project timeline
        self.mock_instance.flag_dict = {
            'construction': ('2024-01-01', '2024-12-31'),
            'operations': ('2025-01-01', '2027-12-31'),
            'debt_service': ('2025-01-01', '2027-12-31'),
            'maintenance': ('2025-01-01', '2027-12-31')
        }
        
        self.flags_manager.initialize()
        flags_dict = self.mock_instance.financial_model['flags']
        
        # Validate logical flag patterns
        construction_flags = flags_dict['construction']
        operations_flags = flags_dict['operations']
        
        # Construction should be active in 2024, inactive afterwards
        self.assertEqual(construction_flags.iloc[0], 1)  # 2024-01
        self.assertEqual(construction_flags.iloc[1], 1)  # 2024-07
        self.assertEqual(construction_flags.iloc[2], 0)  # 2025-01
        self.assertEqual(construction_flags.iloc[3], 0)  # 2025-07
        
        # Operations should be inactive in 2024, active in 2025-2027
        self.assertEqual(operations_flags.iloc[0], 0)  # 2024-01
        self.assertEqual(operations_flags.iloc[1], 0)  # 2024-07
        self.assertEqual(operations_flags.iloc[2], 1)  # 2025-01
        self.assertEqual(operations_flags.iloc[3], 1)  # 2025-07
        self.assertEqual(operations_flags.iloc[4], 1)  # 2026-01
        self.assertEqual(operations_flags.iloc[5], 1)  # 2026-07
        self.assertEqual(operations_flags.iloc[6], 1)  # 2027-01
        self.assertEqual(operations_flags.iloc[7], 1)  # 2027-07
        self.assertEqual(operations_flags.iloc[8], 0)  # 2028-01
        self.assertEqual(operations_flags.iloc[9], 0)  # 2028-07

    
def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
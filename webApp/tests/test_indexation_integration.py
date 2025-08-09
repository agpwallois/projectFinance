import unittest
from unittest.mock import Mock, patch
from decimal import Decimal
import decimal
import pandas as pd
import numpy as np

from financial_model.financial_model_sections.indexation import Indexation


class TestIndexationIntegration(unittest.TestCase):
    """Integration and advanced test cases for the Indexation class."""
    
    def setUp(self):
        """Set up test fixtures for integration tests."""
        self.mock_instance = Mock()
        
        # Create a more realistic financial model structure with semi-annual periods
        # Semi-annual periods over 15 years (30 periods)
        # First half of year typically has fewer days than second half
        semi_annual_years = []
        for year in range(15):
            # Start of year
            semi_annual_years.append(float(year))
            # Mid-year (slightly less than 0.5 due to fewer days in first half)
            semi_annual_years.append(year + 0.496)
        
        self.mock_instance.financial_model = {
            'time_series': {
                'years_from_base_dates': {
                    'merchant_indexation': semi_annual_years,
                    'contract_indexation': semi_annual_years,
                    'opex_indexation': semi_annual_years,
                    'lease_indexation': semi_annual_years
                }
            }
        }
        
        # Mock project with realistic values
        self.mock_instance.project = Mock()
        self.mock_instance.project.index_rate_merchant = 2.5
        self.mock_instance.project.index_rate_contract = 2.0
        self.mock_instance.project.index_rate_opex = 3.0
        self.mock_instance.project.index_rate_lease = 1.5
        
        self.indexation = Indexation(self.mock_instance)
    
    def test_long_term_indexation(self):
        """Test indexation over a long period (15 years with semi-annual periods)."""
        self.indexation.initialize(sensi_inflation=0)
        
        # Check merchant indexation after ~15 years (last period)
        merchant_last = self.indexation.financial_model['indexation']['merchant'].iloc[-1]
        # The last period should be approximately 15 years
        years_elapsed = self.mock_instance.financial_model['time_series']['years_from_base_dates']['merchant_indexation'][-1]
        expected = (1.025 ** years_elapsed)
        self.assertAlmostEqual(merchant_last, expected, places=4)
        
        # Verify monotonic increase
        merchant_series = self.indexation.financial_model['indexation']['merchant']
        self.assertTrue(merchant_series.is_monotonic_increasing)
    
    def test_sensitivity_scenarios(self):
        """Test various inflation sensitivity scenarios."""
        scenarios = [
            {'sensitivity': -1.0, 'description': 'Deflation scenario'},
            {'sensitivity': 0.0, 'description': 'Base case'},
            {'sensitivity': 2.0, 'description': 'High inflation'},
            {'sensitivity': 5.0, 'description': 'Hyperinflation'}
        ]
        
        results = {}
        for scenario in scenarios:
            self.indexation.initialize(sensi_inflation=scenario['sensitivity'])
            results[scenario['description']] = {
                'merchant_10y': self.indexation.financial_model['indexation']['merchant'].iloc[10],
                'opex_10y': self.indexation.financial_model['indexation']['opex'].iloc[10]
            }
        
        # Verify relationships between scenarios
        self.assertLess(results['Deflation scenario']['merchant_10y'], 
                       results['Base case']['merchant_10y'])
        self.assertLess(results['Base case']['merchant_10y'], 
                       results['High inflation']['merchant_10y'])
        self.assertLess(results['High inflation']['merchant_10y'], 
                       results['Hyperinflation']['merchant_10y'])
    
    def test_compound_effect_verification(self):
        """Verify compound effect calculations are correct."""
        self.indexation.initialize(sensi_inflation=0)
        
        # Manually calculate some values to verify
        for indice in ['merchant', 'contract', 'opex', 'lease']:
            rate = getattr(self.mock_instance.project, f'index_rate_{indice}') / 100
            series = self.indexation.financial_model['indexation'][indice]
            years_from_base = self.mock_instance.financial_model['time_series']['years_from_base_dates'][f'{indice}_indexation']
            
            # Check specific periods (not years)
            for period in [0, 5, 10, 15, 20]:
                if period < len(series):
                    years = years_from_base[period]
                    expected = (1 + rate) ** years
                    actual = series.iloc[period]
                    self.assertAlmostEqual(actual, expected, places=6,
                        msg=f"Failed for {indice} at period {period} ({years} years)")
    
    def test_consistency_across_multiple_initializations(self):
        """Test that multiple initializations produce consistent results."""
        # First initialization
        self.indexation.initialize(sensi_inflation=1.5)
        first_result = self.indexation.financial_model['indexation']['merchant'].copy()
        
        # Second initialization with same parameters
        self.indexation.initialize(sensi_inflation=1.5)
        second_result = self.indexation.financial_model['indexation']['merchant']
        
        pd.testing.assert_series_equal(first_result, second_result)
    
    def test_boundary_conditions(self):
        """Test boundary conditions and edge cases."""
        test_cases = [
            {'rate': 0.0, 'sensitivity': 0.0, 'description': 'Zero indexation'},
            {'rate': 100.0, 'sensitivity': 0.0, 'description': '100% indexation'},
            {'rate': 2.0, 'sensitivity': -2.0, 'description': 'Net zero indexation'},
            {'rate': 0.01, 'sensitivity': 0.0, 'description': 'Very small indexation'}
        ]
        
        for test_case in test_cases:
            # Set all rates to the test rate
            for indice in ['merchant', 'contract', 'opex', 'lease']:
                setattr(self.mock_instance.project, f'index_rate_{indice}', test_case['rate'])
            
            self.indexation.initialize(sensi_inflation=test_case['sensitivity'])
            
            # Verify results make sense
            merchant_series = self.indexation.financial_model['indexation']['merchant']
            
            if test_case['rate'] + test_case['sensitivity'] == 0:
                # Should be all 1.0
                self.assertTrue(all(merchant_series == 1.0))
            elif test_case['rate'] + test_case['sensitivity'] > 0:
                # Should be increasing
                self.assertTrue(merchant_series.is_monotonic_increasing)
            else:
                # Should be decreasing
                self.assertTrue(merchant_series.is_monotonic_decreasing)
    
    def test_precision_for_financial_calculations(self):
        """Test that precision is maintained for financial calculations."""
        # Use precise decimal values
        self.mock_instance.project.index_rate_merchant = 2.123456789
        
        self.indexation.initialize(sensi_inflation=0.876543211)
        
        # The combined rate should be (2.123456789 + 0.876543211) / 100 = 0.03
        expected_rate = 0.03
        
        # Check period 10 calculation (not year 10)
        years_at_period_10 = self.mock_instance.financial_model['time_series']['years_from_base_dates']['merchant_indexation'][10]
        expected_at_period_10 = (1 + expected_rate) ** years_at_period_10
        actual_at_period_10 = self.indexation.financial_model['indexation']['merchant'].iloc[10]
        
        # Financial calculations typically need 4-6 decimal places
        self.assertAlmostEqual(actual_at_period_10, expected_at_period_10, places=6)
    
    def test_performance_with_large_datasets(self):
        """Test performance with very long time series."""
        # Create 100-year time series
        long_years = list(range(0, 100))
        self.mock_instance.financial_model['time_series']['years_from_base_dates'] = {
            'merchant_indexation': long_years,
            'contract_indexation': long_years,
            'opex_indexation': long_years,
            'lease_indexation': long_years
        }
        
        import time
        start_time = time.time()
        self.indexation.initialize(sensi_inflation=0)
        end_time = time.time()
        
        # Should complete in reasonable time (less than 1 second)
        self.assertLess(end_time - start_time, 1.0)
        
        # Verify all series have correct length
        for indice in ['merchant', 'contract', 'opex', 'lease']:
            self.assertEqual(len(self.indexation.financial_model['indexation'][indice]), 100)
    
    def test_negative_years_handling(self):
        """Test handling of negative years (historical data)."""
        # Include some negative years
        years_with_history = list(range(-5, 25))  # -5 to 24
        self.mock_instance.financial_model['time_series']['years_from_base_dates'] = {
            'merchant_indexation': years_with_history,
            'contract_indexation': years_with_history,
            'opex_indexation': years_with_history,
            'lease_indexation': years_with_history
        }
        
        self.indexation.initialize(sensi_inflation=0)
        
        merchant_series = self.indexation.financial_model['indexation']['merchant']
        
        # Negative years should have values less than 1
        for i, year in enumerate(years_with_history):
            if year < 0:
                self.assertLess(merchant_series.iloc[i], 1.0)
            elif year == 0:
                self.assertAlmostEqual(merchant_series.iloc[i], 1.0)
            else:
                self.assertGreater(merchant_series.iloc[i], 1.0)
    
    def test_partial_year_handling(self):
        """Test handling of fractional years."""
        # Include fractional years
        fractional_years = [0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
        self.mock_instance.financial_model['time_series']['years_from_base_dates'] = {
            'merchant_indexation': fractional_years,
            'contract_indexation': fractional_years,
            'opex_indexation': fractional_years,
            'lease_indexation': fractional_years
        }
        
        self.indexation.initialize(sensi_inflation=0)
        
        merchant_series = self.indexation.financial_model['indexation']['merchant']
        rate = 0.025  # 2.5%
        
        # Check fractional year calculations
        self.assertAlmostEqual(merchant_series.iloc[1], (1 + rate) ** 0.25, places=6)
        self.assertAlmostEqual(merchant_series.iloc[2], (1 + rate) ** 0.5, places=6)
        self.assertAlmostEqual(merchant_series.iloc[3], (1 + rate) ** 0.75, places=6)
    
    def test_error_propagation(self):
        """Test that errors in input data are handled appropriately."""
        # Test with None values
        self.mock_instance.project.index_rate_merchant = None
        
        with self.assertRaises(TypeError):
            self.indexation.initialize(sensi_inflation=0)
        
        # Test with string values
        self.mock_instance.project.index_rate_merchant = 2.5  # Use numeric value
        # Test with valid numeric value
        self.indexation.initialize(sensi_inflation=0)
        
        # Test with invalid string
        self.mock_instance.project.index_rate_merchant = "invalid"
        with self.assertRaises((ValueError, TypeError, decimal.InvalidOperation)):
            self.indexation.initialize(sensi_inflation=0)
    
    @patch('pandas.Series')
    def test_pandas_series_creation(self, mock_series):
        """Test that pandas Series are created correctly."""
        # Set up mock to track calls
        mock_series.return_value = pd.Series([1.0])
        
        self.indexation._compute_indexation_vector(0.02, pd.Series([0]))
        
        # Verify Series was called with correct arguments
        mock_series.assert_called()
    
    def test_memory_efficiency(self):
        """Test memory efficiency of indexation vectors."""
        self.indexation.initialize(sensi_inflation=0)
        
        # Check that all series use float dtype (more memory efficient than object)
        for indice in ['merchant', 'contract', 'opex', 'lease']:
            series = self.indexation.financial_model['indexation'][indice]
            self.assertEqual(series.dtype, np.float64)
    
    def test_mathematical_properties(self):
        """Test mathematical properties of indexation."""
        self.indexation.initialize(sensi_inflation=0)
        
        merchant_series = self.indexation.financial_model['indexation']['merchant']
        years_series = self.mock_instance.financial_model['time_series']['years_from_base_dates']['merchant_indexation']
        
        # Test that indexation follows the compound formula correctly
        rate = 0.025
        for i in range(len(merchant_series)):
            years = years_series[i]
            expected = (1 + rate) ** years
            actual = merchant_series.iloc[i]
            self.assertAlmostEqual(actual, expected, places=6, 
                                 msg=f"Failed at index {i} with {years} years")
    
    def test_real_world_scenario(self):
        """Test a real-world scenario with mixed inflation rates."""
        # Set realistic different rates for different indices
        self.mock_instance.project.index_rate_merchant = 2.5  # Energy prices
        self.mock_instance.project.index_rate_contract = 2.0  # CPI
        self.mock_instance.project.index_rate_opex = 3.0     # Labor costs
        self.mock_instance.project.index_rate_lease = 1.5    # Real estate
        
        # Apply a sensitivity for stress testing
        self.indexation.initialize(sensi_inflation=0.5)
        
        # After ~10 years (period 20 for semi-annual), verify relative differences
        period_20_idx = 20
        merchant_20 = self.indexation.financial_model['indexation']['merchant'].iloc[period_20_idx]
        contract_20 = self.indexation.financial_model['indexation']['contract'].iloc[period_20_idx]
        opex_20 = self.indexation.financial_model['indexation']['opex'].iloc[period_20_idx]
        lease_20 = self.indexation.financial_model['indexation']['lease'].iloc[period_20_idx]
        
        # OPEX should have highest growth, lease lowest
        self.assertGreater(opex_20, merchant_20)
        self.assertGreater(merchant_20, contract_20)
        self.assertGreater(contract_20, lease_20)
    
    def test_different_periodicities(self):
        """Test indexation with different periodicities (annual, semi-annual, quarterly)."""
        rate = 0.025  # 2.5% annual
        
        # Test 1: Annual periodicity (5 years)
        annual_years = [0, 1, 2, 3, 4, 5]
        self.mock_instance.financial_model['time_series']['years_from_base_dates'] = {
            'merchant_indexation': annual_years,
            'contract_indexation': annual_years,
            'opex_indexation': annual_years,
            'lease_indexation': annual_years
        }
        self.indexation.initialize(sensi_inflation=0)
        annual_5y = self.indexation.financial_model['indexation']['merchant'].iloc[-1]
        
        # Test 2: Semi-annual periodicity (10 periods = 5 years)
        semi_annual_years = [0, 0.496, 1.0, 1.496, 2.0, 2.496, 3.0, 3.496, 4.0, 4.496, 5.0]
        self.mock_instance.financial_model['time_series']['years_from_base_dates'] = {
            'merchant_indexation': semi_annual_years,
            'contract_indexation': semi_annual_years,
            'opex_indexation': semi_annual_years,
            'lease_indexation': semi_annual_years
        }
        self.indexation.initialize(sensi_inflation=0)
        semi_annual_5y = self.indexation.financial_model['indexation']['merchant'].iloc[-1]
        
        # Test 3: Quarterly periodicity (20 periods = 5 years)
        quarterly_years = []
        for year in range(6):  # 0 to 5 years
            if year < 5:
                # Q1 and Q3 typically have fewer days
                quarterly_years.extend([
                    year,  # Start of year
                    year + 0.247,  # End of Q1
                    year + 0.496,  # End of Q2 (mid-year)
                    year + 0.745   # End of Q3
                ])
            else:
                quarterly_years.append(5.0)  # Exactly 5 years at the end
        
        self.mock_instance.financial_model['time_series']['years_from_base_dates'] = {
            'merchant_indexation': quarterly_years,
            'contract_indexation': quarterly_years,
            'opex_indexation': quarterly_years,
            'lease_indexation': quarterly_years
        }
        self.indexation.initialize(sensi_inflation=0)
        quarterly_5y = self.indexation.financial_model['indexation']['merchant'].iloc[-1]
        
        # All should give approximately the same result at 5 years
        # Annual: exactly (1.025)^5
        # Semi-annual and quarterly: approximately (1.025)^5 with small variations
        expected_5y = 1.025 ** 5
        
        self.assertAlmostEqual(annual_5y, expected_5y, places=10)
        self.assertAlmostEqual(semi_annual_5y, expected_5y, places=3)
        self.assertAlmostEqual(quarterly_5y, expected_5y, places=3)
        
        # The differences should be small
        self.assertLess(abs(annual_5y - semi_annual_5y), 0.001)
        self.assertLess(abs(annual_5y - quarterly_5y), 0.001)
    
    def test_leap_year_effect(self):
        """Test the effect of leap years on indexation."""
        # Create periods that span a leap year
        # Assume periods starting in 2023 (not leap) and 2024 (leap year)
        # Semi-annual periods with different day counts
        periods = [
            0,           # Start
            0.4932,      # 180/365 days (non-leap year first half)
            1.0055,      # 365/365 + 184/366 (spans into leap year)
            1.5027,      # Previous + 182/366 (leap year second half)
            2.0000       # Exactly 2 years
        ]
        
        self.mock_instance.financial_model['time_series']['years_from_base_dates'] = {
            'merchant_indexation': periods,
            'contract_indexation': periods,
            'opex_indexation': periods,
            'lease_indexation': periods
        }
        
        self.indexation.initialize(sensi_inflation=0)
        
        # Check that indexation correctly handles the fractional years
        merchant_series = self.indexation.financial_model['indexation']['merchant']
        
        # Verify calculations at each period
        for i, years in enumerate(periods):
            expected = 1.025 ** years
            actual = merchant_series.iloc[i]
            self.assertAlmostEqual(actual, expected, places=6,
                msg=f"Failed at period {i} with {years} years")


if __name__ == '__main__':
    unittest.main()
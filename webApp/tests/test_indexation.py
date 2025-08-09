import unittest
from unittest.mock import Mock, MagicMock, patch
from decimal import Decimal
import pandas as pd
import numpy as np

from financial_model.financial_model_sections.indexation import Indexation


class TestIndexation(unittest.TestCase):
    """Test cases for the Indexation class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_instance = Mock()
        
        # Semi-annual periodicity: years_from_base_dates contains fractional years
        # For semi-annual: ~0.5 years per period but exactly 1.0 at year boundaries
        # Example: Jan-Jun has 181 days, Jul-Dec has 184 days (non-leap year)
        self.mock_instance.financial_model = {
            'time_series': {
                'years_from_base_dates': {
                    'merchant_indexation': [0, 0.496, 1.0, 1.496, 2.0],  # Semi-annual with actual days
                    'contract_indexation': [0, 0.496, 1.0, 1.496, 2.0],
                    'opex_indexation': [0, 0.496, 1.0, 1.496, 2.0],
                    'lease_indexation': [0, 0.496, 1.0, 1.496, 2.0]
                }
            }
        }
        
        # Mock project attributes
        self.mock_instance.project = Mock()
        self.mock_instance.project.index_rate_merchant = 2.0
        self.mock_instance.project.index_rate_contract = 2.5
        self.mock_instance.project.index_rate_opex = 3.0
        self.mock_instance.project.index_rate_lease = 1.5
        
        self.indexation = Indexation(self.mock_instance)
    
    def test_init(self):
        """Test Indexation initialization."""
        self.assertEqual(self.indexation.instance, self.mock_instance)
        self.assertEqual(self.indexation.financial_model, self.mock_instance.financial_model)
    
    def test_get_index_columns(self):
        """Test _get_index_columns returns correct mapping."""
        expected = {
            'merchant': 'merchant_indexation',
            'contract': 'contract_indexation',
            'opex': 'opex_indexation',
            'lease': 'lease_indexation'
        }
        result = self.indexation._get_index_columns()
        self.assertEqual(result, expected)
    
    def test_initialize_indexation_section_creates_section(self):
        """Test _initialize_indexation_section creates section when missing."""
        # Remove indexation section if it exists
        if 'indexation' in self.indexation.financial_model:
            del self.indexation.financial_model['indexation']
        
        self.indexation._initialize_indexation_section()
        
        self.assertIn('indexation', self.indexation.financial_model)
        self.assertEqual(self.indexation.financial_model['indexation'], {})
    
    def test_initialize_indexation_section_preserves_existing(self):
        """Test _initialize_indexation_section preserves existing section."""
        # Add existing data
        self.indexation.financial_model['indexation'] = {'existing': 'data'}
        
        self.indexation._initialize_indexation_section()
        
        self.assertEqual(self.indexation.financial_model['indexation'], {'existing': 'data'})
    
    def test_calculate_indexation_rate_no_sensitivity(self):
        """Test _calculate_indexation_rate without inflation sensitivity."""
        rate = self.indexation._calculate_indexation_rate('merchant', 0)
        self.assertAlmostEqual(rate, 0.02)  # 2.0 / 100
        
        rate = self.indexation._calculate_indexation_rate('contract', 0)
        self.assertAlmostEqual(rate, 0.025)  # 2.5 / 100
    
    def test_calculate_indexation_rate_with_sensitivity(self):
        """Test _calculate_indexation_rate with inflation sensitivity."""
        # Test positive sensitivity
        rate = self.indexation._calculate_indexation_rate('merchant', 1.0)
        self.assertAlmostEqual(rate, 0.03)  # (2.0 + 1.0) / 100
        
        # Test negative sensitivity
        rate = self.indexation._calculate_indexation_rate('opex', -0.5)
        self.assertAlmostEqual(rate, 0.025)  # (3.0 - 0.5) / 100
    
    def test_calculate_indexation_rate_decimal_precision(self):
        """Test _calculate_indexation_rate maintains decimal precision."""
        # Test with precise decimal values
        self.mock_instance.project.index_rate_merchant = 2.123456789
        rate = self.indexation._calculate_indexation_rate('merchant', 0.876543211)
        expected = (Decimal('2.123456789') + Decimal('0.876543211')) / 100
        self.assertAlmostEqual(Decimal(str(rate)), expected, places=9)
    
    def test_get_indexation_years(self):
        """Test _get_indexation_years returns correct series with fractional years."""
        result = self.indexation._get_indexation_years('merchant_indexation')
        expected = pd.Series([0, 0.496, 1.0, 1.496, 2.0])
        pd.testing.assert_series_equal(result, expected)
    
    def test_compute_indexation_vector_with_fractional_years(self):
        """Test _compute_indexation_vector calculation with fractional years (semi-annual)."""
        indexation_rate = 0.02  # 2%
        # Semi-annual periods with actual days
        years = pd.Series([0, 0.496, 1.0, 1.496, 2.0])
        
        result = self.indexation._compute_indexation_vector(indexation_rate, years)
        # Expected values calculated as (1 + 0.02)^years
        expected = pd.Series([
            1.0,
            1.02**0.496,
            1.02**1.0,
            1.02**1.496,
            1.02**2.0
        ])
        
        pd.testing.assert_series_equal(result, expected, check_exact=False, rtol=1e-6)
    
    def test_compute_indexation_vector_zero_rate(self):
        """Test _compute_indexation_vector with zero rate."""
        indexation_rate = 0.0
        years = pd.Series([0, 0.496, 1.0, 1.496, 2.0])
        
        result = self.indexation._compute_indexation_vector(indexation_rate, years)
        expected = pd.Series([1.0, 1.0, 1.0, 1.0, 1.0])
        
        pd.testing.assert_series_equal(result, expected)
    
    def test_compute_indexation_vector_negative_rate(self):
        """Test _compute_indexation_vector with negative rate."""
        indexation_rate = -0.01  # -1%
        years = pd.Series([0, 0.496, 1.0, 1.496])
        
        result = self.indexation._compute_indexation_vector(indexation_rate, years)
        expected = pd.Series([1.0, 0.99**0.496, 0.99**1.0, 0.99**1.496])
        
        pd.testing.assert_series_equal(result, expected, check_exact=False, rtol=1e-6)
    
    def test_create_indexation_vectors(self):
        """Test _create_indexation_vectors creates all vectors."""
        index_columns = self.indexation._get_index_columns()
        self.indexation._initialize_indexation_section()
        self.indexation._create_indexation_vectors(index_columns, 0)
        
        # Check all indices are created
        for indice_name in ['merchant', 'contract', 'opex', 'lease']:
            self.assertIn(indice_name, self.indexation.financial_model['indexation'])
            result = self.indexation.financial_model['indexation'][indice_name]
            self.assertIsInstance(result, pd.Series)
            self.assertEqual(len(result), 5)  # Based on test data
    
    def test_initialize_full_flow(self):
        """Test complete initialization flow with semi-annual periods."""
        # Remove any existing indexation section
        if 'indexation' in self.indexation.financial_model:
            del self.indexation.financial_model['indexation']
        
        # Initialize with no sensitivity
        self.indexation.initialize(sensi_inflation=0)
        
        # Verify indexation section exists
        self.assertIn('indexation', self.indexation.financial_model)
        
        # Verify all indices are created with correct values for semi-annual periods
        # Merchant: 2% annual rate
        merchant_expected = pd.Series([
            1.0,
            1.02**0.496,
            1.02**1.0,
            1.02**1.496,
            1.02**2.0
        ])
        pd.testing.assert_series_equal(
            self.indexation.financial_model['indexation']['merchant'], 
            merchant_expected, 
            check_exact=False, 
            rtol=1e-6
        )
        
        # Contract: 2.5% annual rate
        contract_expected = pd.Series([
            1.0,
            1.025**0.496,
            1.025**1.0,
            1.025**1.496,
            1.025**2.0
        ])
        pd.testing.assert_series_equal(
            self.indexation.financial_model['indexation']['contract'], 
            contract_expected, 
            check_exact=False, 
            rtol=1e-6
        )
    
    def test_initialize_with_sensitivity(self):
        """Test initialization with inflation sensitivity."""
        self.indexation.initialize(sensi_inflation=1.0)
        
        # Merchant: 2.0 + 1.0 = 3.0% annual rate
        merchant_expected = pd.Series([
            1.0,
            1.03**0.496,
            1.03**1.0,
            1.03**1.496,
            1.03**2.0
        ])
        pd.testing.assert_series_equal(
            self.indexation.financial_model['indexation']['merchant'], 
            merchant_expected, 
            check_exact=False, 
            rtol=1e-6
        )
    
    def test_missing_project_attribute(self):
        """Test handling of missing project attributes."""
        # Remove an attribute
        delattr(self.mock_instance.project, 'index_rate_merchant')
        
        with self.assertRaises(AttributeError):
            self.indexation._calculate_indexation_rate('merchant', 0)
    
    def test_missing_time_series_data(self):
        """Test handling of missing time series data."""
        # Remove time series data
        del self.indexation.financial_model['time_series']['years_from_base_dates']['merchant_indexation']
        
        with self.assertRaises(KeyError):
            self.indexation._get_indexation_years('merchant_indexation')
    
    def test_different_length_years(self):
        """Test handling of different length year arrays."""
        # Set different lengths for different indices
        self.indexation.financial_model['time_series']['years_from_base_dates'] = {
            'merchant_indexation': [0, 1, 2],
            'contract_indexation': [0, 1, 2, 3, 4, 5],
            'opex_indexation': [0],
            'lease_indexation': [0, 1]
        }
        
        self.indexation.initialize(sensi_inflation=0)
        
        # Verify different lengths are handled correctly
        self.assertEqual(len(self.indexation.financial_model['indexation']['merchant']), 3)
        self.assertEqual(len(self.indexation.financial_model['indexation']['contract']), 6)
        self.assertEqual(len(self.indexation.financial_model['indexation']['opex']), 1)
        self.assertEqual(len(self.indexation.financial_model['indexation']['lease']), 2)
    
    def test_float_conversion(self):
        """Test that all results are properly converted to float."""
        self.indexation.initialize(sensi_inflation=0)
        
        for indice_name in ['merchant', 'contract', 'opex', 'lease']:
            series = self.indexation.financial_model['indexation'][indice_name]
            # Check dtype is float
            self.assertTrue(np.issubdtype(series.dtype, np.floating))
    
    def test_edge_case_high_inflation(self):
        """Test with very high inflation rate."""
        self.mock_instance.project.index_rate_merchant = 50.0  # 50%
        self.indexation.initialize(sensi_inflation=0)
        
        # Period 4 is at exactly 2.0 years: (1 + 0.5)^2.0
        expected_period_4 = 1.5 ** 2.0
        actual_period_4 = self.indexation.financial_model['indexation']['merchant'].iloc[4]
        self.assertAlmostEqual(actual_period_4, expected_period_4, places=4)
    
    def test_edge_case_large_sensitivity(self):
        """Test with large sensitivity adjustment."""
        # Original rate 2%, sensitivity 98% = 100% total
        self.indexation.initialize(sensi_inflation=98.0)
        
        # At period 2 (exactly 1 year): (1 + 1.0)^1.0
        expected_period_2 = 2.0 ** 1.0
        actual_period_2 = self.indexation.financial_model['indexation']['merchant'].iloc[2]
        self.assertAlmostEqual(actual_period_2, expected_period_2, places=4)
    
    def test_quarterly_periodicity(self):
        """Test indexation with quarterly periodicity."""
        # Set up quarterly periods (Q1 and Q3 typically have fewer days)
        self.indexation.financial_model['time_series']['years_from_base_dates'] = {
            'merchant_indexation': [0, 0.247, 0.496, 0.745, 1.0, 1.247, 1.496, 1.745, 2.0],
            'contract_indexation': [0, 0.247, 0.496, 0.745, 1.0, 1.247, 1.496, 1.745, 2.0],
            'opex_indexation': [0, 0.247, 0.496, 0.745, 1.0, 1.247, 1.496, 1.745, 2.0],
            'lease_indexation': [0, 0.247, 0.496, 0.745, 1.0, 1.247, 1.496, 1.745, 2.0]
        }
        
        self.indexation.initialize(sensi_inflation=0)
        
        # Verify quarterly indexation
        merchant_series = self.indexation.financial_model['indexation']['merchant']
        
        # Check some specific quarters
        self.assertAlmostEqual(merchant_series.iloc[0], 1.0)
        self.assertAlmostEqual(merchant_series.iloc[1], 1.02**0.247, places=6)  # Q1
        self.assertAlmostEqual(merchant_series.iloc[4], 1.02**1.0, places=6)  # End of year 1
        self.assertAlmostEqual(merchant_series.iloc[8], 1.02**2.0, places=6)  # End of year 2
    
    def test_semi_annual_vs_quarterly_consistency(self):
        """Test that semi-annual and quarterly give consistent results at year boundaries."""
        # Semi-annual setup (already in setUp)
        self.indexation.initialize(sensi_inflation=0)
        semi_annual_year2 = self.indexation.financial_model['indexation']['merchant'].iloc[4]  # ~2 years
        
        # Quarterly setup ending at exactly 2 years
        self.indexation.financial_model['time_series']['years_from_base_dates'] = {
            'merchant_indexation': [0, 0.247, 0.496, 0.745, 1.0, 1.247, 1.496, 1.745, 2.0],
            'contract_indexation': [0, 0.247, 0.496, 0.745, 1.0, 1.247, 1.496, 1.745, 2.0],
            'opex_indexation': [0, 0.247, 0.496, 0.745, 1.0, 1.247, 1.496, 1.745, 2.0],
            'lease_indexation': [0, 0.247, 0.496, 0.745, 1.0, 1.247, 1.496, 1.745, 2.0]
        }
        
        self.indexation.initialize(sensi_inflation=0)
        quarterly_year2 = self.indexation.financial_model['indexation']['merchant'].iloc[8]  # ~2 years
        
        # Both should give the same result at ~2 years
        self.assertAlmostEqual(semi_annual_year2, quarterly_year2, places=6)
    
    def test_actual_days_effect(self):
        """Test the effect of actual days vs uniform periods."""
        # Uniform semi-annual (exactly 0.5 years)
        uniform_years = [0, 0.5, 1.0, 1.5, 2.0]
        
        # Actual semi-annual (varies due to calendar days)
        actual_years = [0, 0.496, 1.0, 1.496, 2.0]
        
        rate = 0.02
        uniform_indexation = pd.Series([(1 + rate) ** y for y in uniform_years])
        actual_indexation = pd.Series([(1 + rate) ** y for y in actual_years])
        
        # The differences should be small but noticeable
        differences = abs(uniform_indexation - actual_indexation)
        
        # First period should be identical
        self.assertEqual(differences.iloc[0], 0.0)
        
        # Later periods should have small differences due to actual days
        self.assertGreater(differences.iloc[1], 0)
        self.assertLess(differences.iloc[1], 0.001)  # Small difference
        
        # Final values should be identical (both exactly 2 years)
        self.assertEqual(differences.iloc[4], 0.0)


if __name__ == '__main__':
    unittest.main()
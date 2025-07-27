import unittest
import numpy as np
from unittest.mock import Mock, MagicMock

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

from financial_model.financial_model_sections.dsra import FinancialModelDSRA, calc_dsra_target, calc_dsra_funding


class TestDSRA(TestCase):
    
    def setUp(self):
        """Set up test fixtures with mock instance and financial model data."""
        self.mock_instance = Mock()
        self.mock_instance.dsra = 12  # 12 months DSRA coverage
        self.mock_instance.periodicity = 3  # Quarterly periods
        
        # Create mock financial model structure
        self.mock_instance.financial_model = {
            'senior_debt': {
                'repayments': np.array([0, 100, 100, 100, 50]),
                'interests_operations': np.array([0, 20, 18, 15, 5]),
                'DS_effective': np.zeros(5)  # Will be calculated
            },
            'DSRA': {
                'cash_available_for_dsra': np.zeros(5),
                'dsra_target': np.zeros(5),
                'initial_funding': np.zeros(5),
                'dsra_bop': np.zeros(5),
                'dsra_eop': np.zeros(5),
                'dsra_additions': np.zeros(5),
                'dsra_release': np.zeros(5),
                'dsra_mov': np.zeros(5)
            },
            'op_account': {
                'CFADS_amo': np.array([0, 150, 140, 130, 80])
            },
            'flags': {
                'debt_amo': np.array([0, 1, 1, 1, 1]),
                'construction_end': np.array([1, 0, 0, 0, 0])
            }
        }
        
        self.dsra_model = FinancialModelDSRA(self.mock_instance)

    def test_init_sets_references_correctly(self):
        """Test that __init__ properly sets up references to nested dictionaries."""
        self.assertEqual(self.dsra_model.instance, self.mock_instance)
        self.assertEqual(self.dsra_model.financial_model, self.mock_instance.financial_model)
        self.assertEqual(self.dsra_model.dsra, self.mock_instance.financial_model['DSRA'])
        self.assertEqual(self.dsra_model.senior_debt, self.mock_instance.financial_model['senior_debt'])
        self.assertEqual(self.dsra_model.flags, self.mock_instance.financial_model['flags'])

    def test_compute_senior_debt_effective(self):
        """Test calculation of effective debt service."""
        self.dsra_model._compute_senior_debt_effective()
        
        expected = np.array([0, 120, 118, 115, 55])  # repayments + interests
        np.testing.assert_array_equal(
            self.dsra_model.senior_debt['DS_effective'], 
            expected
        )

    def test_compute_dsra_cash_flow(self):
        """Test calculation of cash available for DSRA."""
        # Set up effective debt service first
        self.dsra_model.senior_debt['DS_effective'] = np.array([0, 120, 118, 115, 55])
        
        self.dsra_model._compute_dsra_cash_flow()
        
        expected = np.array([0, 30, 22, 15, 25])  # max(CFADS_amo - DS_effective, 0)
        np.testing.assert_array_equal(
            self.dsra_model.dsra['cash_available_for_dsra'],
            expected
        )

    def test_compute_dsra_target(self):
        """Test calculation of DSRA target amounts."""
        self.dsra_model.senior_debt['DS_effective'] = np.array([0, 120, 118, 115, 55])
        
        self.dsra_model._compute_dsra_target()
        
        # With 12 months DSRA and 3-month periodicity, look forward 4 periods
        # Period 0: sum([120, 118, 115, 55]) = 408
        # Period 1: sum([118, 115, 55]) = 288
        # Period 2: sum([115, 55]) = 170
        # Period 3: sum([55]) = 55
        # Period 4: sum([]) = 0
        expected_base = np.array([408, 288, 170, 55, 0])
        expected = expected_base * np.array([0, 1, 1, 1, 1])  # Apply debt_amo flag
        expected_final = np.array([0, 288, 170, 55, 0])
        
        np.testing.assert_array_equal(
            self.dsra_model.dsra['dsra_target'],
            expected_final
        )

    def test_compute_initial_funding(self):
        """Test calculation of initial DSRA funding."""
        self.dsra_model.dsra['dsra_target'] = np.array([0, 288, 170, 55, 0])
        
        self.dsra_model._compute_initial_funding()
        
        # First positive target is 288, applied only at construction end
        expected = np.array([288, 0, 0, 0, 0])
        np.testing.assert_array_equal(
            self.dsra_model.dsra['initial_funding'],
            expected
        )

    def test_compute_period_dsra_addition_needed(self):
        """Test DSRA calculation when addition is needed."""
        # Set up scenario where DSRA addition is required
        self.dsra_model.dsra['dsra_target'] = np.array([0, 200, 150, 100, 0])
        self.dsra_model.dsra['initial_funding'] = np.array([200, 0, 0, 0, 0])
        self.dsra_model.dsra['cash_available_for_dsra'] = np.array([0, 50, 40, 30, 20])
        
        # Initialize arrays
        for key in ['dsra_bop', 'dsra_eop', 'dsra_additions', 'dsra_release', 'dsra_mov']:
            self.dsra_model.dsra[key] = np.zeros(5)
        
        effective_target = self.dsra_model.dsra['dsra_target'] + self.dsra_model.dsra['initial_funding']
        
        # Test period 1 - need to add to reach target
        self.dsra_model.dsra['dsra_eop'][0] = 200  # Previous period ending
        self.dsra_model._compute_period_dsra(1, effective_target)
        
        self.assertEqual(self.dsra_model.dsra['dsra_bop'][1], 200)
        self.assertEqual(self.dsra_model.dsra['dsra_additions'][1], 0)  # Target already met
        self.assertEqual(self.dsra_model.dsra['dsra_eop'][1], 200)

    def test_compute_period_dsra_release_needed(self):
        """Test DSRA calculation when release is needed."""
        # Set up scenario where DSRA release is required
        self.dsra_model.dsra['dsra_target'] = np.array([0, 200, 150, 100, 0])
        self.dsra_model.dsra['initial_funding'] = np.array([0, 0, 0, 0, 0])
        
        # Initialize arrays
        for key in ['dsra_bop', 'dsra_eop', 'dsra_additions', 'dsra_release', 'dsra_mov']:
            self.dsra_model.dsra[key] = np.zeros(5)
        
        effective_target = self.dsra_model.dsra['dsra_target'] + self.dsra_model.dsra['initial_funding']
        
        # Test period 2 - current balance exceeds target, should release
        self.dsra_model.dsra['dsra_eop'][1] = 200  # Previous period ending
        self.dsra_model._compute_period_dsra(2, effective_target)
        
        self.assertEqual(self.dsra_model.dsra['dsra_bop'][2], 200)
        self.assertEqual(self.dsra_model.dsra['dsra_release'][2], 50)  # 200 - 150
        self.assertEqual(self.dsra_model.dsra['dsra_eop'][2], 150)

    def test_apply_target_ceiling(self):
        """Test that target ceiling is properly applied."""
        # Set up scenario where ending balance exceeds target
        self.dsra_model.dsra['dsra_eop'] = np.array([0, 0, 180, 0, 0])
        self.dsra_model.dsra['dsra_release'] = np.array([0, 0, 10, 0, 0])
        effective_target = np.array([0, 200, 150, 100, 0])
        
        self.dsra_model._apply_target_ceiling(2, effective_target)
        
        self.assertEqual(self.dsra_model.dsra['dsra_release'][2], 40)  # 10 + (180-150)
        self.assertEqual(self.dsra_model.dsra['dsra_eop'][2], 150)

    def test_update_initial_funding_max(self):
        """Test updating maximum initial funding on instance."""
        self.dsra_model.dsra['initial_funding'] = np.array([250, 0, 0, 0, 0])
        
        self.dsra_model._update_initial_funding_max()
        
        self.assertEqual(self.mock_instance.initial_funding_max, 250)

    def test_initialize_full_workflow(self):
        """Test the complete initialization workflow."""
        # This should run without errors and produce reasonable results
        self.dsra_model.initialize()
        
        # Verify that all computations have been performed
        self.assertGreater(np.sum(self.dsra_model.senior_debt['DS_effective']), 0)
        self.assertGreaterEqual(np.min(self.dsra_model.dsra['cash_available_for_dsra']), 0)
        self.assertTrue(hasattr(self.mock_instance, 'initial_funding_max'))


class TestDSRAUtilityFunctions(TestCase):
    """Test utility functions for DSRA calculations."""

    def test_calc_dsra_target_basic(self):
        """Test basic DSRA target calculation."""
        dsra_months = 6
        periodicity = 3  # Quarterly
        ds_effective = np.array([100, 120, 110, 130, 140])
        
        result = calc_dsra_target(dsra_months, periodicity, ds_effective)
        
        # With 6 months DSRA and 3-month periods, look forward 2 periods
        expected = [230, 240, 270, 140, 0]  # Sum of next 2 periods
        self.assertEqual(result, expected)

    def test_calc_dsra_target_edge_cases(self):
        """Test edge cases for DSRA target calculation."""
        # Test when look-forward exceeds array length
        dsra_months = 12
        periodicity = 3
        ds_effective = np.array([100, 120])
        
        result = calc_dsra_target(dsra_months, periodicity, ds_effective)
        
        expected = [120, 0]  # Can only look forward to available periods
        self.assertEqual(result, expected)

    def test_calc_dsra_funding_with_positive_targets(self):
        """Test DSRA funding calculation with positive targets."""
        dsra_target = np.array([0, 250, 200, 150, 100])
        
        result = calc_dsra_funding(dsra_target)
        
        self.assertEqual(result, 250)  # First positive value

    def test_calc_dsra_funding_all_zeros(self):
        """Test DSRA funding calculation with all zero targets."""
        dsra_target = np.array([0, 0, 0, 0, 0])
        
        result = calc_dsra_funding(dsra_target)
        
        self.assertEqual(result, 0)

    def test_calc_dsra_funding_empty_array(self):
        """Test DSRA funding calculation with empty array."""
        dsra_target = np.array([])
        
        result = calc_dsra_funding(dsra_target)
        
        self.assertEqual(result, 0)


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTest(unittest.makeSuite(TestDSRA))
    suite.addTest(unittest.makeSuite(TestDSRAUtilityFunctions))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
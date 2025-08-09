import unittest
from unittest.mock import Mock, MagicMock, patch
import numpy as np
import pandas as pd
import logging

from financial_model.financial_model_sections.financing_plan import (
    FinancingPlan, InjectionMethod
)


class TestInjectionMethod(unittest.TestCase):
    """Test cases for the InjectionMethod enum."""
    
    def test_injection_method_values(self):
        """Test that injection method enum has correct values."""
        self.assertEqual(InjectionMethod.EQUITY_FIRST.value, 1)
        self.assertEqual(InjectionMethod.PRO_RATA.value, 2)
        
    def test_injection_method_names(self):
        """Test that injection method enum has correct names."""
        self.assertEqual(InjectionMethod.EQUITY_FIRST.name, 'EQUITY_FIRST')
        self.assertEqual(InjectionMethod.PRO_RATA.name, 'PRO_RATA')


class TestFinancingPlan(unittest.TestCase):
    """Test cases for the FinancingPlan class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_model = Mock()
        self.mock_model.financial_model = {
            'uses': {
                'total': pd.Series([1000, 2000, 3000, 4000]),  # 10M total
                'total_cumul': pd.Series([1000, 3000, 6000, 10000])
            }
        }
        self.mock_model.senior_debt_amount = 7000  # 70% gearing
        self.mock_model.project = Mock()
        self.mock_model.project.injection_choice = 1  # EQUITY_FIRST
        self.mock_model.project.subgearing = 20.0  # 20%
        
        self.financing_plan = FinancingPlan(self.mock_model)
        
    def test_init(self):
        """Test FinancingPlan initialization."""
        self.assertEqual(self.financing_plan.model, self.mock_model)
        
    def test_initialize_sources(self):
        """Test initialization of sources data structure."""
        self.financing_plan._initialize_sources()
        
        self.assertIn('sources', self.mock_model.financial_model)
        self.assertEqual(self.mock_model.financial_model['sources'], {})
        
    def test_calculate_senior_debt_gearing(self):
        """Test senior debt gearing calculation."""
        self.financing_plan._calculate_senior_debt_gearing()
        
        # Total costs = 10,000, debt = 7,000, so gearing = 0.7
        expected_gearing = 7000 / 10000
        self.assertAlmostEqual(self.mock_model.gearing_eff, expected_gearing)
        
    def test_calculate_equity_requirement(self):
        """Test equity requirement calculation."""
        self.financing_plan._calculate_equity_requirement()
        
        # Equity = Total costs - Debt = 10,000 - 7,000 = 3,000
        expected_equity = 10000 - 7000
        self.assertEqual(self.financing_plan.total_equity_required, expected_equity)
        self.assertEqual(self.mock_model.subgearing, 0.2)  # 20% converted to decimal
        
    def test_calculate_equity_first_drawdowns_simple(self):
        """Test equity-first drawdowns with simple scenario."""
        # Setup
        self.financing_plan.total_equity_required = 3000
        self.financing_plan._initialize_sources()
        
        # Execute
        self.financing_plan._calculate_equity_first_drawdowns()
        
        # Verify equity is drawn first
        equity_sources = self.mock_model.financial_model['sources']['equity']
        debt_sources = self.mock_model.financial_model['sources']['senior_debt']
        
        # First 3 periods should have equity, last period should have debt
        np.testing.assert_array_equal(equity_sources, [1000, 2000, 0, 0])
        np.testing.assert_array_equal(debt_sources, [0, 0, 3000, 4000])
        
        # Totals should match requirements
        self.assertAlmostEqual(np.sum(equity_sources), 3000)
        self.assertAlmostEqual(np.sum(debt_sources), 7000)
        
    def test_calculate_equity_first_drawdowns_transition_period(self):
        """Test equity-first drawdowns with transition within a period."""
        # Setup where equity requirement falls within a period
        self.mock_model.financial_model['uses'] = {
            'total': pd.Series([1000, 1500, 2000]),  # 4.5M total
            'total_cumul': pd.Series([1000, 2500, 4500])
        }
        self.financing_plan.total_equity_required = 2200  # Falls within period 2
        self.mock_model.senior_debt_amount = 2300  # Update to match expected debt requirement
        self.financing_plan._initialize_sources()
        
        # Execute
        self.financing_plan._calculate_equity_first_drawdowns()
        
        equity_sources = self.mock_model.financial_model['sources']['equity']
        debt_sources = self.mock_model.financial_model['sources']['senior_debt']
        
        # Period 1: All equity (1000)
        # Period 2: Partial equity (1200) + partial debt (300)
        # Period 3: All debt (2000)
        np.testing.assert_array_equal(equity_sources, [1000, 1200, 0])
        np.testing.assert_array_equal(debt_sources, [0, 300, 2000])
        
        self.assertAlmostEqual(np.sum(equity_sources), 2200)
        self.assertAlmostEqual(np.sum(debt_sources), 2300)
        
    def test_calculate_pro_rata_drawdowns(self):
        """Test pro-rata drawdowns calculation."""
        # Setup
        self.mock_model.gearing_eff = 0.7  # 70% debt
        self.financing_plan._initialize_sources()
        
        # Execute
        self.financing_plan._calculate_pro_rata_drawdowns()
        
        equity_sources = self.mock_model.financial_model['sources']['equity']
        debt_sources = self.mock_model.financial_model['sources']['senior_debt']
        
        # Each period should maintain 70/30 debt/equity ratio
        expected_debt = np.array([700, 1400, 2100, 2800])  # 70% of each period
        expected_equity = np.array([300, 600, 900, 1200])   # 30% of each period
        
        np.testing.assert_array_almost_equal(debt_sources, expected_debt)
        np.testing.assert_array_almost_equal(equity_sources, expected_equity)
        
    def test_calculate_pro_rata_drawdowns_debt_cap(self):
        """Test pro-rata drawdowns with debt capacity constraint."""
        # Setup with debt cap lower than proportional amount
        self.mock_model.gearing_eff = 0.5  # 50% gearing
        self.mock_model.senior_debt_amount = 4000  # Lower debt capacity
        self.financing_plan._initialize_sources()
        
        # Execute
        self.financing_plan._calculate_pro_rata_drawdowns()
        
        debt_sources = self.mock_model.financial_model['sources']['senior_debt']
        
        # Should be capped at 4000 total
        self.assertAlmostEqual(np.sum(debt_sources), 4000)
        
    def test_allocate_equity_components(self):
        """Test allocation of equity between share capital and SHL."""
        # Setup
        self.mock_model.subgearing = 0.3  # 30% SHL
        self.mock_model.financial_model['sources'] = {
            'equity': pd.Series([1000, 2000, 0, 0])  # 3000 total
        }
        
        # Execute
        self.financing_plan._allocate_equity_components()
        
        share_capital = self.mock_model.financial_model['sources']['share_capital']
        shl = self.mock_model.financial_model['sources']['SHL']
        
        # Share capital = 70% of equity, SHL = 30% of equity
        expected_share_capital = pd.Series([700, 1400, 0, 0])
        expected_shl = pd.Series([300, 600, 0, 0])
        
        pd.testing.assert_series_equal(share_capital, expected_share_capital, check_dtype=False)
        pd.testing.assert_series_equal(shl, expected_shl, check_dtype=False)
        
    def test_calculate_injection_totals(self):
        """Test calculation of total sources."""
        # Setup
        self.mock_model.financial_model['sources'] = {
            'senior_debt': pd.Series([0, 0, 3000, 4000]),
            'equity': pd.Series([1000, 2000, 0, 0])
        }
        
        # Execute
        self.financing_plan._calculate_injection_totals()
        
        total_sources = self.mock_model.financial_model['sources']['total']
        expected_total = pd.Series([1000, 2000, 3000, 4000])
        
        pd.testing.assert_series_equal(total_sources, expected_total)
        
    @patch('financial_model.financial_model_sections.financing_plan.logger')
    def test_calculate_injection_totals_mismatch_warning(self, mock_logger):
        """Test warning when sources don't match uses."""
        # Setup with mismatched totals
        self.mock_model.financial_model['sources'] = {
            'senior_debt': pd.Series([0, 0, 3000, 3000]),  # Total = 6000 (too low)
            'equity': pd.Series([1000, 2000, 0, 0])        # Total = 3000
        }
        
        # Execute
        self.financing_plan._calculate_injection_totals()
        
        # Should log a warning
        mock_logger.warning.assert_called_once()
        warning_message = mock_logger.warning.call_args[0][0]
        self.assertIn("sources", warning_message)
        self.assertIn("don't match uses", warning_message)
        
    def test_get_financing_summary(self):
        """Test financing summary generation."""
        # Setup
        self.financing_plan.total_equity_required = 3000
        self.mock_model.gearing_eff = 0.7
        self.mock_model.subgearing = 0.2
        
        # Execute
        summary = self.financing_plan.get_financing_summary()
        
        # Verify summary contents
        expected_summary = {
            'total_project_cost': 10000,
            'senior_debt_amount': 7000,
            'total_equity_amount': 3000,
            'effective_gearing': 0.7,
            'subgearing_percentage': 0.2,
            'injection_method': 'EQUITY_FIRST'
        }
        
        self.assertEqual(summary, expected_summary)
        
    def test_calculate_financing_structure_equity_first(self):
        """Test complete financing structure calculation with equity-first method."""
        # Execute full calculation
        self.financing_plan._calculate_financing_structure()
        
        # Verify all components were calculated
        sources = self.mock_model.financial_model['sources']
        
        self.assertIn('equity', sources)
        self.assertIn('senior_debt', sources)
        self.assertIn('share_capital', sources)
        self.assertIn('SHL', sources)
        self.assertIn('total', sources)
        
        # Verify gearing and equity were calculated
        self.assertAlmostEqual(self.mock_model.gearing_eff, 0.7)
        self.assertEqual(self.financing_plan.total_equity_required, 3000)
        
    def test_calculate_financing_structure_pro_rata(self):
        """Test complete financing structure calculation with pro-rata method."""
        # Change to pro-rata method
        self.mock_model.project.injection_choice = 2  # PRO_RATA
        
        # Execute full calculation
        self.financing_plan._calculate_financing_structure()
        
        # Verify pro-rata sources were calculated
        debt_sources = self.mock_model.financial_model['sources']['senior_debt']
        equity_sources = self.mock_model.financial_model['sources']['equity']
        
        # Should maintain proportional relationship
        total_debt = np.sum(debt_sources)
        total_equity = np.sum(equity_sources)
        actual_gearing = total_debt / (total_debt + total_equity)
        
        self.assertAlmostEqual(actual_gearing, 0.7, places=2)
        
       
    def test_initialize_complete_flow(self):
        """Test the complete initialize method."""
        # Execute
        self.financing_plan.initialize()
        
        # Verify complete financing structure was created
        sources = self.mock_model.financial_model['sources']
        
        self.assertIn('equity', sources)
        self.assertIn('senior_debt', sources)
        self.assertIn('share_capital', sources)
        self.assertIn('SHL', sources)
        self.assertIn('total', sources)
        
        # Verify totals balance
        total_sources = np.sum(sources['total'])
        total_uses = np.sum(self.mock_model.financial_model['uses']['total'])
        self.assertAlmostEqual(total_sources, total_uses)


class TestFinancingPlanEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for FinancingPlan."""
    
    def setUp(self):
        """Set up test fixtures for edge cases."""
        self.mock_model = Mock()
        self.mock_model.project = Mock()
        self.financing_plan = FinancingPlan(self.mock_model)
        
    def test_zero_debt_scenario(self):
        """Test financing plan with zero debt (100% equity)."""
        # Setup
        self.mock_model.financial_model = {
            'uses': {
                'total': pd.Series([1000, 2000, 3000]),
                'total_cumul': pd.Series([1000, 3000, 6000])
            }
        }
        self.mock_model.senior_debt_amount = 0
        self.mock_model.project.injection_choice = 1
        self.mock_model.project.subgearing = 0.0
        
        # Execute
        self.financing_plan._calculate_financing_structure()
        
        # All funding should be equity
        debt_sources = self.mock_model.financial_model['sources']['senior_debt']
        equity_sources = self.mock_model.financial_model['sources']['equity']
        
        np.testing.assert_array_equal(debt_sources, [0, 0, 0])
        np.testing.assert_array_equal(equity_sources, [1000, 2000, 3000])
        
    def test_zero_equity_scenario(self):
        """Test financing plan with zero equity (100% debt)."""
        # Setup
        self.mock_model.financial_model = {
            'uses': {
                'total': pd.Series([1000, 2000, 3000]),
                'total_cumul': pd.Series([1000, 3000, 6000])
            }
        }
        self.mock_model.senior_debt_amount = 6000
        self.mock_model.project.injection_choice = 1
        self.mock_model.project.subgearing = 0.0
        self.mock_model.project.gearing = 100
        
        # Execute
        self.financing_plan._calculate_financing_structure()
        
        # All funding should be debt
        debt_sources = self.mock_model.financial_model['sources']['senior_debt']
        equity_sources = self.mock_model.financial_model['sources']['equity']
        
        np.testing.assert_array_equal(debt_sources, [1000, 2000, 3000])
        np.testing.assert_array_equal(equity_sources, [0, 0, 0])
        
    def test_single_period_construction(self):
        """Test financing plan with single construction period."""
        # Setup
        self.mock_model.financial_model = {
            'uses': {
                'total': pd.Series([10000]),
                'total_cumul': pd.Series([10000])
            }
        }
        self.mock_model.senior_debt_amount = 7000
        self.mock_model.project.injection_choice = 1
        self.mock_model.project.subgearing = 20.0
        
        # Execute
        self.financing_plan._calculate_financing_structure()
        
        # Verify single period allocation
        debt_sources = self.mock_model.financial_model['sources']['senior_debt']
        equity_sources = self.mock_model.financial_model['sources']['equity']
        
        self.assertEqual(len(debt_sources), 1)
        self.assertEqual(len(equity_sources), 1)
        self.assertEqual(debt_sources[0] + equity_sources[0], 10000)
        
    def test_high_subgearing_scenario(self):
        """Test financing plan with high subgearing (90% SHL)."""
        # Setup
        self.mock_model.financial_model = {
            'uses': {
                'total': pd.Series([1000, 2000]),
                'total_cumul': pd.Series([1000, 3000])
            }
        }
        self.mock_model.senior_debt_amount = 2000
        self.mock_model.project.injection_choice = 2  # Pro-rata
        self.mock_model.project.subgearing = 90.0  # 90% SHL
        
        # Execute
        self.financing_plan._calculate_financing_structure()
        
        # Verify SHL dominates equity structure
        share_capital = self.mock_model.financial_model['sources']['share_capital']
        shl = self.mock_model.financial_model['sources']['SHL']
        
        total_share_capital = np.sum(share_capital)
        total_shl = np.sum(shl)
        
        # SHL should be 9x share capital
        self.assertAlmostEqual(total_shl / total_share_capital, 9.0, places=1)
        


class TestFinancingPlanIntegration(unittest.TestCase):
    """Integration tests for realistic financing scenarios."""
    
    def test_realistic_solar_project_financing(self):
        """Test financing plan for a realistic solar project."""
        # Create realistic solar project model
        mock_model = Mock()
        
        # 50MW solar project with monthly construction over 12 months
        monthly_costs = [2000, 3000, 4000, 5000, 6000, 8000, 10000, 8000, 6000, 4000, 2000, 1000]
        cumulative_costs = np.cumsum(monthly_costs)  # Total: 59M
        
        mock_model.financial_model = {
            'uses': {
                'total': pd.Series(monthly_costs),
                'total_cumul': pd.Series(cumulative_costs)
            }
        }
        
        # 75% debt financing, 25% equity
        mock_model.senior_debt_amount = 44250  # 75% of 59M
        mock_model.project.injection_choice = 1  # Equity first
        mock_model.project.subgearing = 30.0  # 30% SHL
        
        # Execute
        financing_plan = FinancingPlan(mock_model)
        financing_plan.initialize()
        
        # Verify realistic financing structure
        sources = mock_model.financial_model['sources']
        
        # Total funding should equal total costs
        total_funding = np.sum(sources['total'])
        self.assertAlmostEqual(total_funding, 59000, places=0)
        
        # Verify equity/debt split
        total_debt = np.sum(sources['senior_debt'])
        total_equity = np.sum(sources['equity'])
        
        self.assertAlmostEqual(total_debt, 44250, places=0)
        self.assertAlmostEqual(total_equity, 14750, places=0)
        
        # Verify share capital/SHL split (70/30)
        total_share_capital = np.sum(sources['share_capital'])
        total_shl = np.sum(sources['SHL'])
        
        self.assertAlmostEqual(total_share_capital, 10325, places=0)  # 70% of equity
        self.assertAlmostEqual(total_shl, 4425, places=0)  # 30% of equity
        
        # Verify financing summary
        summary = financing_plan.get_financing_summary()
        self.assertEqual(summary['total_project_cost'], 59000)
        self.assertAlmostEqual(summary['effective_gearing'], 0.75, places=2)
        self.assertEqual(summary['injection_method'], 'EQUITY_FIRST')
        
    def test_wind_project_pro_rata_financing(self):
        """Test pro-rata financing for a wind project."""
        # Create wind project model
        mock_model = Mock()
        
        # 100MW wind project with quarterly construction over 8 quarters
        quarterly_costs = [8000, 12000, 15000, 18000, 20000, 15000, 10000, 5000]
        cumulative_costs = np.cumsum(quarterly_costs)  # Total: 103M
        
        mock_model.financial_model = {
            'uses': {
                'total': pd.Series(quarterly_costs),
                'total_cumul': pd.Series(cumulative_costs)
            }
        }
        
        # 80% debt financing, 20% equity
        mock_model.senior_debt_amount = 82400  # 80% of 103M
        mock_model.project.injection_choice = 2  # Pro-rata
        mock_model.project.subgearing = 25.0  # 25% SHL
        
        # Execute
        financing_plan = FinancingPlan(mock_model)
        financing_plan.initialize()
        
        # Verify pro-rata structure maintained throughout
        sources = mock_model.financial_model['sources']
        
        for i in range(len(quarterly_costs)):
            period_debt = sources['senior_debt'][i]
            period_equity = sources['equity'][i]
            period_total = period_debt + period_equity
            period_shl = sources['SHL'][i]
            period_share_capital = sources['share_capital'][i]
            
            # Each period should maintain 80/20 ratio
            period_gearing = period_debt / period_total if period_total > 0 else 0
            self.assertAlmostEqual(period_gearing, 0.8, places=2)
            
        # Verify final totals
        total_debt = np.sum(sources['senior_debt'])
        total_equity = np.sum(sources['equity'])
        total_shl = np.sum(sources['SHL'])
        total_share_capital = np.sum(sources['share_capital'])


        
        self.assertAlmostEqual(total_debt, 82400, places=0)
        self.assertAlmostEqual(total_equity, 20600, places=0)
        self.assertAlmostEqual(total_shl, 5150, places=0)
        self.assertAlmostEqual(total_share_capital, 15450, places=0)


if __name__ == '__main__':
    # Configure logging to reduce noise during testing
    logging.getLogger('financial_model.financial_model_sections.financing_plan').setLevel(logging.ERROR)
    
    unittest.main()
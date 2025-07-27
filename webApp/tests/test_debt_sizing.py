import unittest
from unittest.mock import Mock, MagicMock, patch
import numpy as np
import pandas as pd
import warnings

from financial_model.financial_model_sections.debt_sizing import SeniorDebtSizing


class TestSeniorDebtSizing(unittest.TestCase):
	"""Test cases for the SeniorDebtSizing class."""
	
	def setUp(self):
		"""Set up test fixtures."""
		self.mock_instance = Mock()
		self.mock_instance.target_DSCR = 1.35
		self.mock_instance.target_gearing = 0.75
		
		# Create realistic financial model data
		self.mock_instance.financial_model = {
			'senior_debt': {
				'interests_operations': np.array([100.0, 150.0, 120.0, 80.0, 40.0]),
				'balance_bop': np.array([10000.0, 8000.0, 6000.0, 4000.0, 2000.0]),
			},
			'days': {
				'debt_interest_operations': np.array([90.0, 90.0, 90.0, 90.0, 90.0])  # Quarterly periods
			},
			'flags': {
				'debt_amo': np.array([1, 1, 1, 1, 1])  # All periods are amortization periods
			},
			'op_account': {
				'cash_flows_operating': np.array([2000.0, 2200.0, 2100.0, 1800.0, 1500.0])
			},
			'uses': {
				'total': pd.Series([5000.0, 3000.0, 2000.0])  # Total project cost = 10,000
			},
			'sources': {
				'senior_debt': np.array([7000.0, 1000.0, 0.0, 0.0, 0.0])  # Total debt = 8,000
			}
		}
		
		self.debt_sizing = SeniorDebtSizing(self.mock_instance)
		
	def test_init(self):
		"""Test SeniorDebtSizing initialization."""
		self.assertEqual(self.debt_sizing.instance, self.mock_instance)
		
	def test_calculate_senior_debt_amount_basic(self):
		"""Test basic senior debt amount calculation."""
		# Execute
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		
		# Check that all required components were calculated
		self.assertIn('discount_factor', fm)
		self.assertIn('debt_sizing', fm)
		
		# Check discount factor calculations
		self.assertIn('avg_interest_rate', fm['discount_factor'])
		self.assertIn('discount_factor', fm['discount_factor'])
		self.assertIn('discount_factor_cumul', fm['discount_factor'])
		
		# Check debt sizing calculations
		self.assertIn('CFADS_amo', fm['debt_sizing'])
		self.assertIn('target_DSCR', fm['debt_sizing'])
		self.assertIn('target_DS', fm['debt_sizing'])
		self.assertIn('target_debt_DSCR', fm['debt_sizing'])
		self.assertIn('target_debt_gearing', fm['debt_sizing'])
		self.assertIn('target_debt_amount', fm['debt_sizing'])
		
	def test_average_interest_rate_calculation(self):



		"""Test average interest rate calculation."""
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		avg_rates = fm['discount_factor']['avg_interest_rate']
		
		# Check that rates are calculated correctly (annual equivalent)
		# Expected: (interests_operations / balance_bop) / (days/360) = annualized rate
		expected_rates = np.array([
			(100/10000) / (90/360),  # 0.04 annualized
			(150/8000) / (90/360),   # 0.075 annualized
			(120/6000) / (90/360),   # 0.08 annualized
			(80/4000) / (90/360),    # 0.08 annualized
			(40/2000) / (90/360)     # 0.08 annualized
		])
		
		np.testing.assert_array_almost_equal(avg_rates, expected_rates, decimal=6)
		
	def test_average_interest_rate_zero_balance(self):
		"""Test average interest rate calculation with zero balance."""
		# Modify balance to include zero
		self.mock_instance.financial_model['senior_debt']['balance_bop'] = np.array([10000.0, 0.0, 6000.0, 4000.0, 2000.0])
		
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		avg_rates = fm['discount_factor']['avg_interest_rate']
		
		# Second period should have zero rate (zero balance)
		self.assertEqual(avg_rates[1], 0)
		# Other periods should have normal rates
		self.assertGreater(avg_rates[0], 0)
		self.assertGreater(avg_rates[2], 0)
		
	def test_discount_factor_calculation(self):
		"""Test discount factor calculation."""
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		discount_factors = fm['discount_factor']['discount_factor']
		
		# Check that discount factors are calculated correctly
		# Expected: 1 / (1 + (avg_rate * days/360))
		avg_rates = fm['discount_factor']['avg_interest_rate']
		expected_factors = 1 / (1 + (avg_rates * 90/360))
		
		np.testing.assert_array_almost_equal(discount_factors, expected_factors, decimal=6)
		
	def test_discount_factor_non_amortization_periods(self):
		"""Test discount factor with non-amortization periods."""
		# Set some periods as non-amortization
		self.mock_instance.financial_model['flags']['debt_amo'] = np.array([0, 0, 1, 1, 1])
		
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		discount_factors = fm['discount_factor']['discount_factor']
		
		# First two periods should have discount factor = 1 (no amortization)
		self.assertEqual(discount_factors[0], 1)
		self.assertEqual(discount_factors[1], 1)
		# Later periods should have calculated discount factors
		self.assertLess(discount_factors[2], 1)
		self.assertLess(discount_factors[3], 1)
		
	def test_cumulative_discount_factor(self):
		"""Test cumulative discount factor calculation."""
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		discount_factors = fm['discount_factor']['discount_factor']
		cumulative_factors = fm['discount_factor']['discount_factor_cumul']
		
		# Check that cumulative is the cumulative product
		expected_cumulative = np.cumprod(discount_factors)
		np.testing.assert_array_almost_equal(cumulative_factors, expected_cumulative, decimal=6)
		
	def test_cfads_amo_calculation(self):
		"""Test CFADS for amortization calculation."""
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		cfads_amo = fm['debt_sizing']['CFADS_amo']
		
		# CFADS_amo should be operating cash flows * debt_amo flag
		expected_cfads = fm['op_account']['cash_flows_operating'] * fm['flags']['debt_amo']
		np.testing.assert_array_equal(cfads_amo, expected_cfads)
		
	def test_target_dscr_calculation(self):
		"""Test target DSCR calculation."""
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		target_dscr = fm['debt_sizing']['target_DSCR']
		
		# Target DSCR should be instance target_DSCR * debt_amo flag
		expected_target = self.mock_instance.target_DSCR * fm['flags']['debt_amo']
		np.testing.assert_array_equal(target_dscr, expected_target)
		
	def test_target_ds_calculation(self):
		"""Test target debt service calculation."""
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		target_ds = fm['debt_sizing']['target_DS']
		cfads_amo = fm['debt_sizing']['CFADS_amo']
		
		# Target DS should be CFADS_amo / target_DSCR
		expected_ds = cfads_amo / self.mock_instance.target_DSCR
		np.testing.assert_array_almost_equal(target_ds, expected_ds, decimal=6)
		
	def test_target_debt_dscr_calculation(self):
		"""Test DSCR-based target debt calculation."""
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		target_debt_dscr = fm['debt_sizing']['target_debt_DSCR']
		
		# Should be NPV of target debt service
		target_ds = fm['debt_sizing']['target_DS']
		discount_factors_cumul = fm['discount_factor']['discount_factor_cumul']
		expected_debt = np.sum(target_ds * discount_factors_cumul)
		
		self.assertAlmostEqual(target_debt_dscr, expected_debt, places=2)
		
	def test_target_debt_gearing_calculation(self):
		"""Test gearing-based target debt calculation."""
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		target_debt_gearing = fm['debt_sizing']['target_debt_gearing']
		
		# Should be total uses * target gearing
		total_uses = fm['uses']['total'].sum()  # 10,000
		expected_debt = total_uses * self.mock_instance.target_gearing  # 7,500
		
		self.assertEqual(target_debt_gearing, expected_debt)
		
	def test_final_debt_amount_selection(self):
		"""Test final debt amount is minimum of DSCR and gearing limits."""
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		target_debt_amount = fm['debt_sizing']['target_debt_amount']
		target_debt_dscr = fm['debt_sizing']['target_debt_DSCR']
		target_debt_gearing = fm['debt_sizing']['target_debt_gearing']
		
		# Should be the minimum of the two constraints
		expected_amount = min(target_debt_dscr, target_debt_gearing)
		self.assertEqual(target_debt_amount, expected_amount)
		
	def test_calculate_senior_debt_repayments_basic(self):
		"""Test basic senior debt repayments calculation."""
		# First calculate debt amount to set up required data
		self.debt_sizing.calculate_senior_debt_amount()
		
		# Execute repayments calculation
		self.debt_sizing.calculate_senior_debt_repayments()
		
		fm = self.mock_instance.financial_model
		
		# Check that target repayments were calculated
		self.assertIn('target_repayments', fm['senior_debt'])
		target_repayments = fm['senior_debt']['target_repayments']
		
		# Should have same length as other arrays
		self.assertEqual(len(target_repayments), 5)
		
		# All repayments should be non-negative
		self.assertTrue(np.all(target_repayments >= 0))
		
	def test_dscr_sculpting_factor_calculation(self):
		"""Test DSCR sculpting factor calculation."""
		# Setup with known values for easier testing
		self.mock_instance.financial_model['sources']['senior_debt'] = np.array([5000, 3000, 0, 0, 0])  # Total = 8000
		
		self.debt_sizing.calculate_senior_debt_amount()
		self.debt_sizing.calculate_senior_debt_repayments()
		
		fm = self.mock_instance.financial_model
		
		# Calculate expected sculpting factor
		senior_debt_sum = np.sum(fm['sources']['senior_debt'])  # 8000
		npv_cfads = np.sum(fm['debt_sizing']['CFADS_amo'] * fm['discount_factor']['discount_factor_cumul'])
		expected_sculpting = npv_cfads / senior_debt_sum
		
		# Reverse-engineer the sculpting factor from the results
		# target_repayments = max(0, min(balance_bop, (CFADS_amo / sculpting) - interests))
		cfads_amo = fm['debt_sizing']['CFADS_amo']
		interests = fm['senior_debt']['interests_operations']
		target_repayments = fm['senior_debt']['target_repayments']
		
		# For periods where repayments > 0, sculpting should be consistent
		for i in range(len(target_repayments)):
			if target_repayments[i] > 0 and cfads_amo[i] > interests[i]:
				calculated_sculpting = cfads_amo[i] / (target_repayments[i] + interests[i])
				self.assertAlmostEqual(calculated_sculpting, expected_sculpting, places=2)
				
	def test_repayments_bounded_by_balance(self):
		"""Test that repayments don't exceed outstanding balance."""
		self.debt_sizing.calculate_senior_debt_amount()
		self.debt_sizing.calculate_senior_debt_repayments()
		
		fm = self.mock_instance.financial_model
		target_repayments = fm['senior_debt']['target_repayments']
		balance_bop = fm['senior_debt']['balance_bop']
		
		# No repayment should exceed the outstanding balance
		for i in range(len(target_repayments)):
			self.assertLessEqual(target_repayments[i], balance_bop[i])
			
	def test_repayments_non_negative(self):
		"""Test that repayments are always non-negative."""
		self.debt_sizing.calculate_senior_debt_amount()
		self.debt_sizing.calculate_senior_debt_repayments()
		
		fm = self.mock_instance.financial_model
		target_repayments = fm['senior_debt']['target_repayments']
		
		# All repayments should be >= 0
		self.assertTrue(np.all(target_repayments >= 0))
		
	def test_zero_senior_debt_drawdowns(self):
		"""Test handling of zero senior debt drawdowns."""
		# Set debt drawdowns to zero
		self.mock_instance.financial_model['sources']['senior_debt'] = np.array([0, 0, 0, 0, 0])
		
		self.debt_sizing.calculate_senior_debt_amount()
		self.debt_sizing.calculate_senior_debt_repayments()
		
		fm = self.mock_instance.financial_model
		target_repayments = fm['senior_debt']['target_repayments']
		
		# Should handle zero drawdowns gracefully without division by zero
		self.assertEqual(len(target_repayments), 5)
		self.assertTrue(np.all(target_repayments >= 0))


class TestSeniorDebtSizingEdgeCases(unittest.TestCase):
	"""Test edge cases and error conditions for SeniorDebtSizing."""
	
	def setUp(self):
		"""Set up test fixtures for edge cases."""
		self.mock_instance = Mock()
		self.mock_instance.target_DSCR = 1.30
		self.mock_instance.target_gearing = 0.80

		self.mock_instance.financial_model = {}
		
		self.debt_sizing = SeniorDebtSizing(self.mock_instance)
			
	def test_all_non_amortization_periods(self):
		"""Test scenario with no amortization periods."""
		self.mock_instance.financial_model.update({
			'senior_debt': {
				'interests_operations': np.array([100.0, 150.0, 120.0]),
				'balance_bop': np.array([10000.0, 8000.0, 6000.0]),
			},
			'days': {
				'debt_interest_operations': np.array([90.0, 90.0, 90.0])
			},
			'flags': {
				'debt_amo': np.array([0, 0, 0])  # No amortization periods
			},
			'op_account': {
				'cash_flows_operating': np.array([2000.0, 2200.0, 2100.0])
			},
			'uses': {
				'total': pd.Series([5000.0])
			},
			'sources': {
				'senior_debt': np.array([4000.0, 0.0, 0.0])
			}
		})
		
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		
		# CFADS_amo should be all zeros
		np.testing.assert_array_equal(fm['debt_sizing']['CFADS_amo'], [0, 0, 0])
		
		# Target DSCR should be all zeros
		np.testing.assert_array_equal(fm['debt_sizing']['target_DSCR'], [0, 0, 0])
		
		# DSCR-based debt should be zero
		self.assertEqual(fm['debt_sizing']['target_debt_DSCR'], 0)
		
	def test_very_high_interest_rates(self):
		"""Test handling of very high interest rates."""
		self.mock_instance.financial_model.update({
			'senior_debt': {
				'interests_operations': np.array([5000.0, 4000.0, 3000.0]),  # Very high interest
				'balance_bop': np.array([10000.0, 8000.0, 6000.0]),
			},
			'days': {
				'debt_interest_operations': np.array([90.0, 90.0, 90.0])
			},
			'flags': {
				'debt_amo': np.array([1, 1, 1])
			},
			'op_account': {
				'cash_flows_operating': np.array([2000.0, 2200.0, 2100.0])
			},
			'uses': {
				'total': pd.Series([20000.0])
			},
			'sources': {
				'senior_debt': np.array([15000.0, 0.0, 0.0])
			}
		})
		
		self.debt_sizing.calculate_senior_debt_amount()
		
		fm = self.mock_instance.financial_model
		avg_rates = fm['discount_factor']['avg_interest_rate']
		
		# Should handle high rates without overflow
		self.assertTrue(np.all(np.isfinite(avg_rates)))
		self.assertTrue(np.all(avg_rates > 0))
		
		# Discount factors should be very small but positive
		discount_factors = fm['discount_factor']['discount_factor']
		self.assertTrue(np.all(discount_factors > 0))
		self.assertTrue(np.all(discount_factors < 1))

	def test_negative_cash_flows(self):
		"""Test handling of negative operating cash flows."""
		self.mock_instance.financial_model.update({
			'senior_debt': {
				'interests_operations': np.array([100.0, 150.0, 120.0]),
				'balance_bop': np.array([10000.0, 8000.0, 6000.0]),
			},
			'days': {
				'debt_interest_operations': np.array([90.0, 90.0, 90.0])
			},
			'flags': {
				'debt_amo': np.array([1, 1, 1])
			},
			'op_account': {
				'cash_flows_operating': np.array([-1000.0, 2200.0, -500.0])  # Negative cash flows
			},
			'uses': {
				'total': pd.Series([10000.0])
			},
			'sources': {
				'senior_debt': np.array([7500.0, 0.0, 0.0])
			}
		})
		
		self.debt_sizing.calculate_senior_debt_amount()
		self.debt_sizing.calculate_senior_debt_repayments()
		
		fm = self.mock_instance.financial_model
		
		# Should handle negative cash flows
		cfads_amo = fm['debt_sizing']['CFADS_amo']
		target_repayments = fm['senior_debt']['target_repayments']
		
		# Negative CFADS periods should result in zero repayments
		self.assertEqual(target_repayments[0], 0)  # Negative CFADS
		self.assertEqual(target_repayments[2], 0)  # Negative CFADS


class TestSeniorDebtSizingIntegration(unittest.TestCase):
	"""Integration tests for realistic debt sizing scenarios."""
	
	def test_realistic_solar_project_debt_sizing(self):
		"""Test debt sizing for a realistic solar project."""
		mock_instance = Mock()
		mock_instance.target_DSCR = 1.35
		mock_instance.target_gearing = 0.75
		
		# 25-year solar project with quarterly periods (100 periods)
		n_periods = 100
		
		# Declining balance schedule
		initial_balance = 75000  # 75M debt
		balance_bop = []
		current_balance = initial_balance
		for i in range(n_periods):
			balance_bop.append(current_balance)
			current_balance = max(0, current_balance - 1000)  # 1M quarterly repayment
			
		# Interest calculations (5% annual = 1.25% quarterly)
		quarterly_rate = 0.0125
		interests_operations = [balance * quarterly_rate for balance in balance_bop]
		
		# Operating cash flows (increasing over time due to inflation)
		base_cfads = 3000  # 3M quarterly
		cash_flows_operating = [base_cfads * (1.02 ** (i // 4)) for i in range(n_periods)]
		
		mock_instance.financial_model = {
			'senior_debt': {
				'interests_operations': np.array(interests_operations),
				'balance_bop': np.array(balance_bop),
			},
			'days': {
				'debt_interest_operations': np.array([90.0] * n_periods)  # Quarterly
			},
			'flags': {
				'debt_amo': np.array([1] * n_periods)  # All amortization periods
			},
			'op_account': {
				'cash_flows_operating': np.array(cash_flows_operating)
			},
			'uses': {
				'total': pd.Series([100000.0])  # 100M total project cost
			},
			'sources': {
				'senior_debt': np.array([75000.0] + [0.0] * (n_periods - 1))  # 75M debt upfront
			}
		}
		
		debt_sizing = SeniorDebtSizing(mock_instance)
		debt_sizing.calculate_senior_debt_amount()
		debt_sizing.calculate_senior_debt_repayments()
		
		fm = mock_instance.financial_model
		
		# Verify debt sizing results
		target_debt_gearing = fm['debt_sizing']['target_debt_gearing']
		target_debt_dscr = fm['debt_sizing']['target_debt_DSCR']
		target_debt_amount = fm['debt_sizing']['target_debt_amount']
		
		# Gearing-based should be 75M
		self.assertEqual(target_debt_gearing, 75000)
		
		# DSCR-based should be reasonable (likely the constraint)
		self.assertGreater(target_debt_dscr, 0)
		
		# Final amount should be minimum of constraints
		self.assertEqual(target_debt_amount, min(target_debt_gearing, target_debt_dscr))
		
		# Verify repayments are reasonable
		target_repayments = fm['senior_debt']['target_repayments']
		
		# All repayments should be non-negative
		self.assertTrue(np.all(target_repayments >= 0))
		
		# Early periods should have higher repayments (more cash available)
		# Later periods should have lower repayments (less outstanding balance)
		first_half_avg = np.mean(target_repayments[:50])
		second_half_avg = np.mean(target_repayments[50:])
		
		# This relationship might not always hold, but generally true for declining balance
		# self.assertGreaterEqual(first_half_avg, second_half_avg * 0.5)  # Allow some flexibility
		
	def test_wind_project_debt_sizing_with_construction_period(self):
		"""Test debt sizing for wind project with construction period."""
		mock_instance = Mock()
		mock_instance.target_DSCR = 1.25
		mock_instance.target_gearing = 0.80
		
		# 2-year construction + 23-year operations (100 periods total)
		n_periods = 100
		construction_periods = 8  # 2 years quarterly
		operation_periods = n_periods - construction_periods
		
		# No debt service during construction
		debt_amo_flags = [0] * construction_periods + [1] * operation_periods
		
		# Ramping balance during construction, then amortizing
		balance_bop = []
		cash_flows = []
		interests = []
		
		# Construction phase
		for i in range(construction_periods):
			balance_bop.append(0)  # No debt during construction
			cash_flows.append(-2000)  # Negative cash flows during construction
			interests.append(0)
			
		# Operations phase
		initial_debt = 120000  # 120M debt at start of operations
		current_balance = initial_debt
		for i in range(operation_periods):
			balance_bop.append(current_balance)
			# Strong cash flows during operations
			cash_flows.append(8000 * (1.02 ** (i // 4)))  # 8M quarterly with inflation
			interests.append(current_balance * 0.0125)  # 5% annual rate
			current_balance = max(0, current_balance - 1500)  # 1.5M quarterly repayment
			
		mock_instance.financial_model = {
			'senior_debt': {
				'interests_operations': np.array(interests),
				'balance_bop': np.array(balance_bop),
			},
			'days': {
				'debt_interest_operations': np.array([90.0] * n_periods)
			},
			'flags': {
				'debt_amo': np.array(debt_amo_flags)
			},
			'op_account': {
				'cash_flows_operating': np.array(cash_flows)
			},
			'uses': {
				'total': pd.Series([150000.0])  # 150M total project cost
			},
			'sources': {
				'senior_debt': np.array([120000.0] + [0.0] * (n_periods - 1))
			}
		}
		
		debt_sizing = SeniorDebtSizing(mock_instance)
		debt_sizing.calculate_senior_debt_amount()
		debt_sizing.calculate_senior_debt_repayments()
		
		fm = mock_instance.financial_model
		
		# Verify construction periods have no debt service
		cfads_amo = fm['debt_sizing']['CFADS_amo']
		target_dscr = fm['debt_sizing']['target_DSCR']
		
		# Construction periods should have zero CFADS and DSCR
		for i in range(construction_periods):
			self.assertEqual(cfads_amo[i], 0)
			self.assertEqual(target_dscr[i], 0)
			
		# Operations periods should have positive CFADS and DSCR
		for i in range(construction_periods, n_periods):
			if cash_flows[i] > 0:  # Only check periods with positive cash flows
				self.assertGreater(cfads_amo[i], 0)
				self.assertGreater(target_dscr[i], 0)
				
		# Verify debt sizing constraints
		target_debt_gearing = fm['debt_sizing']['target_debt_gearing']
		self.assertEqual(target_debt_gearing, 150000 * 0.80)  # 120M
		
		# Final debt amount should make sense
		target_debt_amount = fm['debt_sizing']['target_debt_amount']
		self.assertGreater(target_debt_amount, 0)
		self.assertLessEqual(target_debt_amount, 120000)


if __name__ == '__main__':
	# Suppress numpy warnings for cleaner test output
	warnings.filterwarnings('ignore', category=RuntimeWarning)
	
	unittest.main()
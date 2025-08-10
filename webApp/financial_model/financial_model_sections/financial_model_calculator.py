import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
import logging

import cProfile
import pstats
from functools import wraps

# Import all helper classes
from .income_statement_helper import IncomeStatementHelper
from .cash_flow_statement_helper import CashFlowStatementHelper
from .dsra_helper import DSRAHelper
from .accounts_helper import AccountsHelper


def profile_method(func):
	"""Decorator to profile individual methods."""
	@wraps(func)
	def wrapper(*args, **kwargs):
		profiler = cProfile.Profile()
		profiler.enable()
		result = func(*args, **kwargs)
		profiler.disable()
		
		# Uncomment to see profiling results
		# stats = pstats.Stats(profiler)
		# stats.sort_stats('cumulative')
		# print(f"\nProfile for {func.__name__}:")
		# stats.print_stats(10)
		
		return result
	return wrapper


class FinancialModelCalculator:
	"""
	Main calculator that orchestrates all financial calculations period by period
	to handle interdependencies correctly. Uses helper classes for all calculations.
	"""
	
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model
		self.n_periods = len(self.financial_model['flags']['operations'])
		
		# Set corporate tax rate (needed for income statement calculations)
		self.instance.corporate_income_tax_rate = float(self.instance.project.corporate_income_tax) / 100
		
		# Initialize all helper classes
		self.income_statement_helper = IncomeStatementHelper(instance)
		self.cash_flow_helper = CashFlowStatementHelper(instance)
		self.dsra_helper = DSRAHelper(instance)
		self.accounts_helper = AccountsHelper(instance)
	
	@profile_method
	def initialize(self):
		"""Initialize all calculations using period-by-period approach."""
		logger = logging.getLogger(__name__)
		logger.info("=== Starting FinancialModelCalculator.initialize() ===")
		
		# Initialize all arrays
		self._initialize_all_arrays()
		
		# Perform one-time DSRA calculations
		self._initialize_dsra_calculations()
		
		# Calculate period by period to handle interdependencies
		for period in range(self.n_periods):
			self._calculate_period(period)
		
		# Map calculated values for reporting
		self._map_income_statement_values()
		self._map_operating_account_values()
	
	def _initialize_all_arrays(self):
		"""Initialize all arrays with vectorized operations."""
		n = self.n_periods
		
		# Create dictionary of all arrays to initialize
		arrays_to_init = {
			'EBITDA': ['EBITDA', 'EBITDA_margin'],
			'IS': ['EBITDA', 'EBITDA_margin', 'EBIT', 'EBT', 'corporate_income_tax', 'net_income', 
				   'retained_earnings_bop', 'retained_earnings_eop', 'distributable_profit'],
			'op_account': ['EBITDA', 'working_cap_movement', 'corporate_tax', 
						  'cash_flows_operating', 'construction_costs', 'development_fee',
						  'senior_debt_interests_construction', 'senior_debt_upfront_fee', 
						  'senior_debt_commitment_fees', 'reserves', 'local_taxes',
						  'cash_flows_investing', 'cash_flows_financing', 'CFADS', 
						  'CFADS_amo', 'CFADS_operations', 'balance_bop', 'balance_eop',
						  'cash_flow_available_for_distribution', 'cash_available_for_distribution', 
						  'transfers_distribution_account', 'dsra_mov', 'senior_debt_interests_paid', 
						  'senior_debt_repayments'],
			'distr_account': ['balance_bop', 'balance_eop', 'transfers_distribution_account',
							 'cash_available_for_distribution', 'cash_available_for_dividends',
							 'cash_available_for_SHL_repayments', 'cash_available_for_redemption',
							 'dividends_paid', 'SHL_interests_paid', 'SHL_repayments',
							 'share_capital_repayments'],
			'SHL': ['balance_bop', 'balance_eop', 'interests_operations', 
					'interests_construction', 'interests_paid', 'repayments',
					'interests_capitalized'],
			'senior_debt': ['DS_effective'],
			'share_capital': ['balance_bop', 'balance_eop', 'repayments'],
			'DSRA': ['dsra_bop', 'dsra_eop', 'dsra_target', 'initial_funding',
					'dsra_additions', 'dsra_release', 'dsra_mov', 'cash_available_for_dsra']
		}
		
		# Initialize all arrays at once
		for category, fields in arrays_to_init.items():
			if category not in self.financial_model:
				self.financial_model[category] = {}
			for field in fields:
				self.financial_model[category][field] = np.zeros(n)
	
	def _initialize_dsra_calculations(self):
		"""Perform one-time DSRA calculations that don't depend on period-by-period values."""
		# Calculate effective debt service for all periods
		self.dsra_helper.compute_senior_debt_effective()
		
		# Calculate DSRA targets for all periods
		self.dsra_helper.compute_dsra_targets()
		
		# Calculate initial funding requirements
		self.dsra_helper.compute_initial_funding()
	
	def _calculate_period(self, period: int):
		"""
		Calculate all financial metrics for a single period in the correct order
		to handle interdependencies.
		"""
		# Step 1: Calculate EBITDA (depends on revenues and opex)
		self._calculate_period_ebitda(period)
		
		# Step 2: Calculate SHL interests (needed for income statement)
		self._calculate_period_shl_interests(period)
		
		# Step 3: Calculate Income Statement (needs EBITDA and SHL interests)
		self._calculate_period_income_statement(period)
		
		# Step 4: Calculate Cash Flow Statement (needs EBITDA and taxes)
		self._calculate_period_cash_flows(period)
		
		# Step 5: Calculate DSRA (needs CFADS)
		self._calculate_period_dsra(period)
		
		# Step 6: Calculate account balances and distributions
		self._calculate_period_accounts(period)
	
	def _calculate_period_ebitda(self, period: int):
		"""Calculate EBITDA for a single period using the helper."""
		ebitda_results = self.income_statement_helper.calculate_ebitda(period)
		
		# Store results
		self.financial_model['IS']['EBITDA'][period] = ebitda_results['ebitda']
		self.financial_model['IS']['EBITDA_margin'][period] = ebitda_results['ebitda_margin']
	
	def _calculate_period_shl_interests(self, period: int):
		"""Calculate SHL interests for a single period (needed before income statement)."""
		shl = self.financial_model['SHL']
		flags = self.financial_model['flags']
		days = self.financial_model['days']['model'][period]
		days_per_year = 360  # Banking convention
		
		# Get beginning balance (from previous period or initial)
		if period == 0:
			shl_balance_bop = 0
		else:
			shl_balance_bop = shl['balance_eop'][period - 1]
		
		# Calculate interest
		interest_amount = (
			shl_balance_bop * 
			self.instance.SHL_margin * 
			days / days_per_year
		)
		
		# Split between operations and construction
		shl['interests_operations'][period] = interest_amount * flags['operations'][period]
		shl['interests_construction'][period] = interest_amount * flags['construction'][period]
	
	def _calculate_period_income_statement(self, period: int):
		"""Calculate income statement items for a single period using the helper."""
		IS = self.financial_model['IS']
		
		# Use helper to calculate income statement items
		is_results = self.income_statement_helper.calculate_income_statement_items(
			period=period,
			ebitda=IS['EBITDA'][period],
			depreciation=IS['depreciation'][period],
			senior_debt_interest=self.financial_model['senior_debt']['interests_operations'][period],
			shl_interest=self.financial_model['SHL']['interests_operations'][period]
		)
		
		# Store results
		IS['EBIT'][period] = is_results['ebit']
		IS['EBT'][period] = is_results['ebt']
		IS['corporate_income_tax'][period] = is_results['corporate_income_tax']
		IS['net_income'][period] = is_results['net_income']
	
	def _calculate_period_cash_flows(self, period: int):
		"""Calculate cash flows for a single period using the helper."""
		op_account = self.financial_model['op_account']
		IS = self.financial_model['IS']
		
		# Store EBITDA in operating account
		op_account['EBITDA'][period] = IS['EBITDA'][period]
		op_account['working_cap_movement'][period] = self.financial_model['working_cap']['working_cap_movement'][period]
		op_account['corporate_tax'][period] = -IS['corporate_income_tax'][period]
		
		# Calculate operating cash flows
		cash_flows_operating = self.cash_flow_helper.calculate_operating_cash_flows(
			period=period,
			ebitda=op_account['EBITDA'][period],
			working_cap_movement=op_account['working_cap_movement'][period],
			corporate_tax=op_account['corporate_tax'][period]
		)
		op_account['cash_flows_operating'][period] = cash_flows_operating
		
		# Calculate investing cash flows
		investing_results = self.cash_flow_helper.calculate_investing_cash_flows(period)
		
		# Store investing components
		op_account['construction_costs'][period] = investing_results['construction_costs']
		op_account['development_fee'][period] = investing_results['development_fee']
		op_account['senior_debt_interests_construction'][period] = investing_results['senior_debt_interests_construction']
		op_account['senior_debt_upfront_fee'][period] = investing_results['senior_debt_upfront_fee']
		op_account['senior_debt_commitment_fees'][period] = investing_results['senior_debt_commitment_fees']
		op_account['reserves'][period] = investing_results['reserves']
		op_account['local_taxes'][period] = investing_results['local_taxes']
		op_account['cash_flows_investing'][period] = investing_results['cash_flows_investing']
		
		# Calculate financing cash flows
		cash_flows_financing = self.cash_flow_helper.calculate_financing_cash_flows(period)
		op_account['cash_flows_financing'][period] = cash_flows_financing
		
		# Calculate CFADS
		cfads_results = self.cash_flow_helper.calculate_cfads(
			period=period,
			cash_flows_operating=cash_flows_operating,
			cash_flows_investing=investing_results['cash_flows_investing'],
			cash_flows_financing=cash_flows_financing
		)
		
		# Store CFADS results
		op_account['CFADS'][period] = cfads_results['cfads']
		op_account['CFADS_amo'][period] = cfads_results['cfads_amo']
		op_account['CFADS_operations'][period] = cfads_results['cfads_operations']
	
	def _calculate_period_dsra(self, period: int):
		"""Calculate DSRA movements for a single period using the helper."""
		dsra = self.financial_model['DSRA']
		
		# Calculate cash available for DSRA (can be negative for shortfalls)
		cash_available = self.dsra_helper.calculate_cash_available_for_dsra(period)
		dsra['cash_available_for_dsra'][period] = cash_available
		
		# Set beginning balance
		if period == 0:
			dsra['dsra_bop'][period] = 0
		else:
			dsra['dsra_bop'][period] = dsra['dsra_eop'][period - 1]
		
		# Use helper to calculate movements
		movements = self.dsra_helper.calculate_dsra_movements(
			period=period,
			dsra_bop=dsra['dsra_bop'][period],
			initial_funding=dsra['initial_funding'][period],
			target=dsra['dsra_target'][period],
			cash_available=cash_available
		)
		
		# Store results
		dsra['dsra_additions'][period] = movements['additions']
		dsra['dsra_release'][period] = movements['release']
		dsra['dsra_eop'][period] = movements['eop']
		dsra['dsra_mov'][period] = movements['mov']
	
	def _calculate_period_accounts(self, period: int):
		"""Calculate account balances and distributions for a single period using the helper."""
		# All account calculations delegated to the helper
		self.accounts_helper._set_beginning_balances(period)
		self.accounts_helper._calculate_period_cash_available(period)
		self.accounts_helper._process_period_transfers(period)
		self.accounts_helper._process_period_distributions(period)
		self.accounts_helper._process_period_share_capital(period)
		self.accounts_helper._update_period_ending_balances(period)
	
	def _map_income_statement_values(self):
		"""Map calculated values to Income Statement for reporting."""
		IS = self.financial_model['IS']
		IS['contracted_revenues'] = self.financial_model['revenues']['contract']
		IS['merchant_revenues'] = self.financial_model['revenues']['merchant']
		IS['total_revenues'] = self.financial_model['revenues']['total']
		IS['senior_debt_interests'] = -1 * self.financial_model['senior_debt']['interests_operations']
		IS['shareholder_loan_interests'] = -1 * self.financial_model['SHL']['interests_operations']
		IS['operating_costs'] = -1 * self.financial_model['opex']['operating_costs']
		IS['lease_costs'] = -1 * self.financial_model['opex']['lease_costs']
		IS['total_opex'] = -1 * self.financial_model['opex']['total']
	
	def _map_operating_account_values(self):
		"""Map calculated values to Operating Account for reporting."""
		op_account = self.financial_model['op_account']
		op_account['share_capital'] = self.financial_model['sources']['share_capital']
		op_account['shareholder_loan'] = self.financial_model['sources']['SHL']
		op_account['senior_debt'] = self.financial_model['sources']['senior_debt']
		op_account['dsra_additions'] = self.financial_model['DSRA']['dsra_additions']
		op_account['dsra_release'] = self.financial_model['DSRA']['dsra_release']
		op_account['dsra_initial_funding'] = -1 * self.financial_model['DSRA']['initial_funding']
		op_account['cash_available_for_dsra'] = self.financial_model['DSRA']['cash_available_for_dsra']
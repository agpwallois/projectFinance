import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
import logging


from numba import jit
import cProfile
import pstats
from functools import wraps

# Import the required classes
from .income_statement import IncomeStatement
from .cash_flow_statement import CashFlowStatement
from .dsra import FinancialModelDSRA
from .accounts import Accounts



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
	to handle interdependencies correctly.
	"""
	
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model
		self.n_periods = len(self.financial_model['flags']['operations'])
		# Set corporate tax rate (needed for income statement calculations)
		self.instance.corporate_income_tax_rate = float(self.instance.project.corporate_income_tax) / 100		
		# Initialize calculation classes
		self.income_statement = IncomeStatement(instance)
		self.cash_flow_statement = CashFlowStatement(instance)
		self.dsra_calc = FinancialModelDSRA(instance)
		self.accounts = Accounts(instance)
	
	@profile_method
	def initialize(self):
		"""Initialize all calculations using period-by-period approach."""
		self._initialize_all_arrays()
		
		# Calculate period by period to handle interdependencies
		for period in range(self.n_periods):
			self._calculate_period(period)


		IS['contracted_revenues'] = self.financial_model['revenues']['contract']
		IS['merchant_revenues'] = self.financial_model['revenues']['merchant']
		IS['total'] = self.financial_model['revenues']['total']
		IS['senior_debt_interests'] = self.financial_model['senior_debt']['interests_operations']
		IS['shareholder_loan_interests'] = self.financial_model['SHL']['SHL_interests_paid']


	def _initialize_all_arrays(self):
		"""Initialize all arrays with vectorized operations."""
		n = self.n_periods
		
		# Create dictionary of all arrays to initialize
		arrays_to_init = {
			'EBITDA': ['EBITDA', 'EBITDA_margin'],
			'IS': ['EBIT', 'EBT', 'corporate_income_tax', 'net_income', 
				   'retained_earnings_bop', 'retained_earnings_eop', 'distributable_profit'],
			'op_account': ['EBITDA', 'working_cap_movement', 'corporate_tax', 
						  'cash_flows_operating', 'construction_costs', 'development_fee',
						  'cash_flows_investing', 'cash_flows_financing', 'CFADS', 
						  'CFADS_amo', 'CFADS_operations', 'balance_bop', 'balance_eop',
						  'cash_available_for_distribution', 'transfers_distribution_account',
						  'dsra_mov', 'senior_debt_interests_paid', 'senior_debt_repayments'],
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



	def _calculate_period(self, period: int):
		"""
		Calculate all financial metrics for a single period in the correct order
		to handle interdependencies.
		"""
		# Step 1: Calculate EBITDA (depends on revenues and opex)
		self._calculate_period_ebitda(period)
		
		# Step 2: Calculate SHL interests (needed for income statement)
		self._calculate_period_shl_interests(period)
		
		# Step 3: Calculate Income Statement (needs SHL interests)
		self._calculate_period_income_statement(period)
		
		# Step 4: Calculate Cash Flow Statement (needs EBITDA and taxes)
		self._calculate_period_cash_flows(period)
		
		# Step 5: Calculate DSRA (needs CFADS)
		self._calculate_period_dsra(period)
		
		# Step 6: Calculate account balances and distributions
		self._calculate_period_accounts(period)
		
	def _calculate_period_ebitda(self, period: int):
		"""Calculate EBITDA for a single period."""
		revenues = self.financial_model['revenues']['total'][period]
		opex = self.financial_model['opex']['total'][period]
		
		ebitda_value = revenues - opex
		ebitda_margin = ebitda_value / revenues if revenues > 0 else 0
		
		self.financial_model['EBITDA']['EBITDA'][period] = ebitda_value
		self.financial_model['EBITDA']['EBITDA_margin'][period] = ebitda_margin
		
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
		"""Calculate income statement items for a single period."""
		IS = self.financial_model['IS']



		# EBIT = EBITDA - Depreciation
		IS['EBIT'][period] = (
			self.financial_model['EBITDA']['EBITDA'][period] -
			self.financial_model['IS']['depreciation'][period]
		)


		
		# EBT = EBIT - Interest Expenses
		IS['EBT'][period] = (
			IS['EBIT'][period] -
			self.financial_model['senior_debt']['interests_operations'][period] -
			self.financial_model['SHL']['interests_operations'][period]
		)
		
		# Corporate Income Tax
		IS['corporate_income_tax'][period] = max(
			0,
			self.instance.corporate_income_tax_rate * IS['EBT'][period]
		)
		
		# Net Income
		IS['net_income'][period] = IS['EBT'][period] - IS['corporate_income_tax'][period]
		
	def _calculate_period_cash_flows(self, period: int):
		"""Calculate cash flows for a single period."""
		op_account = self.financial_model['op_account']
		flags = self.financial_model['flags']
		
		# Operating Cash Flows
		op_account['EBITDA'][period] = self.financial_model['EBITDA']['EBITDA'][period]
		op_account['working_cap_movement'][period] = self.financial_model['working_cap']['working_cap_movement'][period]
		op_account['corporate_tax'][period] = self.financial_model['IS']['corporate_income_tax'][period]
		
		op_account['cash_flows_operating'][period] = (
			op_account['EBITDA'][period] + 
			op_account['working_cap_movement'][period] -
			op_account['corporate_tax'][period]
		)
		
		# Investing Cash Flows
		op_account['construction_costs'][period] = self.financial_model['uses']['construction'][period]
		
		op_account['cash_flows_investing'][period] = -(
			op_account['construction_costs'][period]
		)
		
		# Financing Cash Flows
		financing_outflows = (
			self.financial_model['senior_debt']['upfront_fee'][period] +
			self.financial_model['senior_debt']['interests_construction'][period] +
			self.financial_model['senior_debt']['commitment_fees'][period]
		)
		
		financing_inflows = (
			self.financial_model['sources']['senior_debt'][period] +
			self.financial_model['sources']['equity'][period]
		)
		
		op_account['cash_flows_financing'][period] = financing_inflows - financing_outflows
		
		# CFADS
		op_account['CFADS'][period] = (
			op_account['cash_flows_operating'][period] +
			op_account['cash_flows_investing'][period] +
			op_account['cash_flows_financing'][period]
		)
		
		op_account['CFADS_amo'][period] = op_account['CFADS'][period] * flags['debt_amo'][period]
		op_account['CFADS_operations'][period] = op_account['CFADS'][period] * flags['operations'][period]
		
	def _calculate_period_dsra(self, period: int):
		"""Calculate DSRA for a single period."""
		# Initialize DSRA arrays and one-time calculations if first period
		if period == 0:
			# Calculate targets and initial funding (these are calculated once for all periods)
			self.dsra_calc._compute_senior_debt_effective()
			self.dsra_calc._compute_dsra_target()
			self.dsra_calc._compute_initial_funding()
		
		# Calculate DSRA cash flow for this period (depends on current period CFADS)
		dsra = self.financial_model['DSRA']
		dsra['cash_available_for_dsra'][period] = max(
			self.financial_model['op_account']['CFADS_amo'][period] - 
			self.financial_model['senior_debt']['DS_effective'][period], 
			0
		)
		
		# Calculate DSRA movements for this specific period
		self._calculate_period_dsra_movements(period)

	def _calculate_period_dsra_movements(self, period: int):
		"""Calculate DSRA movements for a single period."""
		dsra = self.financial_model['DSRA']
		
		# Set beginning balance
		if period == 0:
			dsra['dsra_bop'][period] = 0
		else:
			dsra['dsra_bop'][period] = dsra['dsra_eop'][period - 1]
		
		# Current balance after initial funding
		current_balance = dsra['dsra_bop'][period] + dsra['initial_funding'][period]
		effective_target = dsra['dsra_target'][period] + dsra['initial_funding'][period]
		target_gap = effective_target - current_balance
		
		# Calculate additions or releases
		dsra['dsra_additions'][period] = 0
		dsra['dsra_release'][period] = 0
		
		if target_gap > 0:
			dsra['dsra_additions'][period] = min(
				target_gap, dsra['cash_available_for_dsra'][period]
			)
		elif target_gap < 0:
			dsra['dsra_release'][period] = abs(target_gap)
		
		# Calculate ending balance
		dsra['dsra_eop'][period] = (
			current_balance +
			dsra['dsra_additions'][period] -
			dsra['dsra_release'][period]
		)
		
		# Apply target ceiling
		if dsra['dsra_eop'][period] > effective_target:
			excess = dsra['dsra_eop'][period] - effective_target
			dsra['dsra_release'][period] += excess
			dsra['dsra_eop'][period] = effective_target
		
		# Calculate net movement
		dsra['dsra_mov'][period] = dsra['dsra_eop'][period] - dsra['dsra_bop'][period]

	def _calculate_period_accounts(self, period: int):
		"""Calculate account balances and distributions for a single period."""
		# Set beginning balances
		self.accounts._set_beginning_balances(period)
		
		# Calculate cash available for distribution
		self.accounts._calculate_period_cash_available(period)
		
		# Process transfers to distribution account
		self.accounts._process_period_transfers(period)
		
		# Process distributions (dividends, SHL payments, etc.)
		self.accounts._process_period_distributions(period)
		
		# Process share capital redemption
		self.accounts._process_period_share_capital(period)
		
		# Update ending balances
		self.accounts._update_period_ending_balances(period)











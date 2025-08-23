from dataclasses import dataclass
from numpy.typing import NDArray
import numpy as np


@dataclass
class AccountBalances:
	"""Represents various account balances and their calculations."""
	balance_eop: NDArray
	balance_bop: NDArray

class AccountsHelper:
	"""
	Manages financial model accounts including distributions, SHL calculations,
	and share capital management.
	"""
	
	def __init__(self, instance):
		self.model = instance.financial_model
		self.instance = instance
		self.days_per_year = 360  # Banking convention
		
	def initialize(self) -> None:
		"""Initialize all account calculations and balances."""
		# Note: The actual period-by-period calculations are handled by 
		# FinancialModelCalculator which calls the individual period methods
		pass
			
	def _set_beginning_balances(self, i: int) -> None:
		"""Set beginning balances for all accounts."""
		if i == 0:
			# First period - all balances start at zero unless there's initial funding
			self.model['op_account']['balance_bop'][i] = 0
			self.model['distr_account']['balance_bop'][i] = 0
			self.model['SHL']['balance_bop'][i] = 0
			self.model['share_capital']['balance_bop'][i] = 0
			self.model['IS']['retained_earnings_bop'][i] = 0
		else:
			# Subsequent periods - BoP equals previous EoP
			self.model['op_account']['balance_bop'][i] = self.model['op_account']['balance_eop'][i-1]
			self.model['distr_account']['balance_bop'][i] = self.model['distr_account']['balance_eop'][i-1]
			self.model['SHL']['balance_bop'][i] = self.model['SHL']['balance_eop'][i-1]
			self.model['share_capital']['balance_bop'][i] = self.model['share_capital']['balance_eop'][i-1]
			self.model['IS']['retained_earnings_bop'][i] = self.model['IS']['retained_earnings_eop'][i-1]
			
	def _calculate_period_SHL_interests(self, i: int) -> None:
		"""Calculate SHL interests for the period."""
		shl = self.model['SHL']
		days = self.model['days']['model'][i]
		flags = self.model['flags']
		
		# Interest calculation based on beginning balance
		interest_amount = (
			shl['balance_bop'][i] * 
			self.instance.SHL_margin * 
			days / self.days_per_year
		)
		
		# Split between operations and construction
		shl['interests_operations'][i] = interest_amount * flags['operations'][i]
		shl['interests_construction'][i] = interest_amount * flags['construction'][i]
		
	def _calculate_period_cash_available(self, i: int) -> None:
		"""Calculate cash available for distribution in this period."""
		distr = self.model['distr_account']
		op_account = self.model['op_account']
		
		# Cash available = CFADS - Senior Debt Service - DSRA movements - Min Cash
		op_account['dsra_mov'][i] = self.model['DSRA']['dsra_mov'][i]
		op_account['senior_debt_interests_paid'][i]  = -1*self.model['senior_debt']['interests_operations'][i]
		op_account['senior_debt_repayments'][i] = -1*self.model['senior_debt']['repayments'][i]

		cash_available = (
			self.model['op_account']['CFADS'][i]
			+ op_account['senior_debt_interests_paid'][i]
			+ op_account['senior_debt_repayments'][i]
			- self.model['DSRA']['dsra_mov'][i]
		)

		op_account['cash_flow_available_for_distribution'][i] = cash_available
		
	def _process_period_transfers(self, i: int) -> None:
		"""Process transfers from operating account to distribution account."""
		distr = self.model['distr_account']
		op_account = self.model['op_account']
		
		# Calculate how much can be transferred
		# This is the positive cash available plus any existing operating account balance
		available_in_op_account = (
			op_account['balance_bop'][i] + 
			max(op_account['cash_flow_available_for_distribution'][i], 0)
		)
		
		op_account['cash_available_for_distribution'][i] = available_in_op_account


		# Transfer to distribution account (keeping minimum cash in operating account)
		min_cash_requirement = self.instance.project.cash_min * self.model['flags']['operations'][i]
		
		transfer_amount = max(
			available_in_op_account - min_cash_requirement,
			0
		)

		op_account['transfers_distribution_account'][i] = -1*transfer_amount
		distr['transfers_distribution_account'][i] = transfer_amount
		
	def _process_period_distributions(self, i: int) -> None:
		"""Process distributions: SHL interest, dividends, SHL repayments."""
		distr = self.model['distr_account']
		shl = self.model['SHL']
		IS = self.model['IS']
		
		# Available cash in distribution account
		available_cash = distr['balance_bop'][i] + distr['transfers_distribution_account'][i]
		distr['cash_available_for_distribution'][i] = available_cash
		
		# Step 1: Pay SHL interest first (senior to dividends)
		shl_interest_due = shl['interests_operations'][i]
		shl['interests_paid'][i] = min(available_cash, shl_interest_due)
		
		# Capitalize unpaid interest into SHL balance
		unpaid_interest = shl_interest_due - shl['interests_paid'][i]
		shl['interests_capitalized'] = getattr(shl, 'interests_capitalized', np.zeros(len(shl['balance_bop'])))
		shl['interests_capitalized'][i] = unpaid_interest
		
		available_cash -= shl['interests_paid'][i]
		
		# Step 2: Calculate distributable profit for dividends
		IS['distributable_profit'][i] = max(
			IS['retained_earnings_bop'][i] + IS['net_income'][i],
			0
		)
		
		# Step 3: Pay dividends (limited by both cash and distributable profit)
		distr['cash_available_for_dividends'][i] = available_cash
		distr['dividends_paid'][i] = -min(
			available_cash,
			IS['distributable_profit'][i]
		)
		available_cash += distr['dividends_paid'][i]
		
		# Step 4: SHL repayments with remaining cash
		distr['cash_available_for_SHL_repayments'][i] = available_cash
		shl['repayments'][i] = min(
			available_cash,
			shl['balance_bop'][i]  # Can't repay more than outstanding
		)
		available_cash -= shl['repayments'][i]
		
		# Step 5: Any remaining cash stays in distribution account
		distr['cash_available_for_redemption'][i] = available_cash
			
	def _process_period_share_capital(self, i: int) -> None:
		"""Process share capital redemption at liquidation."""
		share_capital = self.model['share_capital']
		distr = self.model['distr_account']
		
		# Only process if this is a liquidation period
		if self.model['flags']['liquidation_end'][i] > 0:
			# Calculate available cash in distribution account after all other payments
			available_for_redemption = distr['cash_available_for_redemption'][i]
			
			# Redeem share capital up to available cash and outstanding balance
			share_capital['repayments'][i] = min(
				available_for_redemption,
				share_capital['balance_bop'][i]
			)
		else:
			share_capital['repayments'][i] = 0
			
	def _update_period_ending_balances(self, i: int) -> None:
		"""Update all ending balances for the period."""
		# Operating Account
		op_account = self.model['op_account']
		distr = self.model['distr_account']
		
		op_account['balance_eop'][i] = (
			op_account['balance_bop'][i]
			+ op_account['cash_flow_available_for_distribution'][i]
			+ op_account['transfers_distribution_account'][i]
		)

		distr['SHL_interests_paid'][i] = -1*self.model['SHL']['interests_paid'][i]
		distr['SHL_repayments'][i] = -1*self.model['SHL']['repayments'][i]
		distr['share_capital_repayments'][i] = -1*self.model['share_capital']['repayments'][i]
		
		# Distribution Account
		distr['balance_eop'][i] = (
			distr['balance_bop'][i]
			+ distr['transfers_distribution_account'][i]
			+ distr['SHL_interests_paid'][i]
			+ distr['dividends_paid'][i]
			+ distr['SHL_repayments'][i]
			+ distr['share_capital_repayments'][i]
		)

		# SHL Balance
		shl = self.model['SHL']
		shl['balance_eop'][i] = (
			shl['balance_bop'][i]
			+ self.model['sources']['SHL'][i]
			+ shl['interests_construction'][i]  # Capitalized during construction
			+ shl['interests_capitalized'][i]  # Capitalized during operations
			- shl['repayments'][i]
		)
		
		# Share Capital Balance
		share_capital = self.model['share_capital']
		share_capital['balance_eop'][i] = (
			share_capital['balance_bop'][i]
			+ self.model['sources']['share_capital'][i]
			- share_capital['repayments'][i]
		)
		
		# Retained Earnings
		IS = self.model['IS']
		IS['retained_earnings_eop'][i] = (
			IS['retained_earnings_bop'][i]
			+ IS['net_income'][i]
			+ distr['dividends_paid'][i]
		)
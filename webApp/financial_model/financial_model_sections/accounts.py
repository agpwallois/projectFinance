from dataclasses import dataclass
from typing import Dict, Any
import numpy as np
import pandas as pd
from numpy.typing import NDArray

@dataclass
class AccountBalances:
	"""Represents various account balances and their calculations."""
	balance_eop: NDArray
	balance_bop: NDArray

class FinancialModelAccounts:
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
		self._calculate_distributions()
		self._initialize_operating_account()
		
		# Perform iterative calculations
		for i in range(self.instance.iteration):
			self._calculate_SHL_interests(i)
			self._distribute_cash()
			
	def _calculate_distributions(self) -> None:
		"""Calculate initial cash distributions and transfers."""
		distr = self.model['distr_account']
		
		# Calculate cash available for distribution
		distr['cash_available_for_distribution'] = self._calculate_available_cash()
		
		# Calculate transfers to distribution account
		distr['transfers_distribution_account'] = distr['cash_available_for_distribution'].clip(lower=0)
		
	def _calculate_available_cash(self) -> NDArray:
		"""Calculate total available cash considering various factors."""
		return (
			self.model['CFS']['CFADS']
			- self.model['senior_debt']['DS_effective']
			- self.model['DSRA']['dsra_mov']
			- self.instance.project.cash_min * np.array(self.model['flags']['operations'])
		)
		
	def _initialize_operating_account(self) -> None:
		"""Initialize the operating account balance."""
		op_account = self.model['op_account']
		distr = self.model['distr_account']
		
		# Calculate initial balance
		op_account['balance_eop'] = (
			distr['cash_available_for_distribution'] -
			distr['transfers_distribution_account']
		)
		
		# Roll the balance for initial funding
		op_account['balance_eop'] = np.roll(op_account['balance_eop'], 1)
		
	def _calculate_SHL_interests(self, iteration: int) -> None:
		"""
		Calculate SHL (Shareholder Loan) interests for operations and construction.
		
		Args:
			iteration: Current iteration number
		"""
		shl = self.model['SHL']
		days = self.model['days']['model']
		flags = self.model['flags']
		
		base_calculation = np.array(shl['balance_bop']) * self.instance.SHL_margin * days / self.days_per_year
		
		shl['interests_operations'] = base_calculation * flags['operations']
		shl['interests_construction'] = base_calculation * flags['construction']
		
	def _distribute_cash(self) -> None:
		"""Handle cash distribution logic including SHL, dividends, and share capital."""
		self._process_SHL_payments()
		self._process_dividend_payments()
		self._update_account_balances()
		self._process_share_capital()
		
	def _process_SHL_payments(self) -> None:
		"""Process SHL interest payments and repayments."""
		distr = self.model['distr_account']
		shl = self.model['SHL']
		
		# Calculate and process SHL interest payments
		shl['interests_paid'] = np.minimum(
			distr['transfers_distribution_account'],
			shl['interests_operations']
		)
		
		# Calculate cash available for dividends
		distr['cash_available_for_dividends'] = (
			distr['transfers_distribution_account'] - 
			shl['interests_paid']
		)
		
	def _process_dividend_payments(self) -> None:
		"""Process dividend payments and calculate related metrics."""
		distr = self.model['distr_account']
		
		# Calculate and process dividend payments
		distr['dividends_paid'] = np.minimum(
			distr['cash_available_for_dividends'],
			self.model['IS']['distributable_profit']
		)
		
		# Calculate cash available for SHL repayments
		distr['cash_available_for_SHL_repayments'] = (
			distr['cash_available_for_dividends'] - 
			distr['dividends_paid']
		)
		
		# Process SHL repayments
		self.model['SHL']['repayments'] = np.minimum(
			self.model['SHL']['balance_bop'],
			distr['cash_available_for_SHL_repayments']
		)
		
		# Calculate remaining cash for redemption
		distr['cash_available_for_redemption'] = (
			distr['cash_available_for_SHL_repayments'] - 
			self.model['SHL']['repayments']
		)
		
	def _update_account_balances(self) -> None:
		"""Update all account balances including distribution account and retained earnings."""
		self._update_distribution_account()
		self._update_SHL_balances()
		self._update_retained_earnings()
		
	def _update_distribution_account(self) -> None:
		"""Update distribution account balances."""
		distr = self.model['distr_account']
		shl = self.model['SHL']
		
		period_movement = (
			distr['transfers_distribution_account']
			- shl['interests_paid']
			- distr['dividends_paid']
			- shl['repayments']
		)
		
		distr['balance_eop'] = period_movement.cumsum()
		distr['balance_bop'] = distr['balance_eop'] - period_movement
		
	def _update_SHL_balances(self) -> None:
		"""Update SHL (Shareholder Loan) balances."""
		shl = self.model['SHL']
		
		period_movement = (
			self.model['injections']['SHL']
			+ shl['interests_construction']
			- shl['repayments']
		)
		
		shl['balance_eop'] = period_movement.cumsum()
		shl['balance_bop'] = shl['balance_eop'] - period_movement
		
	def _update_retained_earnings(self) -> None:
		"""Update retained earnings and distributable profit."""
		IS = self.model['IS']
		
		period_movement = (
			IS['net_income']
			- self.model['distr_account']['dividends_paid']
		)
		
		IS['retained_earnings_eop'] = period_movement.cumsum()
		IS['retained_earnings_bop'] = IS['retained_earnings_eop'] - period_movement
		IS['distributable_profit'] = np.clip(
			IS['retained_earnings_bop'] + IS['net_income'],
			0,
			None
		)
		
	def _process_share_capital(self) -> None:
		"""Process share capital repayments and update balances."""
		share_capital = self.model['share_capital']
		distr = self.model['distr_account']
		
		# Calculate repayments
		share_capital['repayments'] = (
			distr['balance_bop'] *
			self.model['flags']['liquidation_end']
		)
		
		# Update distribution account balance
		distr['balance_eop'] -= share_capital['repayments']
		
		# Update share capital balances
		period_movement = (
			self.model['injections']['share_capital']
			- share_capital['repayments']
		)
		
		share_capital['balance_eop'] = period_movement.cumsum()
		share_capital['balance_bop'] = (
			share_capital['balance_eop'] - period_movement
		)
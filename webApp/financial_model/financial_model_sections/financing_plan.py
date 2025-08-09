import pandas as pd
import numpy as np
import logging
from enum import Enum
from typing import Dict, Any
logger = logging.getLogger(__name__)


class InjectionMethod(Enum):
	"""Defines how project funding is structured during construction."""
	EQUITY_FIRST = 1  # Equity injected first, then debt
	PRO_RATA = 2      # Debt and equity injected proportionally

class FinancingPlan:
	"""
	Handles the calculation and structuring of project financing, including:
	- Senior debt and equity allocation
	- Share capital and shareholder loan (SHL) breakdown  
	- Drawdown schedules based on construction timeline
	"""
	
	def __init__(self, financial_model_instance):
		self.model = financial_model_instance

	def initialize(self):
		self._calculate_financing_structure()

	def _calculate_financing_structure(self):
		"""
		Main method to calculate the complete financing structure including:
		- Effective gearing based on debt capacity constraints
		- Equity/debt split
		- Share capital vs shareholder loan allocation
		- Drawdown timing
		"""
		# Initialize the sources dictionary
		self._initialize_sources()
		
		# Calculate financing amounts
		self._calculate_senior_debt_gearing()
		self._calculate_equity_requirement()
		
		# Structure the drawdowns based on injection method
		injection_method = InjectionMethod(self.model.project.injection_choice)
		
		if injection_method == InjectionMethod.EQUITY_FIRST:
			self._calculate_equity_first_drawdowns()
		elif injection_method == InjectionMethod.PRO_RATA:
			self._calculate_pro_rata_drawdowns()
		else:
			raise ValueError(f"Unknown injection method: {injection_method}")
			
		# Split equity into share capital and shareholder loans
		self._allocate_equity_components()
		
		# Calculate totals
		self._calculate_injection_totals()

	def _initialize_sources(self):
		"""Initialize the sources data structure."""
		self.model.financial_model['sources'] = {}
	
	def _calculate_senior_debt_gearing(self):
		"""
		Calculate effective gearing based on actual debt capacity.
		
		Effective debt capacity is the minimum of:
		1. Target gearing × Total project costs
		2. Maximum debt supportable by cash flows (DSCR constraint)
		
		This ensures the debt is both within target parameters and serviceable.
		"""
		total_project_costs = pd.Series(self.model.financial_model['uses']['total']).sum()
		
		# Effective gearing may be lower than target due to DSCR constraints
		self.model.gearing_eff = self.model.senior_debt_amount / total_project_costs
		"""logger.error(self.model.senior_debt_amount)
		logger.error(total_project_costs)"""
	
	def _calculate_equity_requirement(self):
		"""Calculate total equity required as the difference between uses and debt."""
		total_uses = pd.Series(self.model.financial_model['uses']['total']).sum()
		
		self.total_equity_required = (
			total_uses - 
			self.model.senior_debt_amount
		)

		"""logger.error(self.total_equity_required)"""
		

		# Convert subgearing from percentage to decimal
		self.model.subgearing = float(self.model.project.subgearing) / 100
	
	def _calculate_equity_first_drawdowns(self):
		"""
		Calculate drawdowns assuming equity is injected FIRST, then debt.
		
		In this method:
		1. Equity covers all initial project costs up to the total equity requirement
		2. Debt is only drawn after all equity has been injected
		3. This demonstrates sponsor commitment by funding early costs with equity
		"""
		logger.info("Calculating equity-first injection schedule")
		
		# Get period-by-period project costs
		period_costs = self.model.financial_model['uses']['total']
		cumulative_costs = self.model.financial_model['uses']['total_cumul']

		
		# Initialize arrays
		equity_drawdowns = np.zeros_like(period_costs)
		debt_drawdowns = np.zeros_like(period_costs)
		
		# Calculate cumulative equity and debt requirements
		for period in range(len(period_costs)):
			cumulative_cost_to_date = cumulative_costs[period]
			
			
			# Get previous cumulative cost (0 for first period)
			prev_cumulative = cumulative_costs[period - 1] if period > 0 else 0
			
			if prev_cumulative >= self.total_equity_required:
				# Pure debt phase - all equity has been drawn
				equity_drawdowns[period] = 0
				debt_drawdowns[period] = period_costs[period]
				
			elif cumulative_cost_to_date <= self.total_equity_required:
				# Still within equity-only phase
				# All costs in this period are covered by equity
				equity_drawdowns[period] = period_costs[period]
				debt_drawdowns[period] = 0
				
			else:
				# Transition period - we cross from equity to debt in this period
				# Equity covers remaining amount up to total equity requirement
				remaining_equity = self.total_equity_required - prev_cumulative
				equity_drawdowns[period] = remaining_equity
				debt_drawdowns[period] = period_costs[period] - remaining_equity
		
		# Store the calculated drawdowns
		self.model.financial_model['sources']['equity'] = equity_drawdowns
		self.model.financial_model['sources']['senior_debt'] = debt_drawdowns
		
		
		# Validation: ensure totals match requirements
		total_equity_drawn = np.sum(equity_drawdowns)
		total_debt_drawn = np.sum(debt_drawdowns)

		
		if not np.isclose(total_equity_drawn, self.total_equity_required, rtol=1e-10):
			logger.warning(f"Equity drawn ({total_equity_drawn:,.0f}) doesn't match requirement ({self.total_equity_required:,.0f})")
		
		if not np.isclose(total_debt_drawn, self.model.senior_debt_amount, rtol=1e-10):
			logger.warning(f"Debt drawn ({total_debt_drawn:,.0f}) doesn't match capacity ({self.model.senior_debt_amount:,.0f})")
	
	def _calculate_pro_rata_drawdowns(self):
		"""
		Calculate drawdowns assuming debt and equity are drawn proportionally.
		
		This maintains the target capital structure throughout construction,
		which some lenders prefer for risk management.
		"""
		logger.info("Calculating pro-rata injection schedule")
		
		# Calculate debt drawdown schedule based on gearing ratio
		cumulative_debt_drawdowns = np.clip(
			pd.Series(self.model.financial_model['uses']['total_cumul']) * self.model.gearing_eff,
			a_min=None,  # No minimum constraint
			a_max=self.model.senior_debt_amount  # Cap at total debt capacity
		)

		"""logger.error(self.model.gearing_eff)"""
		
		# Convert cumulative to period-by-period amounts
		debt_drawdowns = np.ediff1d(
			cumulative_debt_drawdowns,
			to_begin=cumulative_debt_drawdowns[0]  # First period = first cumulative amount
		)
		
		# Equity fills the gap between total uses and debt in each period
		equity_drawdowns = (
			self.model.financial_model['uses']['total'] - debt_drawdowns
		)


		self.model.financial_model['sources']['senior_debt'] = debt_drawdowns
		self.model.financial_model['sources']['equity'] = equity_drawdowns
	
	def _allocate_equity_components(self):
		"""
		Split total equity between share capital and shareholder loans (SHL).
		
		Share capital: Permanent equity investment
		SHL: Subordinated debt that can potentially be repaid to shareholders
		"""
		total_equity = self.model.financial_model['sources']['equity']
		
		
		# Share capital = equity × (1 - subgearing percentage)
		self.model.financial_model['sources']['share_capital'] = (
			total_equity * (1 - self.model.subgearing)
		)
		
		# Shareholder loans = equity × subgearing percentage  
		self.model.financial_model['sources']['SHL'] = (
			total_equity * self.model.subgearing
		)
	
	def _calculate_injection_totals(self):
		"""Calculate total sources (should equal total uses)."""
		self.model.financial_model['sources']['total'] = (
			self.model.financial_model['sources']['senior_debt'] + 
			self.model.financial_model['sources']['equity']
		)
		
		# Validation check
		total_sources = pd.Series(self.model.financial_model['sources']['total']).sum()
		total_uses = pd.Series(self.model.financial_model['uses']['total']).sum()


		if not np.isclose(total_sources, total_uses, rtol=1e-10):
			logger.warning(f"sources ({total_sources:,.0f}) don't match uses ({total_uses:,.0f})")
	
	def get_financing_summary(self) -> Dict[str, Any]:
		"""
		Return a summary of the financing structure for reporting.
		
		Returns:
			Dictionary containing key financing metrics and amounts
		"""
		return {
			'total_project_cost': pd.Series(self.model.financial_model['uses']['total']).sum(),
			'senior_debt_amount': self.model.senior_debt_amount,
			'total_equity_amount': self.total_equity_required,
			'effective_gearing': self.model.gearing_eff,
			'subgearing_percentage': self.model.subgearing,
			'injection_method': InjectionMethod(self.model.project.injection_choice).name
		}
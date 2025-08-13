import numpy as np
from typing import Dict


class IncomeStatementHelper:
	"""
	Helper class for Income Statement calculations.
	Provides utility functions without managing the period-by-period flow.
	"""
	
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model
		self.corporate_income_tax_rate = float(instance.project.corporate_income_tax) / 100
	
	def calculate_ebitda(self, period: int) -> Dict[str, float]:
		"""
		Calculate EBITDA and EBITDA margin for a specific period.
		
		Parameters:
		-----------
		period: int - Current period index
		
		Returns:
		--------
		dict with keys: ebitda, ebitda_margin
		"""
		revenues = self.financial_model['revenues']['total'][period]
		opex = self.financial_model['opex']['total'][period]
		
		ebitda = revenues - opex
		ebitda_margin = ebitda / revenues if revenues > 0 else 0
		
		return {
			'ebitda': ebitda,
			'ebitda_margin': ebitda_margin
		}
	
	def calculate_income_statement_items(self, period: int, 
										ebitda: float,
										depreciation: float,
										senior_debt_interest: float,
										shl_interest: float) -> Dict[str, float]:
		"""
		Calculate all income statement items for a specific period.
		
		Parameters:
		-----------
		period: int - Current period index
		ebitda: float - EBITDA for the period
		depreciation: float - Depreciation for the period
		senior_debt_interest: float - Senior debt interest for the period
		shl_interest: float - Shareholder loan interest for the period
		
		Returns:
		--------
		dict with keys: ebit, ebt, corporate_income_tax, net_income
		"""
		# Calculate EBIT
		ebit = ebitda + depreciation
		
		# Calculate EBT (Earnings Before Tax)
		ebt = ebit - senior_debt_interest - shl_interest
		
		# Calculate corporate income tax (cannot be negative)
		corporate_income_tax = max(0, self.corporate_income_tax_rate * ebt)
		
		# Calculate net income
		net_income = ebt - corporate_income_tax
		
		return {
			'ebit': ebit,
			'ebt': ebt,
			'corporate_income_tax': corporate_income_tax,
			'net_income': net_income
		}
	
	def calculate_retained_earnings(self, period: int,
								   retained_earnings_bop: float,
								   net_income: float,
								   dividends_paid: float) -> Dict[str, float]:
		"""
		Calculate retained earnings and distributable profit.
		
		Parameters:
		-----------
		period: int - Current period index
		retained_earnings_bop: float - Beginning retained earnings
		net_income: float - Net income for the period
		dividends_paid: float - Dividends paid (should be negative)
		
		Returns:
		--------
		dict with keys: retained_earnings_eop, distributable_profit
		"""
		# Calculate ending retained earnings
		retained_earnings_eop = retained_earnings_bop + net_income + dividends_paid
		
		# Calculate distributable profit (cannot be negative)
		distributable_profit = max(retained_earnings_bop + net_income, 0)
		
		return {
			'retained_earnings_eop': retained_earnings_eop,
			'distributable_profit': distributable_profit
		}
import numpy as np
from typing import Dict

class IncomeStatement:
	"""Refactored to support period-by-period calculation."""
	
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model
		self.corporate_income_tax_rate = float(instance.project.corporate_income_tax) / 100

	def calculate_period(self, period: int) -> Dict[str, float]:
		"""Calculate income statement items for a specific period."""
		# Get required inputs
		ebitda = self.financial_model['EBITDA']['EBITDA'][period]
		depreciation = self.financial_model['IS']['depreciation'][period]
		senior_debt_interest = self.financial_model['senior_debt']['interests_operations'][period]
		shl_interest = self.financial_model['SHL']['interests_operations'][period]
		
		# Calculate EBIT
		ebit = ebitda - depreciation
		
		# Calculate EBT
		ebt = ebit - senior_debt_interest - shl_interest
		
		# Calculate corporate income tax
		corporate_tax = max(0, self.corporate_income_tax_rate * ebt)
		
		# Calculate net income
		net_income = ebt - corporate_tax
		
		return {
			'Contracted revenues': self.financial_model['revenues']['contract'],
			'Merchant revenues': self.financial_model['revenues']['merchant'],
			'Total revenues': self.financial_model['revenues']['total'],

			'EBITDA': ebitda,			
			'EBIT': ebit,
			'EBT': ebt,
			'corporate_income_tax': corporate_tax,
			'net_income': net_income
		}

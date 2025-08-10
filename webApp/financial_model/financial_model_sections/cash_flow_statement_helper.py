import numpy as np
from typing import Dict


class CashFlowStatementHelper:
	"""
	Helper class for Cash Flow Statement calculations.
	Provides utility functions without managing the period-by-period flow.
	"""
	
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model
	
	def calculate_operating_cash_flows(self, period: int,
									  ebitda: float,
									  working_cap_movement: float,
									  corporate_tax: float) -> float:
		"""
		Calculate operating cash flows for a specific period.
		
		Parameters:
		-----------
		period: int - Current period index
		ebitda: float - EBITDA for the period
		working_cap_movement: float - Working capital movement
		corporate_tax: float - Corporate tax paid (should be negative)
		
		Returns:
		--------
		float - Operating cash flows
		"""
		return ebitda + working_cap_movement + corporate_tax
	
	def calculate_investing_cash_flows(self, period: int) -> Dict[str, float]:
		"""
		Calculate investing cash flows and their components for a specific period.
		
		Parameters:
		-----------
		period: int - Current period index
		
		Returns:
		--------
		dict with individual components and total investing cash flows
		"""
		uses = self.financial_model['uses']
		
		# All investing items are outflows (negative)
		construction_costs = -uses['construction'][period]
		development_fee = -uses['development_fee'][period]
		senior_debt_interests_construction = -uses['interests_construction'][period]
		senior_debt_upfront_fee = -uses['upfront_fee'][period]
		senior_debt_commitment_fees = -uses['commitment_fees'][period]
		local_taxes = -uses['local_taxes'][period]
		
		# Reserves might come from elsewhere, check if it exists
		reserves = self.financial_model['op_account'].get('reserves', np.zeros(len(uses['construction'])))[period]
		
		cash_flows_investing = (
			construction_costs +
			development_fee +
			senior_debt_interests_construction +
			senior_debt_upfront_fee +
			senior_debt_commitment_fees +
			reserves +
			local_taxes
		)
		
		return {
			'construction_costs': construction_costs,
			'development_fee': development_fee,
			'senior_debt_interests_construction': senior_debt_interests_construction,
			'senior_debt_upfront_fee': senior_debt_upfront_fee,
			'senior_debt_commitment_fees': senior_debt_commitment_fees,
			'reserves': reserves,
			'local_taxes': local_taxes,
			'cash_flows_investing': cash_flows_investing
		}
	
	def calculate_financing_cash_flows(self, period: int) -> float:
		"""
		Calculate financing cash flows for a specific period.
		
		Parameters:
		-----------
		period: int - Current period index
		
		Returns:
		--------
		float - Financing cash flows
		"""
		sources = self.financial_model['sources']
		
		return (
			sources['senior_debt'][period] +
			sources['SHL'][period] +
			sources['share_capital'][period]
		)
	
	def calculate_cfads(self, period: int,
					   cash_flows_operating: float,
					   cash_flows_investing: float,
					   cash_flows_financing: float) -> Dict[str, float]:
		"""
		Calculate CFADS and its variations for a specific period.
		
		Parameters:
		-----------
		period: int - Current period index
		cash_flows_operating: float - Operating cash flows
		cash_flows_investing: float - Investing cash flows
		cash_flows_financing: float - Financing cash flows
		
		Returns:
		--------
		dict with keys: cfads, cfads_amo, cfads_operations
		"""
		flags = self.financial_model['flags']
		
		# Total CFADS
		cfads = cash_flows_operating + cash_flows_investing + cash_flows_financing
		
		# CFADS during debt amortization period
		cfads_amo = cfads * flags['debt_amo'][period]
		
		# CFADS during operations
		cfads_operations = cfads * flags['operations'][period]
		
		return {
			'cfads': cfads,
			'cfads_amo': cfads_amo,
			'cfads_operations': cfads_operations
		}
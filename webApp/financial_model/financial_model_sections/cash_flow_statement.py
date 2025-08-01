import pandas as pd
import numpy as np
from typing import Dict

class CashFlowStatement:
	"""Refactored to support period-by-period calculation."""
	
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def calculate_period(self, period: int) -> Dict[str, float]:
		"""Calculate cash flows for a specific period."""
		# Operating cash flows
		ebitda = self.financial_model['IS']['EBITDA'][period]
		working_cap_movement = self.financial_model['working_cap']['working_cap_movement'][period]
		corporate_tax = self.financial_model['IS']['corporate_income_tax'][period]
		
		cash_flows_operating = ebitda + working_cap_movement - corporate_tax
		
		# Investing cash flows
		construction_costs = self.financial_model['uses']['construction'][period]
		development_fee = self.financial_model['uses']['development_fee'][period]
		
		cash_flows_investing = -(construction_costs + development_fee)
		
		# Financing cash flows
		financing_outflows = (
			self.financial_model['senior_debt']['upfront_fee'][period] +
			self.financial_model['senior_debt']['interests_construction'][period] +
			self.financial_model['senior_debt']['commitment_fees'][period]
		)
		
		financing_inflows = (
			self.financial_model['sources']['senior_debt'][period] +
			self.financial_model['sources']['equity'][period]
		)
		
		cash_flows_financing = financing_inflows - financing_outflows
		
		# CFADS
		cfads = cash_flows_operating + cash_flows_investing + cash_flows_financing
		
		flags = self.financial_model['flags']
		cfads_amo = cfads * flags['debt_amo'][period]
		cfads_operations = cfads * flags['operations'][period]
		
		return {
			'cash_flows_operating': cash_flows_operating,
			'cash_flows_investing': cash_flows_investing,
			'cash_flows_financing': cash_flows_financing,
			'CFADS': cfads,
			'CFADS_amo': cfads_amo,
			'CFADS_operations': cfads_operations
		}


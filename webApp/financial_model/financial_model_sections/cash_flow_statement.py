import pandas as pd
import numpy as np


class FinancialModelCashFlowStatement:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):


		# Initialize the 'uses' section if it does not exist
		if 'CFS' not in self.instance.financial_model:
			self.instance.financial_model['CFS'] = {}

		self.instance.financial_model['CFS']['cash_flows_operating'] = self.instance.financial_model['EBITDA']['EBITDA'] + self.instance.financial_model['working_cap']['working_cap_movement'] - self.instance.financial_model['IS']['corporate_income_tax']
		self.instance.financial_model['CFS']['cash_flows_investing'] = - (np.array(self.instance.financial_model['uses']['construction']) + np.array(self.instance.financial_model['uses']['development_fee']))

		self.instance.financial_model['CFS']['cash_flows_financing'] = - (self.instance.financial_model['senior_debt']['upfront_fee'] + self.instance.financial_model['senior_debt']['interests_construction'] + self.instance.financial_model['senior_debt']['commitment_fees'] - self.instance.financial_model['injections']['senior_debt'] - self.instance.financial_model['injections']['equity']) 
		self.instance.financial_model['CFS']['CFADS'] = self.instance.financial_model['CFS']['cash_flows_operating'] + self.instance.financial_model['CFS']['cash_flows_investing'] + self.instance.financial_model['CFS']['cash_flows_financing']
		self.instance.financial_model['CFS']['CFADS_amo'] = self.instance.financial_model['CFS']['CFADS'] * self.instance.financial_model['flags']['debt_amo']
		self.instance.financial_model['CFS']['CFADS_operations'] = self.instance.financial_model['CFS']['CFADS'] * self.instance.financial_model['flags']['operations']

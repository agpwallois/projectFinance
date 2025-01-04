import pandas as pd
import numpy as np


class FinancialModelRevenues:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		self.instance.financial_model['revenues'] = {}
		self.instance.financial_model['revenues']['contract'] = (
			self.instance.financial_model['production']['total'] *
			self.instance.financial_model['price']['contract_nom'] / 1000 *
			self.instance.financial_model['time_series']['pct_in_contract_period'] *
			self.instance.financial_model['time_series']['pct_in_operations_period']
		)
		self.instance.financial_model['revenues']['merchant'] = (
			self.instance.financial_model['production']['total'] *
			self.instance.financial_model['price']['merchant_nom'] / 1000 *
			(1 - pd.Series(self.instance.financial_model['time_series']['pct_in_contract_period'])) *
			self.instance.financial_model['time_series']['pct_in_operations_period']
		)
		self.instance.financial_model['revenues']['total'] = (
			self.instance.financial_model['revenues']['contract'] +
			self.instance.financial_model['revenues']['merchant']
		)
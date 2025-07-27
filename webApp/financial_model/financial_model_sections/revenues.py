import pandas as pd
import numpy as np


class Revenues:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self):
		self._initialize_revenues_section()
		self._calculate_contract_revenues()
		self._calculate_merchant_revenues()
		self._calculate_total_revenues()

	def _initialize_revenues_section(self):
		"""Ensure the 'revenues' section exists in the financial model."""
		if 'revenues' not in self.financial_model:
			self.financial_model['revenues'] = {}

	def _calculate_contract_revenues(self):
		"""Calculate revenues from contracts."""
		production = self.financial_model['production']['total']
		price_contract = self.financial_model['price']['contract_nom'] / 1000
		pct_in_contract = self.financial_model['time_series']['pct_in_contract_period']
		pct_in_operations = self.financial_model['time_series']['pct_in_operations_period']

		self.financial_model['revenues']['contract'] = (
			production * price_contract * pct_in_contract * pct_in_operations
		)

	def _calculate_merchant_revenues(self):
		"""Calculate revenues from merchant sales."""
		production = self.financial_model['production']['total']
		price_merchant = self.financial_model['price']['merchant_nom'] / 1000
		pct_in_contract = pd.Series(self.financial_model['time_series']['pct_in_contract_period'])
		pct_in_operations = self.financial_model['time_series']['pct_in_operations_period']

		self.financial_model['revenues']['merchant'] = (
			production * price_merchant * (1 - pct_in_contract) * pct_in_operations
		)

	def _calculate_total_revenues(self):
		"""Calculate total revenues."""
		self.financial_model['revenues']['total'] = (
			self.financial_model['revenues']['contract'] +
			self.financial_model['revenues']['merchant']
		)

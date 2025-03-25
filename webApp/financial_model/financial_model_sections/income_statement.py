import numpy as np


class FinancialModelIncomeStatement:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model
		self.instance.corporate_income_tax_rate = float(self.instance.project.corporate_income_tax) / 100

	def initialize(self):
		self._calculate_ebit()
		self._calculate_ebt()
		self._calculate_corporate_income_tax()
		self._calculate_net_income()

	def _calculate_ebit(self):
		"""Calculate EBIT (Earnings Before Interest and Taxes)."""
		self.financial_model['IS']['EBIT'] = (
			self.financial_model['EBITDA']['EBITDA'] -
			self.financial_model['IS']['depreciation']
		)

	def _calculate_ebt(self):
		"""Calculate EBT (Earnings Before Tax)."""
		self.financial_model['IS']['EBT'] = (
			self.financial_model['IS']['EBIT'] -
			self.financial_model['senior_debt']['interests_operations'] -
			self.financial_model['SHL']['interests_operations']
		)

	def _calculate_corporate_income_tax(self):
		"""Calculate corporate income tax."""
		self.financial_model['IS']['corporate_income_tax'] = np.clip(
			self.instance.corporate_income_tax_rate * self.financial_model['IS']['EBT'],
			0,
			None
		)

	def _calculate_net_income(self):
		"""Calculate net income."""
		self.financial_model['IS']['net_income'] = (
			self.financial_model['IS']['EBT'] -
			self.financial_model['IS']['corporate_income_tax']
		)

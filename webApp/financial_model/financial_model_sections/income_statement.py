import numpy as np


class FinancialModelIncomeStatement:
	def __init__(self, instance):
		self.instance = instance
		self.instance.corporate_income_tax_rate = float(self.instance.project.corporate_income_tax) / 100

	def initialize(self):


		

		self.instance.financial_model['IS']['EBIT'] = self.instance.financial_model['EBITDA']['EBITDA'] - self.instance.financial_model['IS']['depreciation']
		self.instance.financial_model['IS']['EBT'] = self.instance.financial_model['IS']['EBIT'] - self.instance.financial_model['senior_debt']['interests_operations'] - self.instance.financial_model['SHL']['interests_operations']
		
		self.instance.financial_model['IS']['corporate_income_tax'] = np.clip(self.instance.corporate_income_tax_rate * self.instance.financial_model['IS']['EBT'], 0, None)
		self.instance.financial_model['IS']['net_income'] = self.instance.financial_model['IS']['EBT'] - self.instance.financial_model['IS']['corporate_income_tax']
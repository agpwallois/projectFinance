import numpy as np


class FinancialModelEBITDA:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		self.instance.financial_model['EBITDA'] = {}
		self.instance.financial_model['EBITDA']['EBITDA'] = (
			self.instance.financial_model['revenues']['total'] -
			self.instance.financial_model['opex']['total']
		)
		self.instance.financial_model['EBITDA']['EBITDA_margin'] = np.where(
			self.instance.financial_model['revenues']['total'] > 0,
			np.divide(
				self.instance.financial_model['EBITDA']['EBITDA'],
				self.instance.financial_model['revenues']['total']
			),
			0
		)


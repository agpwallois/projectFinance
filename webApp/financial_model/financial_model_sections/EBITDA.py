import numpy as np


class FinancialModelEBITDA:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self):
		self._initialize_ebitda_section()
		self._compute_ebitda()
		self._compute_ebitda_margin()

	def _initialize_ebitda_section(self):
		if 'EBITDA' not in self.financial_model:
			self.financial_model['EBITDA'] = {}

	def _compute_ebitda(self):
		revenues = self.financial_model['revenues']['total']
		opex = self.financial_model['opex']['total']
		self.financial_model['EBITDA']['EBITDA'] = revenues - opex

	def _compute_ebitda_margin(self):
		revenues = self.financial_model['revenues']['total']
		ebitda = self.financial_model['EBITDA']['EBITDA']
		self.financial_model['EBITDA']['EBITDA_margin'] = np.where(
			revenues > 0,
			np.divide(ebitda, revenues),
			0
		)

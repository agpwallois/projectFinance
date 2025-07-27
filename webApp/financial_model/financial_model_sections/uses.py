import numpy as np
import pandas as pd


class Uses:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self):
		"""Calculates and updates the 'uses' section of the financial model."""
		self._initialize_uses_section()
		self._calculate_uses_categories()
		self._ensure_types_section()
		self._calculate_total_uses()
		self._calculate_total_depreciable_uses()

	def _initialize_uses_section(self):
		"""Ensure the 'uses' section exists in the financial model."""
		if 'uses' not in self.financial_model:
			self.financial_model['uses'] = {}

	def _calculate_uses_categories(self):
		"""Calculate individual 'uses' categories."""
		uses = self.financial_model['uses']
		uses['construction'] = self.financial_model['construction_costs']['total']
		uses['development_fee'] = 0

		uses['interests_construction'] = self.financial_model['senior_debt']['interests_construction']
		uses['upfront_fee'] = self.financial_model['senior_debt']['upfront_fee']
		uses['commitment_fees'] = self.financial_model['senior_debt']['commitment_fees']





		uses['senior_debt_idc_and_fees'] = (
			self.financial_model['senior_debt']['interests_construction'] +
			self.financial_model['senior_debt']['upfront_fee'] +
			self.financial_model['senior_debt']['commitment_fees']
		)
		uses['reserves'] = self.financial_model['DSRA']['initial_funding']
		uses['local_taxes'] = self.financial_model['local_taxes']['total']

	def _ensure_types_section(self):
		"""Ensure the 'types' section exists in the financial model."""
		if 'types' not in self.financial_model:
			self.financial_model['types'] = {}

	def _calculate_total_uses(self):
		"""Calculate the total 'uses'."""
		uses = self.financial_model['uses']
		uses['total'] = (
			np.array(uses['construction']) +
			np.array(uses['development_fee']) +
			np.array(uses['interests_construction']) +
			np.array(uses['upfront_fee']) +
			np.array(uses['commitment_fees']) +
			np.array(uses['reserves'])
		)

		""" np.array(uses['local_taxes']) """

		uses['total_cumul'] = pd.Series(uses['total']).cumsum()

	def _calculate_total_depreciable_uses(self):
		"""Calculate total depreciable 'uses'."""
		uses = self.financial_model['uses']
		uses['total_depreciable'] = (
			np.array(uses['construction']) +
			np.array(uses['development_fee']) +
			np.array(uses['interests_construction']) +
			np.array(uses['upfront_fee']) +
			np.array(uses['commitment_fees']) +
			np.array(self.financial_model['SHL']['interests_construction'])
		)

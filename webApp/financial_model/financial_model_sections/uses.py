import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class Uses:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self):
		"""Calculates and updates the 'uses' section of the financial model."""
		self._initialize_uses_section()
		self._calculate_uses_categories()
		self._calculate_total_uses_wo_dev_fee()
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

		# ----- 4.5) Development Fee Optimization -----
		if self.instance.project.devfee_choice == 1:
			# Calculate optimized development fee based on debt capacity
			total_uses_wo_dev_fee = self.financial_model['uses']['total_wo_dev_fee'].sum()
			self.instance.development_fee = max(0, self.financial_model['debt_sizing']['target_debt_DSCR']/self.instance.target_gearing - total_uses_wo_dev_fee)
		else:
			self.instance.development_fee = 0

		"""logger.error(self.instance.development_fee)"""

		uses['development_fee'] = float(self.instance.project.devfee_paid_FC) * self.instance.development_fee * self.financial_model['flags']['construction_start'] + float(self.instance.project.devfee_paid_COD) * self.instance.development_fee * self.financial_model['flags']['construction_end']
	

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


	def _calculate_total_uses_wo_dev_fee(self):
		"""Calculate the total 'uses'."""
		uses = self.financial_model['uses']
		uses['total_wo_dev_fee'] = (
			np.array(uses['construction']) +
			np.array(uses['interests_construction']) +
			np.array(uses['upfront_fee']) +
			np.array(uses['commitment_fees']) +
			np.array(uses['reserves'])
		)


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

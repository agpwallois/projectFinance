import numpy as np
import pandas as pd

class FinancialModelUses:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		"""Calculates and updates the 'uses' section of the financial model."""


		# Calculate the 'uses' categories
		self.instance.financial_model['uses']['construction'] = self.instance.financial_model['construction_costs']['total']
		self.instance.financial_model['uses']['development_fee'] = 0
		self.instance.financial_model['uses']['senior_debt_idc_and_fees'] = self.instance.financial_model['senior_debt']['interests_construction'] + self.instance.financial_model['senior_debt']['upfront_fee'] + self.instance.financial_model['senior_debt']['commitment_fees']   
		self.instance.financial_model['uses']['reserves'] = self.instance.financial_model['DSRA']['initial_funding']
		self.instance.financial_model['uses']['local_taxes'] = self.instance.financial_model['local_taxes']['total']

		# Initialize 'types' section if it doesn't exist
		if 'types' not in self.instance.financial_model:
			 self.instance.financial_model['types'] = {}

		# Calculate the total uses
		self.instance.financial_model['uses']['total'] = np.array(self.instance.financial_model['uses']['construction']) + np.array(
			self.instance.financial_model['uses']['development_fee']) + np.array(
			self.instance.financial_model['uses']['senior_debt_idc_and_fees']) + np.array(self.instance.financial_model['uses']['reserves'])

		# Calculate total depreciable uses
		self.instance.financial_model['uses']['total_depreciable'] = np.array(self.instance.financial_model['uses']['construction']) + np.array(
			self.instance.financial_model['uses']['development_fee']) + np.array(
			self.instance.financial_model['uses']['senior_debt_idc_and_fees']) + np.array(self.instance.financial_model['SHL']['interests_construction'])
import pandas as pd
import numpy as np


class WorkingCapital:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self):
		"""Initialize and calculate the working capital components."""
		self._initialize_working_cap_section()
		self._calculate_revenues_in_period_paid()
		self._calculate_accounts_receivable()
		self._calculate_costs_in_period_paid()
		self._calculate_accounts_payable()
		self._calculate_cashflows()
		self._calculate_working_cap_movement()

	def _initialize_working_cap_section(self):
		"""Ensure the 'working_cap' section exists in the financial model."""
		if 'working_cap' not in self.financial_model:
			self.financial_model['working_cap'] = {}

	def _calculate_revenues_in_period_paid(self):
		"""Calculate revenues paid within the period."""
		days_model = pd.Series(self.financial_model['days']['model'])
		payment_delay = self.instance.project.payment_delay_revenues
		revenues_total = self.financial_model['revenues']['total']

		self.financial_model['working_cap']['revenues_in_period_paid'] = (
			(1 - payment_delay / days_model) * revenues_total
		)

	def _calculate_accounts_receivable(self):
		"""Calculate accounts receivable at end and beginning of period."""
		working_cap = self.financial_model['working_cap']
		revenues_total = self.financial_model['revenues']['total']
		revenues_paid = working_cap['revenues_in_period_paid']

		working_cap['accounts_receivable_eop'] = revenues_total - revenues_paid
		working_cap['accounts_receivable_bop'] = np.roll(
			working_cap['accounts_receivable_eop'], 1
		)

	def _calculate_costs_in_period_paid(self):
		"""Calculate costs paid within the period."""
		days_model = pd.Series(self.financial_model['days']['model'])
		payment_delay = self.instance.project.payment_delay_costs
		opex_total = self.financial_model['opex']['total']

		self.financial_model['working_cap']['costs_in_period_paid'] = (
			(1 - payment_delay / days_model) * opex_total
		)

	def _calculate_accounts_payable(self):
		"""Calculate accounts payable at end and beginning of period."""
		working_cap = self.financial_model['working_cap']
		opex_total = self.financial_model['opex']['total']
		costs_paid = working_cap['costs_in_period_paid']

		working_cap['accounts_payable_eop'] = opex_total - costs_paid
		working_cap['accounts_payable_bop'] = np.roll(
			working_cap['accounts_payable_eop'], 1
		)

	def _calculate_cashflows(self):
		"""Calculate cashflows from creditors and debtors."""
		working_cap = self.financial_model['working_cap']

		working_cap['cashflows_from_creditors'] = np.ediff1d(
			working_cap['accounts_receivable_eop'],
			to_begin=working_cap['accounts_receivable_eop'][0]
		)
		working_cap['cashflows_from_debtors'] = np.ediff1d(
			working_cap['accounts_payable_eop'],
			to_begin=working_cap['accounts_payable_eop'][0]
		)

	def _calculate_working_cap_movement(self):
		"""Calculate net working capital movement."""
		working_cap = self.financial_model['working_cap']

		working_cap['working_cap_movement'] = (
			working_cap['cashflows_from_debtors'] -
			working_cap['cashflows_from_creditors']
		)

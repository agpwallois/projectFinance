import pandas as pd
import numpy as np


class FinancialModelWorkingCapital:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		self.instance.financial_model['working_cap'] = {}
		self.instance.financial_model['working_cap']['revenues_in_period_paid'] = (
			(1 - self.instance.project.payment_delay_revenues / pd.Series(self.instance.financial_model['days']['model'])) *
			self.instance.financial_model['revenues']['total']
		)
		self.instance.financial_model['working_cap']['accounts_receivable_eop'] = (
			self.instance.financial_model['revenues']['total'] -
			self.instance.financial_model['working_cap']['revenues_in_period_paid']
		)
		self.instance.financial_model['working_cap']['accounts_receivable_bop'] = np.roll(
			self.instance.financial_model['working_cap']['accounts_receivable_eop'], 1
		)
		self.instance.financial_model['working_cap']['costs_in_period_paid'] = (
			(1 - self.instance.project.payment_delay_costs / pd.Series(self.instance.financial_model['days']['model'])) *
			self.instance.financial_model['opex']['total']
		)
		self.instance.financial_model['working_cap']['accounts_payable_eop'] = (
			self.instance.financial_model['opex']['total'] -
			self.instance.financial_model['working_cap']['costs_in_period_paid']
		)
		self.instance.financial_model['working_cap']['accounts_payable_bop'] = np.roll(
			self.instance.financial_model['working_cap']['accounts_payable_eop'], 1
		)
		self.instance.financial_model['working_cap']['cashflows_from_creditors'] = np.ediff1d(
			self.instance.financial_model['working_cap']['accounts_receivable_eop'],
			to_begin=self.instance.financial_model['working_cap']['accounts_receivable_eop'][0]
		)
		self.instance.financial_model['working_cap']['cashflows_from_debtors'] = np.ediff1d(
			self.instance.financial_model['working_cap']['accounts_payable_eop'],
			to_begin=self.instance.financial_model['working_cap']['accounts_payable_eop'][0]
		)
		self.instance.financial_model['working_cap']['working_cap_movement'] = (
			self.instance.financial_model['working_cap']['cashflows_from_debtors'] -
			self.instance.financial_model['working_cap']['cashflows_from_creditors']
		)
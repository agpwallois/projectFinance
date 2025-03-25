import pandas as pd
import numpy as np


class FinancialModelSeniorDebt:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self):
		self._calculate_balance_eop_and_bop()
		self._calculate_interests()
		self._calculate_upfront_fee()
		self._calculate_senior_debt_availability()
		self._calculate_commitment_fees()
		self._calculate_gearing()

	def _calculate_balance_eop_and_bop(self):
		"""Calculate balance at the end and beginning of the period."""
		senior_debt = self.financial_model['senior_debt']
		injections = self.financial_model['injections']['senior_debt']
		repayments = senior_debt['repayments']

		senior_debt['balance_eop'] = (injections - repayments).cumsum()
		senior_debt['balance_bop'] = (
			senior_debt['balance_eop'] + repayments - injections
		)

	def _calculate_interests(self):
		"""Calculate interests during construction and operations."""
		senior_debt = self.financial_model['senior_debt']
		balance_bop = senior_debt['balance_bop']
		interest_rate = self.instance.senior_debt_interest_rate
		days = self.financial_model['days']

		senior_debt['interests_construction'] = (
			balance_bop * interest_rate * days['debt_interest_construction'] / 360
		)
		senior_debt['interests_operations'] = (
			balance_bop * interest_rate * days['debt_interest_operations'] / 360
		)
		senior_debt['interests'] = (
			senior_debt['interests_construction'] + senior_debt['interests_operations']
		)

	def _calculate_upfront_fee(self):
		"""Calculate the upfront fee."""
		self.financial_model['senior_debt']['upfront_fee'] = (
			pd.Series(self.financial_model['flags']['construction_start']) *
			self.instance.senior_debt_amount *
			self.instance.senior_debt_upfront_fee
		)

	def _calculate_senior_debt_availability(self):
		"""Calculate senior debt availability at EOP and BOP."""
		senior_debt = self.financial_model['senior_debt']
		flags = self.financial_model['flags']
		injections = self.financial_model['injections']['senior_debt']

		senior_debt['senior_debt_available_eop'] = (
			(self.instance.senior_debt_amount - senior_debt['balance_bop']) *
			flags['construction']
		)
		senior_debt['senior_debt_available_bop'] = (
			senior_debt['senior_debt_available_eop'] + injections
		)

	def _calculate_commitment_fees(self):
		"""Calculate commitment fees."""
		senior_debt = self.financial_model['senior_debt']
		days = self.financial_model['days']

		senior_debt['commitment_fees'] = (
			senior_debt['senior_debt_available_bop'] *
			self.instance.senior_debt_commitment_fee *
			days['model'] / 360
		)

	def _calculate_gearing(self):
		"""Calculate effective gearing."""
		uses_total = pd.Series(self.financial_model['uses']['total']).sum()
		self.instance.gearing_eff = self.instance.senior_debt_amount / uses_total

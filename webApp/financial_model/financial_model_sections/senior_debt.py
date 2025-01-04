import pandas as pd
import numpy as np

class FinancialModelSeniorDebt:
	def __init__(self, instance):
		self.instance = instance


	def initialize(self):
		# Calculate balance at the end of the period (EOP) and beginning of the period (BOP)
		self.instance.financial_model['senior_debt']['balance_eop'] = (self.instance.financial_model['injections']['senior_debt'] - self.instance.financial_model['senior_debt']['repayments']).cumsum()
		self.instance.financial_model['senior_debt']['balance_bop'] = self.instance.financial_model['senior_debt']['balance_eop'] + self.instance.financial_model['senior_debt']['repayments'] - self.instance.financial_model['injections']['senior_debt']

		# Calculate interests during construction and operations
		self.instance.financial_model['senior_debt']['interests_construction'] = self.instance.financial_model['senior_debt']['balance_bop'] * self.instance.senior_debt_interest_rate * self.instance.financial_model['days']['debt_interest_construction'] / 360
		self.instance.financial_model['senior_debt']['interests_operations'] = self.instance.financial_model['senior_debt']['balance_bop'] * self.instance.senior_debt_interest_rate * self.instance.financial_model['days']['debt_interest_operations'] / 360

		# Total interest
		self.instance.financial_model['senior_debt']['interests'] = self.instance.financial_model['senior_debt']['interests_construction'] + self.instance.financial_model['senior_debt']['interests_operations']

		# Calculate upfront fee
		self.instance.financial_model['senior_debt']['upfront_fee'] = pd.Series(self.instance.financial_model['flags']['construction_start']) * self.instance.senior_debt_amount * self.instance.senior_debt_upfront_fee

		# Calculate available senior debt at EOP and BOP
		self.instance.financial_model['senior_debt']['senior_debt_available_eop'] = (self.instance.senior_debt_amount - self.instance.financial_model['senior_debt']['balance_bop']) * self.instance.financial_model['flags']['construction']
		self.instance.financial_model['senior_debt']['senior_debt_available_bop'] = self.instance.financial_model['senior_debt']['senior_debt_available_eop'] + self.instance.financial_model['injections']['senior_debt']

		# Commitment fees
		self.instance.financial_model['senior_debt']['commitment_fees'] = self.instance.financial_model['senior_debt']['senior_debt_available_bop'] * self.instance.senior_debt_commitment_fee * self.instance.financial_model['days']['model'] / 360


		self.instance.gearing_eff = self.instance.senior_debt_amount / pd.Series(self.instance.financial_model['uses']['total']).sum()
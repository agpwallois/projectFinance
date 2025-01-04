
import pandas as pd
import numpy as np


class FinancialModelFinancingPlan:
	def __init__(self, instance):
		self.instance = instance


	def initialize(self):
		self.instance.financial_model['injections'] = {}

		equity_amount = pd.Series(self.instance.financial_model['uses']['total']) - self.instance.senior_debt_amount
		self.instance.gearing_eff = self.instance.senior_debt_amount / pd.Series(self.instance.financial_model['uses']['total']).sum()

		self.instance.subgearing = float(self.instance.project.subgearing) / 100

		if self.instance.project.injection_choice == 1:
			senior_debt_drawdowns_cumul = np.clip(
				pd.Series(self.instance.financial_model['uses']['total_cumul']) * self.instance.gearing_eff, 
				None, 
				self.instance.senior_debt_amount
			)
			self.instance.financial_model['injections']['senior_debt'] = np.ediff1d(
				senior_debt_drawdowns_cumul, 
				to_begin=senior_debt_drawdowns_cumul[0]
			)
			self.instance.financial_model['injections']['equity'] = (
				self.instance.financial_model['uses']['total'] - self.instance.financial_model['injections']['senior_debt']
			)
			self.instance.financial_model['injections']['share_capital'] = (
				self.instance.financial_model['injections']['equity'] * (1 - self.instance.subgearing)
			)
			self.instance.financial_model['injections']['SHL'] = (
				self.instance.financial_model['injections']['equity'] * self.instance.subgearing
			)
			self.instance.financial_model['injections']['total'] = (
				self.instance.financial_model['injections']['senior_debt'] + self.instance.financial_model['injections']['equity']
			)

		elif self.instance.project.injection_choice == 2:
			senior_debt_drawdowns_cumul = np.clip(
				self.instance.financial_model['uses']['total_cumul'] * self.instance.gearing_eff, 
				None, 
				self.instance.senior_debt_amount
			)
			self.instance.financial_model['injections']['senior_debt'] = np.ediff1d(
				senior_debt_drawdowns_cumul, 
				to_begin=senior_debt_drawdowns_cumul[0]
			)
			self.instance.financial_model['injections']['equity'] = (
				self.instance.financial_model['uses']['total'] - self.instance.financial_model['injections']['senior_debt']
			)
			self.instance.financial_model['injections']['share_capital'] = (
				self.instance.financial_model['injections']['equity'] * (1 - self.instance.subgearing)
			)
			self.instance.financial_model['injections']['SHL'] = (
				self.instance.financial_model['injections']['equity'] * self.instance.subgearing
			)
			self.instance.financial_model['injections']['total'] = (
				self.instance.financial_model['injections']['senior_debt'] + self.instance.financial_model['injections']['equity']
			)
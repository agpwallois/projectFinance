
import numpy as np


class FinancialModelSeniorDebtSizing:
	def __init__(self, instance):
		self.instance = instance

	def calculate_senior_debt_amount(self):
		self.instance.financial_model['discount_factor']['avg_interest_rate'] = np.where(self.instance.financial_model['days']['debt_interest_operations'] != 0,np.divide(self.instance.financial_model['senior_debt']['interests_operations'], self.instance.financial_model['senior_debt']['balance_bop'], out=np.zeros_like(self.instance.financial_model['senior_debt']['interests_operations']), where=self.instance.financial_model['senior_debt']['balance_bop'] != 0) / self.instance.financial_model['days']['debt_interest_operations'] * 360,0)	
		self.instance.financial_model['discount_factor']['discount_factor'] = np.where(self.instance.financial_model['flags']['debt_amo'] == 1, (1 / (1 + (self.instance.financial_model['discount_factor']['avg_interest_rate'] * self.instance.financial_model['days']['debt_interest_operations'] / 360))), 1)
		self.instance.financial_model['discount_factor']['discount_factor_cumul'] = self.instance.financial_model['discount_factor']['discount_factor'].cumprod()

		self.instance.financial_model['debt_sizing']['CFADS_amo'] = self.instance.financial_model['CFS']['cash_flows_operating'] * self.instance.financial_model['flags']['debt_amo']
		self.instance.financial_model['debt_sizing']['target_DSCR'] = self.instance.target_DSCR * self.instance.financial_model['flags']['debt_amo']

		self.instance.financial_model['debt_sizing']['target_DS'] = self.instance.financial_model['debt_sizing']['CFADS_amo'] / self.instance.target_DSCR
		self.instance.financial_model['debt_sizing']['target_debt_DSCR'] = sum(self.instance.financial_model['debt_sizing']['target_DS'] * self.instance.financial_model['discount_factor']['discount_factor_cumul'])
		self.instance.financial_model['debt_sizing']['target_debt_gearing'] = self.instance.financial_model['uses']['total'].sum() * self.instance.target_gearing
		self.instance.financial_model['debt_sizing']['target_debt_amount'] = min(self.instance.financial_model['debt_sizing']['target_debt_DSCR'] , self.instance.financial_model['debt_sizing']['target_debt_gearing'])

	def calculate_senior_debt_repayments(self):

		senior_debt_drawdowns_sum  = sum(self.instance.financial_model['injections']['senior_debt'])				
		npv_CFADS = sum(self.instance.financial_model['debt_sizing']['CFADS_amo'] * self.instance.financial_model['discount_factor']['discount_factor_cumul'])
		DSCR_sculpting = npv_CFADS / senior_debt_drawdowns_sum if senior_debt_drawdowns_sum > 0 else 1

		self.instance.financial_model['senior_debt']['target_repayments'] = np.maximum(0, np.minimum(self.instance.financial_model['senior_debt']['balance_bop'], self.instance.financial_model['debt_sizing']['CFADS_amo'] / DSCR_sculpting - self.instance.financial_model['senior_debt']['interests_operations']))
		
		self.instance.financial_model['senior_debt']['DS_effective'] = self.instance.financial_model['senior_debt']['repayments'] + self.instance.financial_model['senior_debt']['interests_operations']

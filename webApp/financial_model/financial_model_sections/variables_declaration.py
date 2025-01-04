
import pandas as pd
import numpy as np


class FinancialModelDeclareVariables:
	def __init__(self, instance):
		self.instance = instance

	def declare_variables(self):
		data_length = len(self.instance.financial_model['dates']['model']['end'])

		self.instance.optimised_devfee = 0
		self.instance.development_fee = np.full(data_length, 0)

		self.instance.financial_model['IS'] = {}
		self.instance.financial_model['IS']['distributable_profit'] = np.full(data_length, 1)

		self.instance.financial_model['op_account'] = {}
		self.instance.financial_model['senior_debt'] = {}
		self.instance.financial_model['discount_factor'] = {}
		self.instance.financial_model['BS'] = {}

		self.instance.financial_model['distr_account'] = {}
		self.instance.financial_model['debt_sizing'] = {}
		self.instance.financial_model['share_capital'] = {}
		self.instance.financial_model['audit'] = {}

		self.instance.financial_model['uses'] = {}
		self.instance.financial_model['uses']['total'] = self.instance.financial_model['construction_costs']['total']
		self.instance.financial_model['uses']['total_cumul'] = self.instance.financial_model['uses']['total'].cumsum()

		self.instance.financial_model['SHL'] = {}
		self.instance.financial_model['SHL']['balance_bop'] = np.full(data_length, 1)
		self.instance.financial_model['SHL']['interests_construction'] = np.full(data_length, 0)
		self.instance.financial_model['SHL']['interests_operations'] = np.full(data_length, 0)

		self.instance.financial_model['op_account']['balance_eop'] = np.full(data_length, 0)

		self.instance.financial_model['DSRA'] = {}
		self.instance.financial_model['DSRA']['dsra_bop'] = np.full(data_length, 0)
		self.instance.financial_model['DSRA']['initial_funding'] = np.full(data_length, 0)
		self.instance.financial_model['DSRA']['dsra_mov'] = np.full(data_length, 0)
		self.instance.initial_funding_max = 0

		self.instance.financial_model['debt_sizing']['target_debt_amount'] = (
			self.instance.financial_model['uses']['total'] * float(self.instance.project.debt_gearing_max) / 100
		)
		self.instance.financial_model['senior_debt']['target_repayments'] = np.full(data_length, 0)

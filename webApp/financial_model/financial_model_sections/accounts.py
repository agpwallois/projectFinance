import pandas as pd
import numpy as np
from pyxirr import xirr
from dateutil.parser import ParserError
from dateutil import parser
import datetime


import numpy as np

class FinancialModelAccounts:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		self.instance.financial_model['distr_account']['cash_available_for_distribution'] = (
			self.instance.financial_model['CFS']['CFADS'] 
			- self.instance.financial_model['senior_debt']['DS_effective'] 
			- self.instance.financial_model['DSRA']['dsra_mov'] 
			- self.instance.project.cash_min * np.array(self.instance.financial_model['flags']['operations'])
		)
		self.instance.financial_model['distr_account']['transfers_distribution_account'] = self.instance.financial_model['distr_account']['cash_available_for_distribution'].clip(lower=0)

		self.instance.financial_model['op_account']['balance_eop'] = self.instance.financial_model['distr_account']['cash_available_for_distribution']  - self.instance.financial_model['distr_account']['transfers_distribution_account']

		# Initial funding 
		self.instance.financial_model['op_account']['balance_eop'] = np.roll(self.instance.financial_model['op_account']['balance_eop'], 1)

		for i in range(self.instance.iteration):
			self._calculate_SHL_interests(i)
			self._distribute_cash()

	def _calculate_SHL_interests(self, i):
		self.instance.financial_model['SHL']['interests_operations'] = np.array(self.instance.financial_model['SHL']['balance_bop']) * self.instance.SHL_margin * self.instance.financial_model['days']['model'] / 360 * self.instance.financial_model['flags']['operations']
		self.instance.financial_model['SHL']['interests_construction'] = np.array(self.instance.financial_model['SHL']['balance_bop']) * self.instance.SHL_margin * self.instance.financial_model['days']['model'] / 360 * self.instance.financial_model['flags']['construction']

	def _distribute_cash(self):
		self.instance.financial_model['SHL']['interests_paid'] = np.minimum(self.instance.financial_model['distr_account']['transfers_distribution_account'], self.instance.financial_model['SHL']['interests_operations'])
		self.instance.financial_model['distr_account']['cash_available_for_dividends'] = self.instance.financial_model['distr_account']['transfers_distribution_account'] - self.instance.financial_model['SHL']['interests_paid']
		self.instance.financial_model['distr_account']['dividends_paid'] = np.minimum(self.instance.financial_model['distr_account']['cash_available_for_dividends'], self.instance.financial_model['IS']['distributable_profit'])

		self.instance.financial_model['distr_account']['cash_available_for_SHL_repayments'] = self.instance.financial_model['distr_account']['cash_available_for_dividends'] - self.instance.financial_model['distr_account']['dividends_paid']
		self.instance.financial_model['SHL']['repayments'] = np.minimum(self.instance.financial_model['SHL']['balance_bop'], self.instance.financial_model['distr_account']['cash_available_for_SHL_repayments'])

		self.instance.financial_model['distr_account']['cash_available_for_redemption'] = self.instance.financial_model['distr_account']['cash_available_for_SHL_repayments'] - self.instance.financial_model['SHL']['repayments']

		self.instance.financial_model['distr_account']['balance_eop'] = (self.instance.financial_model['distr_account']['transfers_distribution_account'] 
																- self.instance.financial_model['SHL']['interests_paid'] 
																- self.instance.financial_model['distr_account']['dividends_paid'] 
																- self.instance.financial_model['SHL']['repayments']).cumsum()
		self.instance.financial_model['distr_account']['balance_bop'] = self.instance.financial_model['distr_account']['balance_eop'] - (self.instance.financial_model['distr_account']['transfers_distribution_account'] 
																												  - self.instance.financial_model['SHL']['interests_paid'] 
																												  - self.instance.financial_model['distr_account']['dividends_paid'] 
																												  - self.instance.financial_model['SHL']['repayments'])

		self.instance.financial_model['SHL']['balance_eop'] = (self.instance.financial_model['injections']['SHL'] 
													 + self.instance.financial_model['SHL']['interests_construction'] 
													 - self.instance.financial_model['SHL']['repayments']).cumsum()
		self.instance.financial_model['SHL']['balance_bop'] = self.instance.financial_model['SHL']['balance_eop'] - (self.instance.financial_model['injections']['SHL'] 
																								 + self.instance.financial_model['SHL']['interests_construction'] 
																								 - self.instance.financial_model['SHL']['repayments'])

		self.instance.financial_model['IS']['retained_earnings_eop'] = (self.instance.financial_model['IS']['net_income'] 
															   - self.instance.financial_model['distr_account']['dividends_paid']).cumsum()
		self.instance.financial_model['IS']['retained_earnings_bop'] = self.instance.financial_model['IS']['retained_earnings_eop'] - (self.instance.financial_model['IS']['net_income'] 
																												 - self.instance.financial_model['distr_account']['dividends_paid'])
		self.instance.financial_model['IS']['distributable_profit'] = np.clip(self.instance.financial_model['IS']['retained_earnings_bop'] + self.instance.financial_model['IS']['net_income'], 0, None)

		self.instance.financial_model['share_capital']['repayments'] = self.instance.financial_model['distr_account']['balance_bop'] * self.instance.financial_model['flags']['liquidation_end']
		self.instance.financial_model['distr_account']['balance_eop'] = self.instance.financial_model['distr_account']['balance_eop'] - self.instance.financial_model['share_capital']['repayments']

		self.instance.financial_model['share_capital']['balance_eop'] = (self.instance.financial_model['injections']['share_capital'] 
																- self.instance.financial_model['share_capital']['repayments']).cumsum()
		self.instance.financial_model['share_capital']['balance_bop'] = self.instance.financial_model['share_capital']['balance_eop'] - (self.instance.financial_model['injections']['share_capital'] 
																											   - self.instance.financial_model['share_capital']['repayments'])

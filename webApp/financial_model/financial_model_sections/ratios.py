import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class FinancialModelRatios:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self):
		self._initialize_ratios()
		self._calculate_avg_interest_rate()
		self._calculate_dscr_effective()
		self._calculate_llcr()
		self._calculate_plcr()
		self._calculate_dscr_stats()
		self._calculate_llcr_min()

	def _initialize_ratios(self):
		"""Initialize the ratios dictionary."""
		if 'ratios' not in self.financial_model:
			self.financial_model['ratios'] = {}

	def _calculate_avg_interest_rate(self):
		"""Calculate the average interest rate for the discount factor."""
		senior_debt = self.financial_model['senior_debt']
		days = self.financial_model['days']

		self.financial_model['discount_factor']['avg_interest_rate'] = np.where(
			days['debt_interest_operations'] != 0,
			np.divide(
				senior_debt['interests_operations'],
				senior_debt['balance_bop'],
				out=np.zeros_like(senior_debt['interests_operations']),
				where=senior_debt['balance_bop'] != 0
			) / days['debt_interest_operations'] * 360,
			0
		)

	def _calculate_dscr_effective(self):
		"""Calculate the Debt Service Coverage Ratio (DSCR)."""
		cfads_amo = np.array(self.financial_model['CFS']['CFADS_amo'])
		ds_effective = np.array(self.financial_model['senior_debt']['DS_effective'])

		self.financial_model['ratios']['DSCR_effective'] = np.divide(
			cfads_amo,
			ds_effective,
			out=np.zeros_like(cfads_amo),
			where=ds_effective != 0
		)

	def _calculate_llcr(self):
		"""Calculate the Loan Life Coverage Ratio (LLCR)."""
		avg_interest_rate = np.array(self.financial_model['discount_factor']['avg_interest_rate'])
		cfads_amo = self.financial_model['CFS']['CFADS_amo']
		balance_eop = self.financial_model['senior_debt']['balance_eop']
		model_end = self.financial_model['dates']['model']['end']

		self.financial_model['ratios']['LLCR'] = calculate_ratio(
			avg_interest_rate, cfads_amo, balance_eop, model_end
		)

	def _calculate_plcr(self):
		"""Calculate the Project Life Coverage Ratio (PLCR)."""
		avg_interest_rate = np.array(self.financial_model['discount_factor']['avg_interest_rate'])
		cfads = self.financial_model['CFS']['CFADS']
		balance_eop = self.financial_model['senior_debt']['balance_eop']
		model_end = self.financial_model['dates']['model']['end']

		self.financial_model['ratios']['PLCR'] = calculate_ratio(
			avg_interest_rate, cfads, balance_eop, model_end
		)

	def _calculate_dscr_stats(self):
		"""Calculate average and minimum DSCR."""
		mask = np.array(self.financial_model['flags']['debt_amo']) == 1
		dscr_effective = np.array(self.financial_model['ratios']['DSCR_effective'][mask])

		self.financial_model['ratios']['DSCR_avg'] = dscr_effective.mean()
		self.financial_model['ratios']['DSCR_min'] = dscr_effective.min()

	def _calculate_llcr_min(self):
		"""Calculate the minimum LLCR."""
		mask = np.array(self.financial_model['flags']['debt_amo']) == 1
		indices = np.where(mask)[0]
		indices_without_last = indices[:-1]

		llcr = np.array(self.financial_model['ratios']['LLCR'][indices_without_last])
		self.financial_model['ratios']['LLCR_min'] = llcr.min()


def calculate_ratio(avg_interest_rate, CFADS, senior_debt_balance_eop, dates_series):
	"""Calculate financial coverage ratios."""
	avg_i = avg_interest_rate[avg_interest_rate > 0].mean()
	discounted_CFADS = compute_npv(CFADS, avg_i, dates_series)
	return divide_with_condition(discounted_CFADS, senior_debt_balance_eop)


def compute_npv(cfads, discount_rate, dates_series):
	"""Compute the Net Present Value (NPV) of CFADS."""
	npvs = []
	dates_series = pd.to_datetime(pd.Series(dates_series), dayfirst=True)

	for i in range(len(cfads)):
		npv = 0
		if cfads[i] > 1:
			for j in range(i, len(cfads)):
				end_date = dates_series[j]
				start_date = dates_series[i] if i == 0 else dates_series[i - 1]
				time_delta = (end_date - start_date).days / 365.25
				npv += cfads[j] / ((1 + discount_rate) ** time_delta)
		npvs.append(npv)
	return npvs


def divide_with_condition(numerator, denominator):
	"""Divide with a condition to avoid division by near-zero values."""
	return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0.01)

import pandas as pd
import numpy as np


class FinancialModelRatios:
	def __init__(self, instance):
		self.instance = instance


	def initialize(self):
		self.instance.financial_model['ratios'] = {}

		self.instance.financial_model['ratios']['DSCR_effective'] = np.divide(
			np.array(self.instance.financial_model['CFS']['CFADS_amo']), 
			np.array(self.instance.financial_model['senior_debt']['DS_effective']), 
			out=np.zeros_like(np.array(self.instance.financial_model['CFS']['CFADS_amo'])), 
			where=np.array(self.instance.financial_model['senior_debt']['DS_effective']) != 0
		)

		self.instance.financial_model['ratios']['LLCR'] = calculate_ratio(
			np.array(self.instance.financial_model['discount_factor']['avg_interest_rate']), 
			self.instance.financial_model['debt_sizing']['CFADS_amo'], 
			self.instance.financial_model['senior_debt']['balance_eop'], 
			self.instance.financial_model['dates']['model']['end']
		)

		self.instance.financial_model['ratios']['PLCR'] = calculate_ratio(
			np.array(self.instance.financial_model['discount_factor']['avg_interest_rate']), 
			self.instance.financial_model['CFS']['CFADS'], 
			self.instance.financial_model['senior_debt']['balance_eop'], 
			self.instance.financial_model['dates']['model']['end']
		)

		mask = np.array(self.instance.financial_model['flags']['debt_amo']) == 1

		self.instance.financial_model['ratios']['DSCR_avg'] = np.array(self.instance.financial_model['ratios']['DSCR_effective'][mask]).mean()
		self.instance.financial_model['ratios']['DSCR_min'] = np.array(self.instance.financial_model['ratios']['DSCR_effective'][mask]).min()

		indices = np.where(mask)[0]
		indices_without_last = indices[:-1]

		self.instance.financial_model['ratios']['LLCR_min'] = np.array(self.instance.financial_model['ratios']['LLCR'][indices_without_last]).min()


def calculate_ratio(avg_interest_rate, CFADS, senior_debt_balance_eop, dates_series):
	
	avg_i = avg_interest_rate[avg_interest_rate > 0].mean()

	discounted_CFADS = compute_npv(CFADS, avg_i, dates_series)

	ratio = divide_with_condition(discounted_CFADS, senior_debt_balance_eop)

	return ratio

def compute_npv(cfads, discount_rate, dates_series):
	npvs = []

	dates_series = pd.Series(dates_series)
	dates_series = pd.to_datetime(dates_series, dayfirst=True)

	series_end_period = dates_series.dt.date
	

	for i in range(len(cfads)):
		npv = 0
		if cfads[i] > 1:
			for j in range(i, len(cfads)):
				end_date = dates_series[j]
				start_date = dates_series[i-1]
				time_delta = (end_date - start_date).days/365.25
				npv += cfads[j] / ((1+discount_rate) ** (time_delta))

			npvs.append(npv)
		else: 
			npvs.append(0)

	return npvs

def divide_with_condition(numerator, denominator):
	# Divide numerator by denominator, set 0 where denominator is less than or equal to 0.01
	return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0.01)
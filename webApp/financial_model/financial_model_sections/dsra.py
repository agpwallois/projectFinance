
import numpy as np


class FinancialModelDSRA:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		self.instance.financial_model['DSRA']['cash_available_for_dsra'] = np.maximum(self.instance.financial_model['CFS']['CFADS_amo'] - self.instance.financial_model['senior_debt']['DS_effective'], 0)
		self.instance.financial_model['DSRA']['dsra_target'] = calc_dsra_target(self.instance.dsra, self.instance.periodicity, np.array(self.instance.financial_model['senior_debt']['DS_effective'])) * np.array(self.instance.financial_model['flags']['debt_amo'])
		self.instance.financial_model['DSRA']['initial_funding'] = calc_dsra_funding(np.array(self.instance.financial_model['DSRA']['dsra_target'])) * np.array(self.instance.financial_model['flags']['construction_end'])
		self.instance.financial_model['DSRA']['dsra_additions_available'] = np.minimum(self.instance.financial_model['DSRA']['cash_available_for_dsra'], self.instance.financial_model['DSRA']['dsra_target'])
		self.instance.financial_model['DSRA']['dsra_additions_required'] = np.maximum(self.instance.financial_model['DSRA']['dsra_target'] - self.instance.financial_model['DSRA']['dsra_bop'], 0)
		self.instance.financial_model['DSRA']['dsra_additions_required_available'] = np.minimum(self.instance.financial_model['DSRA']['dsra_additions_available'], self.instance.financial_model['DSRA']['dsra_additions_required'])
		self.instance.financial_model['DSRA']['dsra_target'] = self.instance.financial_model['DSRA']['dsra_target'] + self.instance.financial_model['DSRA']['initial_funding']
		self.instance.financial_model['DSRA']['dsra_eop'] = np.clip((self.instance.financial_model['DSRA']['initial_funding'] + self.instance.financial_model['DSRA']['dsra_additions_required_available']).cumsum(), 0, self.instance.financial_model['DSRA']['dsra_target'])
		self.instance.financial_model['DSRA']['dsra_eop_mov'] = np.ediff1d(self.instance.financial_model['DSRA']['dsra_eop'], to_begin=self.instance.financial_model['DSRA']['dsra_eop'][0])
		self.instance.financial_model['DSRA']['dsra_additions'] = np.maximum(self.instance.financial_model['DSRA']['dsra_eop_mov'], 0)
		self.instance.financial_model['DSRA']['dsra_release'] = np.minimum(self.instance.financial_model['DSRA']['dsra_eop_mov'], 0)
		self.instance.financial_model['DSRA']['dsra_bop'] = np.roll(self.instance.financial_model['DSRA']['dsra_eop'], 1)
		self.instance.financial_model['DSRA']['dsra_mov'] =(self.instance.financial_model['DSRA']['dsra_eop'] - self.instance.financial_model['DSRA']['dsra_bop'])

		self.instance.initial_funding_max = max(self.instance.financial_model['DSRA']['initial_funding'])


def calc_dsra_target(dsra, periodicity, DS_effective):

	look_forward=int(dsra/periodicity)	

	looking_forward_debt_service = []
	for i in range(len(DS_effective)):
		forward_debt_service = sum(DS_effective[i+1:min(i+1+look_forward, len(DS_effective))])
		looking_forward_debt_service.append(forward_debt_service)

	return looking_forward_debt_service	
	
def calc_dsra_funding(dsra_target):
	
	positive_sum = 0
	count = 0
	for num in dsra_target:
		if num > 0:
			positive_sum += num
			count += 1
		if count == 1:
			break
	return positive_sum

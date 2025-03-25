import numpy as np


class FinancialModelDSRA:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self):
		self._compute_senior_debt_effective()
		self._compute_dsra_cash_flow()
		self._compute_dsra_target()
		self._compute_initial_funding()
		self._compute_dsra_additions_and_movements()
		self._update_initial_funding_max()

	def _compute_senior_debt_effective(self):
		senior_debt = self.financial_model['senior_debt']
		senior_debt['DS_effective'] = (
			senior_debt['repayments'] + senior_debt['interests_operations']
		)

	def _compute_dsra_cash_flow(self):
		dsra = self.financial_model['DSRA']
		senior_debt = self.financial_model['senior_debt']
		dsra['cash_available_for_dsra'] = np.maximum(
			self.financial_model['CFS']['CFADS_amo'] - senior_debt['DS_effective'], 0
		)

	def _compute_dsra_target(self):
		dsra = self.financial_model['DSRA']
		dsra['dsra_target'] = calc_dsra_target(
			self.instance.dsra,
			self.instance.periodicity,
			np.array(self.financial_model['senior_debt']['DS_effective'])
		) * np.array(self.financial_model['flags']['debt_amo'])

	def _compute_initial_funding(self):
		dsra = self.financial_model['DSRA']
		dsra['initial_funding'] = calc_dsra_funding(
			np.array(dsra['dsra_target'])
		) * np.array(self.financial_model['flags']['construction_end'])

	def _compute_dsra_additions_and_movements(self):
		dsra = self.financial_model['DSRA']

		dsra['dsra_additions_available'] = np.minimum(
			dsra['cash_available_for_dsra'], dsra['dsra_target']
		)
		dsra['dsra_additions_required'] = np.maximum(
			dsra['dsra_target'] - dsra.get('dsra_bop', 0), 0
		)
		dsra['dsra_additions_required_available'] = np.minimum(
			dsra['dsra_additions_available'], dsra['dsra_additions_required']
		)
		dsra['dsra_target'] += dsra['initial_funding']
		dsra['dsra_eop'] = np.clip(
			(dsra['initial_funding'] + dsra['dsra_additions_required_available']).cumsum(),
			0,
			dsra['dsra_target']
		)
		dsra['dsra_eop_mov'] = np.ediff1d(dsra['dsra_eop'], to_begin=dsra['dsra_eop'][0])
		dsra['dsra_additions'] = np.maximum(dsra['dsra_eop_mov'], 0)
		dsra['dsra_release'] = np.minimum(dsra['dsra_eop_mov'], 0)
		dsra['dsra_bop'] = np.roll(dsra['dsra_eop'], 1)
		dsra['dsra_mov'] = dsra['dsra_eop'] - dsra['dsra_bop']

	def _update_initial_funding_max(self):
		self.instance.initial_funding_max = max(self.financial_model['DSRA']['initial_funding'])


def calc_dsra_target(dsra, periodicity, DS_effective):
	look_forward = int(dsra / periodicity)
	return [
		sum(DS_effective[i + 1 : min(i + 1 + look_forward, len(DS_effective))])
		for i in range(len(DS_effective))
	]


def calc_dsra_funding(dsra_target):
	for num in dsra_target:
		if num > 0:
			return num
	return 0

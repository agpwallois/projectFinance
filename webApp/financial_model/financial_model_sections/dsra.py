import numpy as np



class FinancialModelDSRA:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model
		self.dsra = self.financial_model['DSRA']
		self.senior_debt = self.financial_model['senior_debt']
		self.flags = self.financial_model['flags']

	def initialize(self):
		"""Initialize DSRA calculations in logical sequence."""
		self._compute_senior_debt_effective()
		self._compute_dsra_cash_flow()
		self._compute_dsra_target()
		self._compute_initial_funding()
		self._compute_dsra_movements()
		self._update_initial_funding_max()

	def _compute_senior_debt_effective(self):
		"""Calculate effective debt service including repayments and interest."""
		self.senior_debt['DS_effective'] = (
			self.senior_debt['repayments'] + self.senior_debt['interests_operations']
		)

	def _compute_dsra_cash_flow(self):
		"""Calculate cash available for DSRA after debt service."""
		self.dsra['cash_available_for_dsra'] = np.maximum(
			self.financial_model['op_account']['CFADS_amo'] - self.senior_debt['DS_effective'], 0
		)

	def _compute_dsra_target(self):
		"""Calculate DSRA target balance based on forward-looking debt service."""
		dsra_target = calc_dsra_target(
			self.instance.dsra,
			self.instance.periodicity,
			np.array(self.senior_debt['DS_effective'])
		)
		self.dsra['dsra_target'] = dsra_target * np.array(self.flags['debt_amo'])

	def _compute_initial_funding(self):
		"""Calculate initial DSRA funding requirement."""
		self.dsra['initial_funding'] = (
			calc_dsra_funding(np.array(self.dsra['dsra_target'])) *
			np.array(self.flags['construction_end'])
		)

	def _compute_dsra_movements(self):
		"""Calculate DSRA movements, additions, and releases for all periods."""
		n_periods = len(self.dsra['dsra_target'])
		effective_target = self.dsra['dsra_target'] + self.dsra['initial_funding']

		for i in range(n_periods):
			self._compute_period_dsra(i, effective_target)

	def _compute_period_dsra(self, period, effective_target):
		"""Calculate DSRA balances and movements for a single period."""
		# Set beginning balance
		self.dsra['dsra_bop'][period] = 0 if period == 0 else self.dsra['dsra_eop'][period - 1]
		
		# Current balance after initial funding
		current_balance = self.dsra['dsra_bop'][period] + self.dsra['initial_funding'][period]
		target_gap = effective_target[period] - current_balance
		
		# Calculate additions or releases
		if target_gap > 0:
			self.dsra['dsra_additions'][period] = min(
				target_gap, self.dsra['cash_available_for_dsra'][period]
			)
		elif target_gap < 0:
			self.dsra['dsra_release'][period] = abs(target_gap)
		
		# Calculate ending balance
		self.dsra['dsra_eop'][period] = (
			current_balance +
			self.dsra['dsra_additions'][period] -
			self.dsra['dsra_release'][period]
		)
		
		# Apply target ceiling
		self._apply_target_ceiling(period, effective_target)
		
		# Calculate net movement
		self.dsra['dsra_mov'][period] = self.dsra['dsra_eop'][period] - self.dsra['dsra_bop'][period]

	def _apply_target_ceiling(self, period, effective_target):
		"""Ensure ending balance doesn't exceed target, releasing excess if needed."""
		if self.dsra['dsra_eop'][period] > effective_target[period]:
			excess = self.dsra['dsra_eop'][period] - effective_target[period]
			self.dsra['dsra_release'][period] += excess
			self.dsra['dsra_eop'][period] = effective_target[period]

	def _update_initial_funding_max(self):
		"""Update instance with maximum initial funding requirement."""
		self.instance.initial_funding_max = max(self.dsra['initial_funding'])

def calc_dsra_target(dsra_months, periodicity, ds_effective):
	"""Calculate DSRA target as sum of forward-looking debt service periods."""
	look_forward_periods = int(dsra_months / periodicity)
	return [
		sum(ds_effective[i + 1:min(i + 1 + look_forward_periods, len(ds_effective))])
		for i in range(len(ds_effective))
	]

def calc_dsra_funding(dsra_target):
	"""Return the first positive DSRA target value for initial funding."""
	return next((target for target in dsra_target if target > 0), 0)
import numpy as np
import logging


class DSRAHelper:
	"""
	Helper class for DSRA calculations.
	Provides utility functions without managing the period-by-period flow.
	"""
	
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model
		self.dsra = self.financial_model['DSRA']
		self.senior_debt = self.financial_model['senior_debt']
		self.flags = self.financial_model['flags']
		self.days_per_year = 360  # Banking convention

	def compute_senior_debt_effective(self):
		"""Calculate effective debt service including repayments and interest."""
		self.senior_debt['DS_effective'] = (
			self.senior_debt['repayments'] + 
			self.senior_debt['interests_operations']
		)
		
	def compute_dsra_targets(self):
		"""Calculate DSRA target balances for all periods based on forward-looking debt service."""
		dsra_target = calc_dsra_target(
			self.instance.dsra,
			self.instance.periodicity,
			np.array(self.senior_debt['DS_effective'])
		)
		self.dsra['dsra_target'] = dsra_target * np.array(self.flags['debt_amo'])
		
	def compute_initial_funding(self):
		"""Calculate initial DSRA funding requirement at construction end."""
		self.dsra['initial_funding'] = (
			calc_dsra_funding(np.array(self.dsra['dsra_target'])) *
			np.array(self.flags['construction_end'])
		)
		# Update instance with maximum initial funding requirement
		self.instance.initial_funding_max = max(self.dsra['initial_funding'])
		
	def calculate_cash_available_for_dsra(self, period: int) -> float:
		"""
		Calculate cash available for DSRA after debt service for a specific period.
		Returns negative value if there's a shortfall requiring DSRA release.
		"""
		return (
			self.financial_model['op_account']['CFADS_amo'][period] - 
			self.senior_debt['DS_effective'][period]
		)
		
	def calculate_dsra_movements(self, period: int, 
								balance_bop: float,
								initial_funding: float,
								target: float,
								cash_available: float) -> dict:
		"""
		Calculate DSRA movements for a single period.
		
		Parameters:
		-----------
		period: int - Current period index
		balance_bop: float - DSRA beginning balance
		initial_funding: float - Initial funding for this period
		target: float - DSRA target for this period
		cash_available: float - Cash available for DSRA (can be negative for shortfalls)
		
		Returns:
		--------
		dict with keys: additions, release, eop, mov
		"""
		# Current balance after initial funding
		current_balance = balance_bop + initial_funding
		effective_target = target + initial_funding
		
		additions = 0
		release = 0
		
		# Check if CFADS is insufficient to cover debt service (shortfall scenario)
		if cash_available < 0:
			# CFADS insufficient - need to release from DSRA to cover shortfall
			# Release up to the shortfall amount, limited by available DSRA balance
			shortfall_release = min(abs(cash_available), current_balance)
			release = shortfall_release
			
			# Update current balance after shortfall release
			current_balance -= shortfall_release
			
			# After covering shortfall, check if we need to release excess
			if current_balance > effective_target:
				excess_release = current_balance - effective_target
				release += excess_release
				current_balance = effective_target
				
		else:
			# CFADS sufficient - normal DSRA management
			target_gap = effective_target - current_balance
			
			if target_gap > 0:
				# Need to add to DSRA (limited by available cash after debt service)
				additions = min(target_gap, cash_available)
			elif target_gap < 0:
				# Release excess from DSRA
				release = abs(target_gap)
		
		# Calculate ending balance
		eop = balance_bop + initial_funding + additions - release
		
		# Apply target ceiling (should not exceed target)
		if eop > effective_target:
			excess = eop - effective_target
			release += excess
			eop = effective_target
		
		# Calculate net movement
		mov = eop - balance_bop
		
		return {
			'additions': additions,
			'release': release,
			'eop': eop,
			'mov': mov
		}


# Standalone utility functions
def calc_dsra_target(dsra_months: float, periodicity: int, ds_effective: np.ndarray) -> list:
	"""
	Calculate DSRA target as sum of forward-looking debt service periods.
	
	Parameters:
	-----------
	dsra_months: float - Number of months of debt service to reserve
	periodicity: int - Period length in months
	ds_effective: np.ndarray - Array of effective debt service amounts
	
	Returns:
	--------
	list of DSRA targets for each period
	"""
	look_forward_periods = int(dsra_months / periodicity)
	return [
		sum(ds_effective[i + 1:min(i + 1 + look_forward_periods, len(ds_effective))])
		for i in range(len(ds_effective))
	]


def calc_dsra_funding(dsra_target: np.ndarray) -> float:
	"""
	Return the first positive DSRA target value for initial funding.
	
	Parameters:
	-----------
	dsra_target: np.ndarray - Array of DSRA targets
	
	Returns:
	--------
	float - First positive target value, or 0 if none exist
	"""
	return next((float(target) for target in dsra_target if target > 0), 0.0)
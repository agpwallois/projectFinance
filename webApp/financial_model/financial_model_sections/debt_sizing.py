import numpy as np
from typing import Any


class SeniorDebtSizing:
	"""
	A class responsible for calculating senior debt sizing and repayments
	in a project’s financial model.
	"""

	def __init__(self, instance: Any) -> None:
		"""
		Initialize the FinancialModelSeniorDebtSizing with a main project instance.

		Args:
			instance: Main object containing the financial model data and
					  relevant parameters (e.g., target_DSCR, target_gearing, etc.).
		"""
		self.instance = instance
		fm = self.instance.financial_model
		fm["debt_sizing"] = {}
		fm['discount_factor'] = {}


	def calculate_senior_debt_amount(self) -> None:
		"""
		Calculates the senior debt amount based on two constraints:
		  1. DSCR-based limit (target_debt_DSCR).
		  2. Gearing-based limit (target_debt_gearing).

		Assigns the final debt amount (target_debt_amount) as the minimum of these two.
		Updates the instance.financial_model dictionary in-place.
		"""
		fm = self.instance.financial_model

		# ----- 1) Average interest rate -----
		with np.errstate(divide='ignore', invalid='ignore'):
			avg_interest_rate = np.divide(
				fm['senior_debt']['interests_operations'],
				fm['senior_debt']['balance_bop'],
				out=np.zeros_like(fm['senior_debt']['interests_operations']),
				where=fm['senior_debt']['balance_bop'] != 0
			)
			# Convert annual rate to period rate by factoring the ratio of days/360
			fm['discount_factor']['avg_interest_rate'] = np.where(
				fm['days']['debt_interest_operations'] != 0,
				avg_interest_rate / fm['days']['debt_interest_operations'] * 360,
				0
			)

		# ----- 2) Periodic discount factor -----
		fm['discount_factor']['discount_factor'] = np.where(
			fm['flags']['debt_amo'] == 1,
			1 / (1 + (fm['discount_factor']['avg_interest_rate'] *
					  fm['days']['debt_interest_operations'] / 360)),
			1
		)
		fm['discount_factor']['discount_factor_cumul'] = (
			fm['discount_factor']['discount_factor'].cumprod()
		)

		# ----- 3) DSCR & CFADS for amortization -----
		fm['debt_sizing']['CFADS_amo'] = (
			fm['op_account']['cash_flows_operating'] * fm['flags']['debt_amo']
		)
		fm['debt_sizing']['target_DSCR'] = (
			self.instance.target_DSCR * fm['flags']['debt_amo']
		)

		# ----- 4) Target Debt (DSCR-based) -----
		fm['debt_sizing']['target_DS'] = (
			fm['debt_sizing']['CFADS_amo'] / self.instance.target_DSCR
		)
		fm['debt_sizing']['target_debt_DSCR'] = np.sum(
			fm['debt_sizing']['target_DS'] *
			fm['discount_factor']['discount_factor_cumul']
		)

		# ----- 5) Target Debt (Gearing-based) -----
		total_uses = fm['uses']['total'].sum()
		fm['debt_sizing']['target_debt_gearing'] = total_uses * self.instance.target_gearing

		# ----- 6) Final Senior Debt Amount -----
		fm['debt_sizing']['target_debt_amount'] = min(
			fm['debt_sizing']['target_debt_DSCR'],
			fm['debt_sizing']['target_debt_gearing']
		)

		

	def calculate_senior_debt_repayments(self) -> None:
		"""
		Calculates the target repayments for senior debt, using a sculpting approach
		driven by CFADS and the ratio of NPV(CFADS) to total senior debt drawdowns.
		Updates the instance.financial_model dictionary in-place.
		"""
		fm = self.instance.financial_model

		# Sum of all senior debt drawdowns
		senior_debt_drawdowns_sum = np.sum(fm['sources']['senior_debt'])

		# Net Present Value (NPV) of CFADS for amortization
		npv_cfads = np.sum(
			fm['debt_sizing']['CFADS_amo'] *
			fm['discount_factor']['discount_factor_cumul']
		)

		# DSCR-based sculpting factor
		if senior_debt_drawdowns_sum > 0:
			DSCR_sculpting = npv_cfads / senior_debt_drawdowns_sum
		else:
			DSCR_sculpting = 1  # Default to 1 to avoid divide-by-zero

		# Target repayments for each period = max(0, min(balance_bop, (CFADS_amo / DSCR_sculpting) - interests_operations))
		fm['senior_debt']['target_repayments'] = np.maximum(
			0,
			np.minimum(
				fm['senior_debt']['balance_bop'],
				fm['debt_sizing']['CFADS_amo'] / DSCR_sculpting -
				fm['senior_debt']['interests_operations']
			)
		)

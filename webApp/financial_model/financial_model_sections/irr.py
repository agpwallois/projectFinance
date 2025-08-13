import datetime
import numpy as np
import pandas as pd
from typing import Optional, Union, List
from pyxirr import xirr, InvalidPaymentsError
from dateutil.parser import ParserError
from dateutil import parser


class FinancialModelIRR:
	"""
	A class responsible for computing various IRRs, valuations,
	and payback times in a financial model.
	"""

	def __init__(self, instance: "YourProjectInstance") -> None:
		"""
		Initializes the FinancialModelIRR class with a project instance
		that holds project data and a mutable financial_model dictionary.

		Args:
			instance: The main project instance object that contains:
					  - project discount_factor_valuation
					  - financial_model dictionary
					  - other relevant project data
		"""
		self.instance = instance
		# Convert the discount factor from percentage to a decimal (e.g., 5% -> 0.05)
		self.instance.valuation_df = float(self.instance.project.discount_factor_valuation) / 100.0

	def initialize(self) -> None:
		"""
		Calculates and populates the financial_model['IRR'] dictionary and additional
		properties in the main instance. Steps include:
		  1. Construct equity and debt cash flows.
		  2. Compute various IRRs (equity, share capital, SHL, project pre/post-tax, senior debt).
		  3. Build the IRR curve, find payback date, and compute payback time.
		  4. Calculate an ongoing 'gearing_during_finplan'.
		  5. Compute present-value-based valuations at different discount rates.
		"""
		# Prepare the IRR sub-dictionary in the financial_model
		self.instance.financial_model["IRR"] = {}

		share_capital_cf = self._get_share_capital_cf()
		SHL_cf = self._get_shl_cf()

		# Equity CF is the sum of share-capital CF and SHL CF
		self.instance.equity_cf = share_capital_cf + SHL_cf
		equity_cf_cumul = self.instance.equity_cf.cumsum()

		# Convert model end dates into a list of date objects
		dates_end = pd.to_datetime(
			self.instance.financial_model["dates"]["model"]["end"], dayfirst=True
		).dt.date

		# Construct project-level cash flows (pre-tax and post-tax)
		project_cf_pre_tax = self._get_project_cf_pre_tax()
		project_cf_post_tax = project_cf_pre_tax + self.instance.financial_model["IS"]["corporate_income_tax"]

		# Construct senior debt cash flows
		debt_cash_flows = self._get_debt_cash_flows()


		self.instance.financial_model["IRR"]["equity_cf"] = share_capital_cf
		self.instance.financial_model["IRR"]["SHL_cf"] = SHL_cf

		# ---- Calculate various IRRs ----
		self.instance.financial_model["IRR"]["equity"] = calculate_xirr(dates_end, self.instance.equity_cf)
		self.instance.financial_model["IRR"]["share_capital"] = calculate_xirr(dates_end, share_capital_cf)
		self.instance.financial_model["IRR"]["SHL"] = calculate_xirr(dates_end, SHL_cf)
		self.instance.financial_model["IRR"]["project_pre_tax"] = calculate_xirr(dates_end, project_cf_pre_tax)
		self.instance.financial_model["IRR"]["project_post_tax"] = calculate_xirr(dates_end, project_cf_post_tax)
		self.instance.financial_model["IRR"]["senior_debt"] = calculate_xirr(dates_end, debt_cash_flows)

		# Store the final equity IRR (as percentage) at instance level
		self.instance.IRR = self.instance.financial_model["IRR"]["equity"] * 100.0

		# ---- Build IRR curve ----
		self.instance.financial_model["IRR"]["irr_curve"] = create_IRR_curve(
			self.instance.equity_cf,
			self.instance.financial_model["dates"]["model"]["end"],
		)

		# ---- Payback date & time ----
		payback_date = find_payback_date(
			pd.Series(self.instance.financial_model["dates"]["model"]["end"]),
			equity_cf_cumul,
		)
		self._populate_payback_info(payback_date)

		# ---- Gearing calculation ----
		self._calculate_gearing_during_finplan()

		# ---- Valuation calculations (today’s date discounting) ----
		self._calculate_current_valuations()





	def _get_share_capital_cf(self) -> pd.Series:
		"""
		Retrieves share capital related cash flows.

		Returns:
			Pandas Series representing the net share capital cash flows.
		"""
		fm = self.instance.financial_model
		return (
			- fm["sources"]["share_capital"]
			- fm["distr_account"]["dividends_paid"]
			+ fm["share_capital"]["repayments"]
		)

	def _get_shl_cf(self) -> pd.Series:
		"""
		Retrieves SHL (shareholder loan) related cash flows.

		Returns:
			Pandas Series representing the net SHL cash flows.
		"""
		fm = self.instance.financial_model
		return (
			- fm["sources"]["SHL"]
			+ fm["SHL"]["interests_operations"]
			+ fm["SHL"]["repayments"]
		)

	def _get_project_cf_pre_tax(self) -> pd.Series:
		"""
		Constructs the pre-tax project cash flows.

		Returns:
			Pandas Series of pre-tax project cash flows.
		"""
		fm = self.instance.financial_model
		return -fm["uses"]["total"] + fm["EBITDA"]["EBITDA"]

	def _get_debt_cash_flows(self) -> pd.Series:
		"""
		Constructs the senior debt cash flows.

		Returns:
			Pandas Series representing net debt cash flows.
		"""
		fm = self.instance.financial_model
		return (
			-fm["sources"]["senior_debt"]
			+ fm["senior_debt"]["repayments"]
			+ fm["senior_debt"]["interests"]
			+ fm["senior_debt"]["upfront_fee"]
			+ fm["senior_debt"]["commitment_fees"]
		)

	def _populate_payback_info(self, payback_date: Optional[str]) -> None:
		"""
		Attempts to parse and compute payback date/time. Updates the financial_model['IRR']
		dictionary with this information.

		Args:
			payback_date: The earliest date at which cumulative equity
						  cash flows become non-negative, as a string.
		"""
		fm_irr = self.instance.financial_model["IRR"]

		if payback_date is None:
			fm_irr["payback_date"] = "error"
			fm_irr["payback_time"] = "error"
			return

		try:
			parsed_date = parser.parse(str(payback_date)).date()
			time_diff = parsed_date - self.instance.project.start_construction
			fm_irr["payback_time"] = round(time_diff.days / 365.25, 1)
			fm_irr["payback_date"] = parsed_date.strftime("%d/%m/%Y")
		except ParserError:
			fm_irr["payback_date"] = "error"
			fm_irr["payback_time"] = "error"



	def _calculate_gearing_during_finplan(self) -> None:
		"""
		Calculates the gearing ratio during the financial plan, defined as:
		cumulative senior debt / (cumulative equity + cumulative senior debt).
		"""
		fm = self.instance.financial_model
		cum_senior_debt = fm["sources"]["senior_debt"].cumsum()
		cum_equity = fm["sources"]["equity"].cumsum()
		fm["gearing_during_finplan"] = cum_senior_debt / (cum_equity + cum_senior_debt)

	def _calculate_current_valuations(self) -> None:
		"""
		Computes equity valuations at multiple discount rates (the valuation_df itself,
		valuation_df - 0.01, and valuation_df + 0.01). This accounts for the time from
		the model’s end dates to today’s date.
		"""
		fm = self.instance.financial_model
		fm_irr = fm["IRR"]

		# Convert model end dates to Timestamps
		end_period = pd.to_datetime(fm["dates"]["model"]["end"], dayfirst=True)
		current_date = pd.Timestamp(datetime.datetime.now().date())

		# Days from each end date to current_date; negative => clip to 0
		time_since_today = end_period.apply(lambda d: (current_date - d).days).clip(lower=0)

		# Store the discount rate variations
		fm_irr["eqt_discount_factor"] = self.instance.valuation_df
		fm_irr["eqt_discount_factor_less_1"] = self.instance.valuation_df - 0.01
		fm_irr["eqt_discount_factor_plus_1"] = self.instance.valuation_df + 0.01

		# Build discount factors
		discount_vector = self._build_discount_vector(time_since_today, fm_irr["eqt_discount_factor"])
		discount_less_1_vector = self._build_discount_vector(time_since_today, fm_irr["eqt_discount_factor_less_1"])
		discount_plus_1_vector = self._build_discount_vector(time_since_today, fm_irr["eqt_discount_factor_plus_1"])

		# Compute present values at each discount rate
		equity_cf = self.instance.equity_cf
		fm_irr["valuation"] = np.sum(equity_cf * discount_vector)
		fm_irr["valuation_less_1"] = np.sum(equity_cf * discount_less_1_vector)
		fm_irr["valuation_plus_1"] = np.sum(equity_cf * discount_plus_1_vector)

	@staticmethod
	def _build_discount_vector(time_since_today: pd.Series, discount_rate: float) -> np.ndarray:
		"""
		Builds a discount factor vector from the time difference (in days) and a given rate.

		Args:
			time_since_today: A Series representing days between each end date and current date.
			discount_rate: The rate used to discount future cash flows.

		Returns:
			A NumPy array of discount factors.
		"""
		return np.where(
			time_since_today != 0,
			1 / (1 + discount_rate) ** (time_since_today / 365.0),
			1
		)


# ---------------------- Utility Functions ---------------------- #

def calculate_xirr(dates: Union[pd.Series, List[datetime.date]], cash_flows: pd.Series) -> float:
	"""
	Wrapper around pyxirr's xirr function to handle invalid payments gracefully.

	Args:
		dates: A list or Series of date objects.
		cash_flows: A Series of cash flow amounts (in the same order as dates).

	Returns:
		The XIRR as a float (e.g. 0.1 => 10% IRR). Returns 0 if invalid cash flows are detected.
	"""
	try:
		return xirr(dates, cash_flows)
	except InvalidPaymentsError:
		"""print(f"Warning: Invalid cash flows provided for XIRR calculation: {cash_flows}")"""
		return 0.0


def create_IRR_curve(
	equity_cash_flows: pd.Series,
	series_end_period: Union[pd.Series, List[str]]
) -> List[float]:
	"""
	Creates an IRR curve by calculating the IRR at each incremental step
	in the equity_cash_flows timeline.

	Args:
		equity_cash_flows: The partial or cumulative equity cash flows at each period.
		series_end_period: The string dates representing period ends (in '%d/%m/%Y' format).

	Returns:
		A list of IRR values (as percentages) at each step, clipped to >= 0.
	"""

	equity_cash_flows = pd.Series(equity_cash_flows)

	irr_values = []
	for i in range(1, len(equity_cash_flows) + 1):
		subset_cash_flows = equity_cash_flows.iloc[:i]
		subset_dates = pd.to_datetime(
			pd.Series(series_end_period).iloc[:i],
			dayfirst=True
		).dt.date

		try:
			irr = xirr(subset_dates, subset_cash_flows) * 100.0
		except InvalidPaymentsError:
			irr = 0.0
		except Exception:
			# Catch-all for any other unexpected errors
			irr = 0.0

		# Ensure the IRR is at least 0
		irr_values.append(max(irr, 0.0))

	return irr_values


def find_payback_date(
	series_end_period: pd.Series,
	equity_cash_flows_cumul: pd.Series
) -> Optional[str]:
	"""
	Finds the first date (from series_end_period) at which the cumulative
	equity cash flow is non-negative.

	Args:
		series_end_period: A Series of string dates representing period ends.
		equity_cash_flows_cumul: The cumulative sum of equity cash flows.

	Returns:
		A string representing the earliest payback date, or None if no payback occurs.
	"""
	valid_indices = np.where(equity_cash_flows_cumul >= 0)[0]
	if len(valid_indices) > 0:
		# The earliest date among valid_indices
		payback_idx = valid_indices[np.argmin(series_end_period[valid_indices])]
		return str(series_end_period[payback_idx])
	return None



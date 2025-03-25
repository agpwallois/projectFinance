import pandas as pd
from typing import Any, Dict


class FinancialModelDays:
	"""
	A class responsible for calculating the number of days in various
	periods (model, contracts, etc.) by using start and end dates
	stored in the financial_model dictionary.
	"""

	def __init__(self, instance: Any) -> None:
		"""
		Initialize the FinancialModelDays with the main project instance.

		Args:
			instance: Main object containing the financial_model dictionary
					  along with other data (e.g., flags, periods, etc.).
		"""
		self.instance = instance

	def initialize(self) -> None:
		"""
		Initializes the financial_model['days'] dictionary by:
			1. Building a dictionary of start/end date series and flags.
			2. Converting each date series to Timestamps.
			3. Calculating day counts for each period and storing them.
		"""
		self.instance.financial_model["days"] = {}
		days_series_dict = self._build_days_series_dict()

		for key, value in days_series_dict.items():
			start_dates = self._parse_dates(value["start_dates"])
			end_dates = self._parse_dates(value["end_dates"])

			# Calculate the inclusive day count and multiply by the associated flag
			days_count = (end_dates - start_dates).dt.days.add(1).mul(value["flag"])
			self.instance.financial_model["days"][key] = days_count

	def _build_days_series_dict(self) -> Dict[str, Dict[str, Any]]:
		"""
		Builds a dictionary that maps each period name (e.g. 'model', 'contract')
		to its corresponding date ranges and a 'flag' value used for calculations.

		Returns:
			A dictionary keyed by period names, each containing:
				- "flag": The numeric multiplier used in day calculations.
				- "start_dates": A list or Pandas Series of start dates.
				- "end_dates": A list or Pandas Series of end dates.
		"""
		fm = self.instance.financial_model  # Shortcut for readability

		return {
			"model": {
				"flag": 1,
				"start_dates": fm["dates"]["model"]["start"],
				"end_dates": fm["dates"]["model"]["end"],
			},
			"contract": {
				"flag": fm["flags"]["contract"],
				"start_dates": fm["dates"]["contract"]["start"],
				"end_dates": fm["dates"]["contract"]["end"],
			},
			"contract_indexation": {
				"flag": fm["flags"]["contract_indexation"],
				"start_dates": fm["dates"]["contract_indexation"]["start"],
				"end_dates": fm["dates"]["contract_indexation"]["end"],
			},
			"merchant_indexation": {
				"flag": fm["flags"]["merchant_indexation"],
				"start_dates": fm["dates"]["merchant_indexation"]["start"],
				"end_dates": fm["dates"]["merchant_indexation"]["end"],
			},
			"opex_indexation": {
				"flag": fm["flags"]["opex_indexation"],
				"start_dates": fm["dates"]["opex_indexation"]["start"],
				"end_dates": fm["dates"]["opex_indexation"]["end"],
			},
			"debt_interest_construction": {
				"flag": fm["flags"]["construction"],
				"start_dates": fm["dates"]["debt_interest_construction"]["start"],
				"end_dates": fm["dates"]["debt_interest_construction"]["end"],
			},
			"debt_interest_operations": {
				"flag": fm["flags"]["debt_amo"],
				"start_dates": fm["dates"]["debt_interest_operations"]["start"],
				"end_dates": fm["dates"]["debt_interest_operations"]["end"],
			},
			"operations": {
				"flag": fm["flags"]["operations"],
				"start_dates": fm["dates"]["operations"]["start"],
				"end_dates": fm["dates"]["operations"]["end"],
			},
			"lease_indexation": {
				"flag": fm["flags"]["lease_indexation"],
				"start_dates": fm["dates"]["lease_indexation"]["start"],
				"end_dates": fm["dates"]["lease_indexation"]["end"],
			},
		}

	@staticmethod
	def _parse_dates(date_series: pd.Series) -> pd.Series:
		"""
		Converts a series/list of date strings or Timestamp objects into a pd.Series of Timestamps.

		Args:
			date_series: A series/list of date strings (format '%d/%m/%Y') or Timestamp objects.

		Returns:
			A Pandas Series of Timestamp objects.
		"""
		return pd.to_datetime(pd.Series(date_series), format="%d/%m/%Y", dayfirst=True)

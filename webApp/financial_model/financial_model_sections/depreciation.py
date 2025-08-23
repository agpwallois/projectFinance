import numpy as np
from typing import Any


class Depreciation:
	"""
	A class responsible for calculating and populating the depreciation
	line item in a financial model’s Income Statement.
	"""

	def __init__(self, instance: Any) -> None:
		"""
		Initialize the FinancialModelDepreciation with a main project instance.

		Args:
			instance: The main project instance that holds:
			  - financial_model data (with 'uses', 'time_series', etc.)
			  - project attributes (like 'operating_life').
		"""
		self.instance = instance

	def initialize(self) -> None:
		"""
		Sets up the depreciation in the financial_model['IS'] dictionary by:
		  1. Summing the total depreciable uses.
		  2. Spreading that total depreciation over the operating life, scaled
			 by the time spent in each operation period (years_during_operations).
		"""
		fm = self.instance.financial_model
		
		# Total depreciable amount, e.g., from capital expenditures
		total_depreciable = np.array(fm["uses"]["total_depreciable"]).sum()
		
		# The fraction of each period that falls into the operating phase
		years_during_operations = np.array(fm["time_series"]["years_during_operations"]) * np.array(fm["time_series"]["pct_in_operations_period"]) 
		
		# Retrieve operating life, default to 1 to prevent division by zero
		operating_life = self.instance.project.operating_life or 1
		
		# Distribute total depreciation over each period
		depreciation_schedule = total_depreciable * years_during_operations / operating_life
		
		# Store the calculated depreciation in the Income Statement section
		fm["IS"]["depreciation"] = -1*depreciation_schedule

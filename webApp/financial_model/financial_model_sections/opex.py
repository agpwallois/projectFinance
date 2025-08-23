import numpy as np
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class OperatingExpenses:
	operating_costs: np.ndarray
	lease_costs: np.ndarray
	total: np.ndarray

class Opex:
	"""Handles the calculation of operating expenses in a financial model."""
	
	def __init__(self, instance):
		"""
		Initialize the FinancialModelOpex calculator.
		
		Args:
			instance: The parent financial model instance containing project details
					 and calculation parameters.
		"""
		self.instance = instance
		self._financial_model = instance.financial_model
		self._project = instance.project

	def _get_time_series(self) -> np.ndarray:
		"""Retrieve the years during operations time series."""

		time_series = np.array(self._financial_model['time_series']['years_during_operations']) * np.array(self._financial_model['time_series']['pct_in_operations_period'])                 
		return time_series

	def _get_indexed_costs(self, base_cost: float, index_type: str, sensitivity: float) -> np.ndarray:
		"""
		Calculate costs with indexation and sensitivity adjustment.
		
		Args:
			base_cost: The base cost value to be adjusted
			index_type: The type of indexation to apply ('opex' or 'lease')
			sensitivity: Sensitivity factor for cost adjustment
		
		Returns:
			np.ndarray: Adjusted costs over time
		"""
		indexation = np.array(self._financial_model['indexation'][index_type])
		time_series = self._get_time_series()
		sensitivity_factor = 1 + float(sensitivity)
		
		return base_cost * indexation * time_series * sensitivity_factor

	def initialize(self, sensi_opex: float = 0) -> None:
		"""
		Initialize and calculate all operating expenses.
		
		Args:
			sensi_opex: Sensitivity factor for operating expenses adjustment (default: 0)
		"""
		operating_costs = self._get_indexed_costs(
			self._project.opex,
			'opex',
			sensi_opex
		)
		
		lease_costs = self._get_indexed_costs(
			self._project.lease,
			'lease',
			sensi_opex
		)
		
		total_costs = operating_costs + lease_costs
		
		# Store results in the financial model
		self._financial_model['opex'] = {
			'operating_costs': operating_costs,
			'lease_costs': lease_costs,
			'total': total_costs
		}
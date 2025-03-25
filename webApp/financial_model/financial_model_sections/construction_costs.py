import numpy as np

class FinancialModelConstructionCosts:
	"""
	Handles initialization and calculation of construction costs
	in the financial model.
	"""
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		"""
		Initialize the construction costs series in the financial model.
		"""
		# Ensure local taxes are computed before proceeding
		self.instance.comp_local_taxes()

		# Retrieve required data from the instance
		construction_costs_assumptions = self.instance.construction_costs_assumptions
		construction_flags = self.instance.financial_model['flags'].get('construction')
		operations_flags_length = len(self.instance.financial_model['flags'].get('operations', []))

		# Validate that required inputs are available
		if construction_costs_assumptions is None or construction_flags is None:
			raise ValueError("Construction costs assumptions or flags are not properly initialized.")

		# Create the total construction costs array
		zero_padding = np.zeros(operations_flags_length - len(construction_costs_assumptions))
		total_construction_costs = np.hstack([construction_costs_assumptions, zero_padding]) * construction_flags

		# Assign results to the financial model
		self.instance.financial_model['construction_costs'] = {
			'total': total_construction_costs
		}

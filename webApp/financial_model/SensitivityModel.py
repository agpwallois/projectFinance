from .WindProject import WindProject
from .SolarProject import SolarProject
import copy
import pandas as pd
from .FinancialModel import FinancialModel
from .SolarProject import SolarProject


class SensitivityModel(SolarProject):

	def __init__(self, request, lender_base_case):

		super().__init__(request)
	# Deep copy the financial model instance to create an independent copy
		"""self.__dict__ = copy.deepcopy(lender_base_case.__dict__)"""
			# Deep copy the financial model instance to create an independent copy


	def apply_sensitivity(self, sensitivity_type):
		# Apply the sensitivity to the copy of the Base Case financial model
		if sensitivity_type == 'sensi_production':
			self.initialize_production(sensi_production = self.sensi_production)
		
		elif sensitivity_type == 'sensi_inflation':
			self.initialize_indexation_series(sensi_inflation = self.sensi_inflation)
		
		elif sensitivity_type == 'sensi_opex':
			self.initialize_opex(sensi_opex = self.sensi_opex)
		
		elif sensitivity_type == 'sponsor_production_choice':
			self.production['total'] = self.P50*pd.Series(self.seasonality)*self.capacity['after_degradation']
		
		else:
			
			pass
	
	def recalc_financial_model(self):
		# Rerun the methods on which the sensititiy had an impact and recompute the financial model
		self.initialize_price_series()
		self.initialize_revenues()
		self.initialize_ebitda()
		self.initialize_working_cap()
		self.perform_calculations(with_debt_sizing_sculpting=False)
		self.create_results()
		return self
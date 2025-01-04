import numpy as np

class FinancialModelDepreciation:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
	  
		self.instance.financial_model['IS']['depreciation'] = np.array(self.instance.financial_model['uses']['total_depreciable']).sum() * np.array(self.instance.financial_model['time_series']['years_during_operations']) / self.instance.project.operating_life

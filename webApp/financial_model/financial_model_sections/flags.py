import pandas as pd

class FinancialModelFlags:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		# Parse model start and end dates
		model_end = pd.to_datetime(
			pd.Series(self.instance.financial_model['dates']['model']['end']), 
			format='%d/%m/%Y', dayfirst=True
		)
		model_start = pd.to_datetime(
			pd.Series(self.instance.financial_model['dates']['model']['start']), 
			format='%d/%m/%Y', dayfirst=True
		)

		# Initialize flags
		self.instance.financial_model['flags'] = {}
		
		for name, (start, end) in self.instance.flag_dict.items():
			self.instance.financial_model['flags'][name] = (
				(model_end >= pd.to_datetime(start)) & (model_start <= pd.to_datetime(end))
			).astype(int)

		# Add start_year flag
		self.instance.financial_model['flags']['start_year'] = (model_start.dt.month == 1).astype(int)



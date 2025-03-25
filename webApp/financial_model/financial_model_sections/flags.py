import pandas as pd


class FinancialModelFlags:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self):
		model_start, model_end = self._parse_model_dates()
		self._initialize_flags()
		self._set_flag_values(model_start, model_end)
		self._set_start_year_flag(model_start)

	def _parse_model_dates(self):
		"""Parse model start and end dates into pandas datetime objects."""
		model_start = pd.to_datetime(
			pd.Series(self.financial_model['dates']['model']['start']),
			format='%d/%m/%Y',
			dayfirst=True
		)
		model_end = pd.to_datetime(
			pd.Series(self.financial_model['dates']['model']['end']),
			format='%d/%m/%Y',
			dayfirst=True
		)
		return model_start, model_end

	def _initialize_flags(self):
		"""Ensure the 'flags' dictionary exists in the financial model."""
		if 'flags' not in self.financial_model:
			self.financial_model['flags'] = {}

	def _set_flag_values(self, model_start, model_end):
		"""Set flag values based on the given date ranges."""
		for name, (start, end) in self.instance.flag_dict.items():
			self.financial_model['flags'][name] = (
				(model_end >= pd.to_datetime(start)) &
				(model_start <= pd.to_datetime(end))
			).astype(int)

	def _set_start_year_flag(self, model_start):
		"""Set a flag indicating if the model starts in January."""
		self.financial_model['flags']['start_year'] = (model_start.dt.month == 1).astype(int)

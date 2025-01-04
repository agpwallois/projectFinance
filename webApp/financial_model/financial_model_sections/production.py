

import pandas as pd
import calendar
import numpy as np




class FinancialModelProduction:
	def __init__(self, instance):
		self.instance = instance
		

	def initialize(self, sensi_production=0):

		self.instance.create_capacity_series()

		"""Initialize the seasonality series based on input and dates."""
		self.instance.financial_model['seasonality'] = {}
		self.instance.financial_model['seasonality'] = create_season_series(
			self.instance.seasonality_inp, self.instance.financial_model['dates']
		)

		"""Initialize the production metrics for the financial model."""
		self.instance.financial_model['production'] = {}

		# Total production calculation
		self.instance.financial_model['production']['total'] = (
			self.instance.project.p90_10y / 1000
			* pd.Series(self.instance.financial_model['seasonality'])
			* self.instance.financial_model['capacity']['after_degradation']
			* (1 + float(sensi_production))
		)

		# Contract production calculation
		self.instance.financial_model['production']['contract'] = (
			self.instance.financial_model['production']['total']
			* self.instance.financial_model['time_series']['pct_in_contract_period']
			* self.instance.financial_model['time_series']['pct_in_operations_period']
		)

		# Cumulative production within a year
		self.instance.financial_model['production']['contract_cumul_in_year'] = pd.Series(
			calc_production_cumul(
				self.instance.financial_model['production']['contract'],
				self.instance.financial_model['flags']['start_year']
			)
		)

		# Uncomment and complete if capacity factor calculation is needed
		# self.financial_model['production']['capacity_factor'] = pd.Series(
		#     np.where(
		#         self.financial_model['days']['operations'] > 0,
		#         self.financial_model['production']['total'] / (
		#             (self.installed_capacity * self.financial_model['days']['operations'] * 24) / 1000
		#         ),
		#         0
		#     )
		# )


def create_season_series(seasonality,dates_series):
	
	data = {'start':dates_series['model']['start'],
			'end':dates_series['model']['end']}

	df = pd.DataFrame(data)

	df_seasonality_result = pd.DataFrame(columns=dates_series['model']['end'])

	for index, row in df.iterrows():
		start_date = row['start']
		end_date = row['end']
		dates_in_period = pd.date_range(start=start_date, end=end_date).values.astype('datetime64[D]').tolist()
		
		for i in range(1,13):
			count = 0
			days_in_month = 0

			try:
				for value in dates_in_period:
					
					if value.month == i:
						count += 1
						days_in_month = calendar.monthrange(value.year, value.month)[1]
				
				df_seasonality_result.loc[i,end_date] = count/days_in_month

			except ZeroDivisionError:

				df_seasonality_result.loc[i,end_date] = 0

	df_seasonality_result=df_seasonality_result.mul(seasonality, axis=0)
	arr_time_seasonality = df_seasonality_result.sum(axis=0)
	arr_time_seasonality = arr_time_seasonality.values.tolist()

	return arr_time_seasonality


def calc_production_cumul(production, start_calendar_year):

	cumulative_production = np.zeros_like(production)
	for i in range(len(production)):
		if start_calendar_year[i] == 1:
			cumulative_production[i] = production[i]
		else:
			cumulative_production[i] = cumulative_production[i - 1] + production[i]

	return cumulative_production




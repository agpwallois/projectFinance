
import pandas as pd




class FinancialModelDays:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		self.instance.financial_model['days'] = {}
		days_series_dict = self._get_days_series_dict()

		for key, value in days_series_dict.items():
			end_dates = pd.to_datetime(pd.Series(value['end_dates']), format='%d/%m/%Y', dayfirst=True)
			start_dates = pd.to_datetime(pd.Series(value['start_dates']), format='%d/%m/%Y', dayfirst=True)
			self.instance.financial_model['days'][key] = (((end_dates - start_dates).dt.days + 1) * value['flag'])


	def _get_days_series_dict(self):
		return {
			'model': {
				'flag': 1,
				'start_dates': self.instance.financial_model['dates']['model']['start'],
				'end_dates': self.instance.financial_model['dates']['model']['end'],
			},
			'contract': {
				'flag': self.instance.financial_model['flags']['contract'],
				'start_dates': self.instance.financial_model['dates']['contract']['start'],
				'end_dates': self.instance.financial_model['dates']['contract']['end'],
			},
			'contract_indexation': {
				'flag': self.instance.financial_model['flags']['contract_indexation'],
				'start_dates': self.instance.financial_model['dates']['contract_indexation']['start'],
				'end_dates': self.instance.financial_model['dates']['contract_indexation']['end'],
			},
			'merchant_indexation': {
				'flag': self.instance.financial_model['flags']['merchant_indexation'],
				'start_dates': self.instance.financial_model['dates']['merchant_indexation']['start'],
				'end_dates': self.instance.financial_model['dates']['merchant_indexation']['end'],
			},
			'opex_indexation': {
				'flag': self.instance.financial_model['flags']['opex_indexation'],
				'start_dates': self.instance.financial_model['dates']['opex_indexation']['start'],
				'end_dates': self.instance.financial_model['dates']['opex_indexation']['end'],
			},
			'debt_interest_construction': {
				'flag': self.instance.financial_model['flags']['construction'],
				'start_dates': self.instance.financial_model['dates']['debt_interest_construction']['start'],
				'end_dates': self.instance.financial_model['dates']['debt_interest_construction']['end'],
			},
			'debt_interest_operations': {
				'flag': self.instance.financial_model['flags']['debt_amo'],
				'start_dates': self.instance.financial_model['dates']['debt_interest_operations']['start'],
				'end_dates': self.instance.financial_model['dates']['debt_interest_operations']['end'],
			},
			'operations': {
				'flag': self.instance.financial_model['flags']['operations'],
				'start_dates': self.instance.financial_model['dates']['operations']['start'],
				'end_dates': self.instance.financial_model['dates']['operations']['end'],
			},
			'lease_indexation': {
				'flag': self.instance.financial_model['flags']['lease_indexation'],
				'start_dates': self.instance.financial_model['dates']['lease_indexation']['start'],
				'end_dates': self.instance.financial_model['dates']['lease_indexation']['end'],
			},
		}
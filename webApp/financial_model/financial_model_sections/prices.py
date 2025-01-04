import pandas as pd

class FinancialModelPrices:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		self.instance.financial_model['price'] = {}
		self.instance.financial_model['price']['merchant_real'] = pd.Series(
			array_elec_prices(self.instance.financial_model['time_series']['series_end_period_year'], self.instance.price_elec_low)
		)
		self.instance.financial_model['price']['merchant_nom'] = (
			self.instance.financial_model['price']['merchant_real'] * self.instance.financial_model['indexation']['merchant']
		)
		self.instance.financial_model['price']['contract_real'] = pd.Series(
			self.instance.contract_price * pd.Series(self.instance.financial_model['flags']['contract'])
		).astype(float)
		self.instance.financial_model['price']['contract_nom'] = (
			self.instance.financial_model['price']['contract_real'] * self.instance.financial_model['indexation']['contract']
		)




def array_elec_prices(series_end_period_year, dic_price_elec):
	electricity_prices = []
	
	for row in series_end_period_year:
		if str(row) in dic_price_elec.keys():
			electricity_prices.append(dic_price_elec[str(row)])
		else:
			electricity_prices.append(0)
	
	return electricity_prices
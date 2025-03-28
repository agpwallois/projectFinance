
from .model_financial_model import FinancialModel

class WindFinancialModel(FinancialModel): 

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.installed_capacity = self.project.wind_turbine_installed*1000*self.project.capacity_per_turbine

	def create_capacity_series(self):


		self.financial_model['capacity'] = {}

		self.financial_model['capacity']['before_degradation'] = self.project.installed_capacity*self.financial_model['flags']['operations']
		self.financial_model['capacity']['degradation_factor'] = 1/(1+0)**self.financial_model['time_series']['years_from_COD_avg']
		self.financial_model['capacity']['after_degradation'] = self.financial_model['capacity']['before_degradation']

	def comp_local_taxes(self):

		self.financial_model['local_taxes'] = {}
	
		self.financial_model['local_taxes']['development_tax'] = self.project.wind_turbine_installed*self.project.dev_tax_taxable_base_wind*self.development_tax_rate/1000*self.financial_model['flags']['construction_start']
		self.financial_model['local_taxes']['archeological_tax'] = 0*self.financial_model['flags']['construction_start']
		self.financial_model['local_taxes']['total'] = self.financial_model['local_taxes']['development_tax'] + self.financial_model['local_taxes']['archeological_tax']

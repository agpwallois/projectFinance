
from .model_fm import FinancialModel
import numpy as np

import logging

logger = logging.getLogger(__name__)

class SolarFinancialModel(FinancialModel): 

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.installed_capacity = self.project.panels_capacity

	def create_capacity_series(self):

		self.financial_model['capacity'] = {}

		annual_degradation = float(self.project.annual_degradation)/100

		self.financial_model['capacity']['before_degradation'] = self.project.panels_capacity*self.financial_model['flags']['operations']
		self.financial_model['capacity']['degradation_factor'] = 1/(1+annual_degradation)**np.array(self.financial_model['time_series']['years_from_COD_avg'])

		
		self.financial_model['capacity']['after_degradation'] = self.financial_model['capacity']['before_degradation'] * self.financial_model['capacity']['degradation_factor']

	def comp_local_taxes(self):

		self.financial_model['local_taxes'] = {}

		self.financial_model['local_taxes']['development_tax'] = float(self.project.panels_capacity)*float(self.project.dev_tax_taxable_base_solar)*float(self.development_tax_rate)/1000*self.financial_model['flags']['construction_start']
		self.financial_model['local_taxes']['archeological_tax'] = float(self.project.panels_surface)*float(self.project.archeological_tax_base_solar)*float(self.project.archeological_tax)/1000*self.financial_model['flags']['construction_start']
		self.financial_model['local_taxes']['total'] = self.financial_model['local_taxes']['development_tax'] + self.financial_model['local_taxes']['archeological_tax']


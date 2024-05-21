from .FinancialModel import FinancialModel


class SolarProject(FinancialModel): 

	def __init__(self, request):
		super().__init__(request)
		self.panels_capacity = int(request.POST['panels_capacity'])
		self.degradation = float(request.POST['annual_degradation'])/100
		self.panels_surface = float(request.POST['panels_surface'])
		self.dev_tax_taxable_base_solar = float(request.POST['dev_tax_taxable_base_solar'])
		self.archeological_tax_base_solar = float(request.POST['archeological_tax_base_solar'])
		self.archeological_tax = float(request.POST['archeological_tax'])/100
		self.installed_capacity = self.panels_capacity
		self.contract = request.POST['contract']
		self.contract_price = float(request.POST['contract_price'])

	
	def calc_capacity(self,flag_operations,years_from_COD_avg):
		capacity_before_degradation = self.panels_capacity*flag_operations
		degradation_factor = 1/(1+self.degradation)**years_from_COD_avg
		capacity_after_degradation = capacity_before_degradation * degradation_factor

		capacity = {
			'before_degradation': capacity_before_degradation.tolist(),
			'degradation_factor': degradation_factor.tolist(),
			'after_degradation': capacity_after_degradation.tolist(),
		}
		return capacity
	
	def comp_development_tax(self,development_tax_rate,flag_construction_start):
		development_tax = self.panels_capacity*self.dev_tax_taxable_base_solar*development_tax_rate/1000*flag_construction_start
		development_tax = {
			'development_tax': development_tax.tolist(),
		}
		return development_tax

	def comp_archeological_tax(self,archeological_tax_rate,flag_construction_start):
		archeological_tax = self.panels_surface*self.archeological_tax_base_solar*archeological_tax_rate/1000*flag_construction_start
		archeological_tax = {
			'archeological_tax': archeological_tax.tolist(),
		}
		return archeological_tax


	def comp_contract_price(self):
		contract_price = self.contract_price
		
		return contract_price

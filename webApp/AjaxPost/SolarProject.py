from .FinancialModel import FinancialModel


class SolarProject(FinancialModel): 

	def __init__(self, request):
		super().__init__(request)
		self.panels_capacity = int(request.POST['panels_capacity'])
		self.degradation = float(request.POST['annual_degradation'])/100
		self.panels_surface = float(request.POST['panels_surface'])
		self.dev_tax_taxable_base_solar = float(request.POST['dev_tax_taxable_base_solar'])
		self.archeological_tax_base_solar = float(request.POST['archeological_tax_base_solar'])
		self.archeological_tax_rate = float(request.POST['archeological_tax'])/100
		self.installed_capacity = self.panels_capacity
		self.contract = request.POST['contract']
		self.contract_price = float(request.POST['contract_price'])

	
	def create_capacity_series(self):
		
		self.capacity = {}

		self.capacity['before_degradation'] = self.panels_capacity*self.flags['operations']
		self.capacity['degradation_factor'] = 1/(1+self.degradation)**self.time_series['years_from_COD_avg']
		self.capacity['after_degradation'] = self.capacity['before_degradation'] * self.capacity['degradation_factor']


	def comp_local_taxes(self):

		self.local_taxes = {}

		self.local_taxes['development_tax'] = self.panels_capacity*self.dev_tax_taxable_base_solar*self.development_tax_rate/1000*self.flags['construction_start']
		self.local_taxes['archeological_tax'] = self.panels_surface*self.archeological_tax_base_solar*self.archeological_tax_rate/1000*self.flags['construction_start']
		self.local_taxes['total'] = self.local_taxes['development_tax'] + self.local_taxes['archeological_tax']



	def comp_contract_price(self):
		contract_price = self.contract_price
		
		return contract_price

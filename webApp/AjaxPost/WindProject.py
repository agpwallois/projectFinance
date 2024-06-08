from .FinancialModel import FinancialModel
import pandas as pd


class WindProject(FinancialModel): 

	def __init__(self, request):
		super().__init__(request)
		self.wind_turbine_installed = int(request.POST['wind_turbine_installed'])
		self.capacity_per_turbine = float(request.POST['capacity_per_turbine'])
		self.dev_tax_taxable_base_wind = float(request.POST['dev_tax_taxable_base_wind'])
		self.rotor_diameter = request.POST['rotor_diameter']
		self.installed_capacity = self.wind_turbine_installed*1000*self.capacity_per_turbine
		self.contract = request.POST['contract']
		self.contract_price = float(request.POST['contract_price'])


	def create_capacity_series(self):

		self.capacity = {}

		self.capacity['before_degradation'] = self.installed_capacity*self.flags['operations']
		self.capacity['degradation_factor'] = 1/(1+0)**self.time_series['years_from_COD_avg']
		self.capacity['after_degradation'] = self.capacity['before_degradation']


	def comp_local_taxes(self):

		self.local_taxes = {}
	
		self.local_taxes['development_tax'] = self.wind_turbine_installed*self.dev_tax_taxable_base_wind*self.development_tax_rate/1000*self.flags['construction_start']
		self.local_taxes['archeological_tax'] = 0*self.flags['construction_start']
		self.local_taxes['total'] = self.local_taxes['development_tax'] + self.local_taxes['archeological_tax']





	def comp_contract_price(self):
		contract_price = self.contract_price
		
		return contract_price



"""
def calc_contract_price(contract_type, wind_turbine_installed, rotor_diameter,production_under_contract, production_under_contract_cumul,capacity_factor, days_series,time_series,flags):
	if contract_type == 'FiT':
		return calc_contract_E17_price(wind_turbine_installed,rotor_diameter,production_under_contract, production_under_contract_cumul)
	elif contract_type == 'CfD - E16':
		return calc_contract_E16_price(capacity_factor, days_series,time_series,flags)
	elif contract_type == 'CfD - E17':
		return calc_contract_E17_price(wind_turbine_installed,rotor_diameter,production_under_contract, production_under_contract_cumul)
	elif contract_type == 'CfD - AO':
		return calc_contract_E17_price(wind_turbine_installed,rotor_diameter,production_under_contract, production_under_contract_cumul)
	elif contract_type == 'Corporate PPA':
		return calc_contract_E17_price(wind_turbine_installed,rotor_diameter,production_under_contract, production_under_contract_cumul)
	else:
		raise ValueError("Invalid contract type")


def calc_contract_E17_price(wind_turbine_installed,rotor_diameter,production_under_contract, production_under_contract_cumul):

	# Constants for price calculation
	coefficient_KI = 13/(rotor_diameter/110)
	annual_production_ceiling = 1/20*coefficient_KI*math.pi*(rotor_diameter/2)**2*wind_turbine_installed

	# Rotor diameter price adjustment thresholds
	lower_rotor_diameter = 80
	upper_rotor_diameter = 100
	before_ceiling_lower_price = 74
	before_ceiling_upper_price = 72
	
	# Calculate price before reaching the ceiling
	before_ceiling_price = before_ceiling_lower_price + ((before_ceiling_upper_price - before_ceiling_lower_price) / (upper_rotor_diameter - lower_rotor_diameter)) * (rotor_diameter - lower_rotor_diameter)
	
	# Fixed price after exceeding the ceiling
	after_ceiling_price = 40

	# Determine production above the annual limit
	production_above_ceiling = np.maximum(production_under_contract_cumul-annual_production_ceiling,0)

	# Calculate contract price based on whether production is above or below the ceiling
	contract_E17_price = np.where(production_under_contract > 0, (production_above_ceiling * after_ceiling_price + (production_under_contract - production_above_ceiling) * before_ceiling_price) / production_under_contract, 0)
	
	return contract_E17_price


def calc_contract_E16_price(capacity_factor, days_series, time_series,flags):

	avg_equiv_operating_hours_per_year_lower = 2400
	avg_equiv_operating_hours_per_year_mid = 2800
	avg_equiv_operating_hours_per_year_upper = 3600

	TDCC_index_factor = 0.9875

	price_lower = 82
	price_mid = 68
	price_upper = 28

	equiv_operating_hours = sum(capacity_factor*days_series['contracted']*24)/sum(time_series['pct_in_contract_period'])
	
	contract_E16_price = interpolate_E16(equiv_operating_hours)*flags['contract']

	return contract_E16_price

def interpolate_E16(x):

	points = np.array([[2400, 80.98], [2800, 67.15], [3600, 27.65]])
	# If x is below the lowest x value in the points, return the corresponding y value
	if x <= points[0][0]:
		return points[0][1]
	# If x is above the highest x value in the points, return the corresponding y value
	elif x >= points[-1][0]:
		return points[-1][1]
	# Otherwise, interpolate between the appropriate points
	else:
		for i in range(len(points) - 1):
			if points[i][0] <= x <= points[i + 1][0]:
				x1, y1 = points[i]
				x2, y2 = points[i + 1]
				# Linear interpolation formula
				y = y1 + (y2 - y1) * (x - x1) / (x2 - x1)
				return y

"""
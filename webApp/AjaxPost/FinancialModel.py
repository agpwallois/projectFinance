import datetime
from dateutil.relativedelta import relativedelta
import calendar
import math
import pandas as pd
import numpy as np

class FinancialModel: 

	def __init__(self, request):
		self.periodicity = request.POST['periodicity']
		
		self.construction_start = datetime.datetime.strptime(request.POST['start_construction'], "%Y-%m-%d").date()
		self.construction_end = datetime.datetime.strptime(request.POST['end_construction'], "%Y-%m-%d").date()
		self.COD = self.construction_end + datetime.timedelta(days=1)

		self.operating_life = int(request.POST['operating_life'])
		self.end_of_operations = self.construction_end + relativedelta(years=self.operating_life)
		self.liquidation = int(request.POST['liquidation'])
		self.liquidation_date = self.end_of_operations + relativedelta(months=self.liquidation)
		
		self.debt_tenor = float(request.POST['debt_tenor'])
		self.debt_maturity_date = self.construction_start + relativedelta(months=+int(self.debt_tenor*12)-1)
		self.debt_maturity = self.debt_maturity_date.replace(day = calendar.monthrange(self.debt_maturity_date.year, self.debt_maturity_date.month)[1])

		self.periods = {
			'contract': {'start': request.POST['start_contract'], 'end': request.POST['end_contract']},
			'contract_indexation': {'start': request.POST['contract_indexation_start_date'], 'end': request.POST['end_contract']},
			'merchant_indexation': {'start': request.POST['price_elec_indexation_start_date'], 'end': self.end_of_operations},
			'lease_indexation': {'start': request.POST['lease_indexation_start_date'], 'end': self.end_of_operations},
			'opex_indexation': {'start': request.POST['opex_indexation_start_date'], 'end': self.end_of_operations},
			'debt_interest_construction': {'start': request.POST['start_construction'], 'end': request.POST['end_construction']},
			'debt_interest_operations': {'start': self.COD, 'end': self.debt_maturity_date},
			'operations': {'start': self.COD, 'end': self.end_of_operations},
		}

		self.seasonality = []
		for i in range(1, 13):
			self.seasonality.append(float(request.POST[f'seasonality_m{i}']))

		self.construction_costs = []
		delta = relativedelta(self.construction_end, self.construction_start)
		months = delta.years * 12 + delta.months + 1
		for i in range(1, months+1):
			self.construction_costs.append(float(request.POST[f'costs_m{i}']))



		self.price_elec_low = create_elec_price_dict(request, 'price_elec_low_y', self.construction_end, self.liquidation_date)
		self.price_elec_med = create_elec_price_dict(request, 'price_elec_med_y', self.construction_end, self.liquidation_date)
		self.price_elec_high = create_elec_price_dict(request, 'price_elec_high_y', self.construction_end, self.liquidation_date)



		
		
		self.dev_tax_commune = float(request.POST['dev_tax_commune_tax'])/100
		self.dev_tax_department = float(request.POST['dev_tax_department_tax'])/100


		self.P90 = float(request.POST['p90_10y'])/1000
		self.P75 = float(request.POST['p75'])/1000
		self.P50 = float(request.POST['p50'])/1000

		self.contract = request.POST['contract']

		self.index_rate_merchant = float(request.POST['price_elec_indexation']) / 100
		self.index_rate_contract = float(request.POST['contract_indexation']) / 100
		self.index_rate_opex = float(request.POST['opex_indexation']) / 100
		self.index_rate_lease = float(request.POST['lease_indexation']) / 100


		self.tfpb_rate = (float(request.POST['tfpb_commune_tax'])+float(request.POST['tfpb_department_tax'])+float(request.POST['tfpb_region_tax'])+float(request.POST['tfpb_additional_tax']))/100
		self.cfe_rate = (float(request.POST['cfe_commune_tax'])+float(request.POST['cfe_intercommunal_tax'])+float(request.POST['cfe_specific_eqp_tax'])+float(request.POST['cfe_localCCI_tax']))/100
		self.cfe_mgt_fee = float(request.POST['cfe_mgt_fee'])/100
		self.cfe_discount_tax_base= float(request.POST['cfe_discount_tax_base'])/100

			

	def create_model_dates_series(self):
		# Create a timeline for the financial model 
		model_dates_series = {
			'model_start_dates': create_model_start_series(self.periodicity, self.construction_start, self.construction_end, self.liquidation_date),
			'model_end_dates': create_model_end_series(self.periodicity, self.construction_start, self.construction_end, self.liquidation_date),
			}
		return model_dates_series

	def create_dates_series(self, model_dates_series):
		# Create a timeline for each contract
		period_dates_series = {}
		for period_name, period_dates in self.periods.items():
			period_dates_series[period_name] = {
				'start': create_start_period_series(model_dates_series['model_start_dates'], period_dates['start'], period_dates['end']),
				'end': create_end_period_series(model_dates_series['model_end_dates'], period_dates['start'], period_dates['end']),
			}
		return period_dates_series

	def create_all_dates_series(self):
		model_dates_series = self.create_model_dates_series()
		period_dates_series = self.create_dates_series(model_dates_series)

		dates_series = {}

		dates_series['model_start_dates'] = [pd.to_datetime(date) for date in model_dates_series['model_start_dates']]
		dates_series['model_end_dates'] = [pd.to_datetime(date) for date in model_dates_series['model_end_dates']]

		for period_name, period_dates in period_dates_series.items():
			dates_series[f'{period_name}_start_dates'] = [pd.to_datetime(date) for date in period_dates['start']]
			dates_series[f'{period_name}_end_dates'] = [pd.to_datetime(date) for date in period_dates['end']]

		return dates_series

	def create_flags(self, dates):
		flag = Flag(dates['model_start_dates'], dates['model_end_dates'])
		flag_dict = {
			'construction_start': (self.construction_start, self.construction_start),
			'construction_end': (self.construction_end, self.construction_end),
			'construction': (self.construction_start, self.construction_end),
			'operations': (self.COD, self.end_of_operations),
			'contract': (self.periods['contract']['start'], self.periods['contract']['end']),
			'operations_end': (self.end_of_operations, self.end_of_operations),
			'liquidation': (self.end_of_operations + datetime.timedelta(days=1), self.liquidation_date),
			'liquidation_end': (self.liquidation_date, self.liquidation_date),
			'debt_amo': (self.COD, self.debt_maturity),
			'contract_index_period': (self.periods['contract_indexation']['start'], self.periods['contract']['end']),
			'merchant_index_period': (self.periods['merchant_indexation']['start'], self.end_of_operations),
			'lease_index_period': (self.periods['lease_indexation']['start'], self.end_of_operations),
			'opex_index_period': (self.periods['opex_indexation']['start'], self.end_of_operations),
			}
		
		flags = {}
		for name, (start, end) in flag_dict.items():
			flags[name] = flag.create_flag(start, end).tolist()

		flags['start_year'] = flag.create_flag_start_year().tolist()
		return flags
	
	@staticmethod
	def create_days_series(dates_series, flags):
		days_dict = create_days_series(dates_series, flags)
		return days_dict

	@staticmethod
	def create_time_series(dates_series,days_series,flags):
		time_series = create_time_series(dates_series,days_series,flags)
		return time_series		

	def create_seasonality_series(self,dates_series):
		seasonality = create_season_series(self.seasonality,dates_series)
		return seasonality

	def create_capacity_series(self,flags,time_series):
		capacity = self.calc_capacity(pd.Series(flags['operations']),pd.Series(time_series['years_from_COD_avg']))
		return capacity

	def create_construction_costs_series(self,flags):
		construction_costs_series = np.hstack([self.construction_costs,np.zeros(pd.Series(flags['operations']).size - len(self.construction_costs))]) * pd.Series(flags['construction'])
		return construction_costs_series

	def calc_construction_costs_sum(self):
		construction_costs_sum = np.sum(self.construction_costs)
		return construction_costs_sum

	def calc_construction_costs_cum(self, construction_costs_series):
		construction_costs_cum = construction_costs_series.cumsum()
		return construction_costs_cum

	def calc_development_tax(self, flags):
		development_tax_rate = self.dev_tax_commune + self.dev_tax_department
		development_tax = self.comp_development_tax(development_tax_rate,pd.Series(flags['construction_start']))
		return development_tax

	def calc_archeological_tax(self, flags):
		if hasattr(self, 'archeological_tax'):
			archeological_tax = self.comp_archeological_tax(self.archeological_tax,pd.Series(flags['construction_start']))
		else: 
			return None	
		return archeological_tax

	def calc_production(self, seasonality,capacity,time_series,flags):
		production = self.P90*pd.Series(seasonality)*capacity['after_degradation']
		production_under_contract = production * pd.Series(time_series['pct_in_contract_period']) * pd.Series(time_series['pct_in_operations_period'])
		production_in_year_under_contract_cumul = calc_production_cumul(production_under_contract,pd.Series(flags['start_year']))

		production_series = {
		'production': production.tolist(),
		'production_under_contract': production_under_contract.tolist(),
		'production_in_year_under_contract_cumul': production_in_year_under_contract_cumul.tolist(),
		}

		return production_series


	def calc_capacity_factor(self,days,production):
		capacity_factor = np.where(pd.Series(days)>0,pd.Series(production)/((self.installed_capacity*pd.Series(days)*24)/1000),0)
		capacity_factor = {
		'capacity_factor': capacity_factor.tolist(),
		}

		return capacity_factor

	def calc_contract_price(self):
		contract_price = self.comp_contract_price()
		
		return contract_price




	def create_indexation_series(self, time_series):

		# Create a dictionary to store the mapping between the index names and their corresponding columns
		index_columns = {
			'merchant': 'years_from_base_date_merchant_index',
			'contract': 'years_from_base_date_contract_index',
			'opex': 'years_from_base_date_opex_index',
			'lease': 'years_from_base_date_lease_index'
		}

		indexation_series = {}

		# Iterate over the dictionary to create the indexation vectors
		for indice_name, column_name in index_columns.items():

			# Create the indexation vector for the current index
			indice_indice = array_index(getattr(self, f'index_rate_{indice_name}'), pd.Series(time_series[column_name]))

			# Add the indexation vector to the dictionary
			indexation_series[indice_name] = indice_indice.tolist()

		return indexation_series

	def create_merchant_price_series(self, time_series, indexation_series):
		merchant_price_series_real = array_elec_prices(time_series['series_end_period_year'], pd.Series(self.price_elec_low))
		merchant_price_series_nom = merchant_price_series_real * pd.Series(indexation_series['merchant'])
		
		merchant_price_series = {
			'real': merchant_price_series_real,
			'nom': merchant_price_series_nom.tolist(),
		}
		return merchant_price_series

	def create_contract_price_series(self, time_series, indexation_series, flags):
		contract_price_series_real = self.calc_contract_price() * pd.Series(flags['contract'])
		contract_price_series_nom = contract_price_series_real * pd.Series(indexation_series['merchant'])
		
		contract_price_series = {
			'real': contract_price_series_real.tolist(),
			'nom': contract_price_series_nom.tolist(),
		}
		return contract_price_series




	def build_financial_model(self):
		dates_series = self.create_all_dates_series()
		flags = self.create_flags(dates_series)
		days_series = self.create_days_series(dates_series,flags)
		time_series = self.create_time_series(dates_series,days_series,flags)
		seasonality = self.create_seasonality_series(dates_series)
		capacity = self.create_capacity_series(flags,time_series)
		construction_costs_series = self.create_construction_costs_series(flags)
		construction_costs_sum = self.calc_construction_costs_sum()
		construction_costs_cum = self.calc_construction_costs_cum(construction_costs_series)
		development_tax = self.calc_development_tax(flags)
		archeological_tax = self.calc_archeological_tax(flags)
		production = self.calc_production(seasonality,capacity,time_series,flags)
		capacity_factor = self.calc_capacity_factor(days_series['operations'],production['production'])
		
		indexation_series = self.create_indexation_series(time_series)
		merchant_price_series = self.create_merchant_price_series(time_series, indexation_series)
		contract_price_series = self.create_contract_price_series(time_series, indexation_series, flags)



		return dates_series, flags, days_series, time_series, seasonality, capacity, development_tax, archeological_tax, production, capacity_factor, indexation_series, merchant_price_series, contract_price_series 




	def to_dict(self):
		return self.build_financial_model()



def array_index(indexation_rate,indexation_year):
	arr_indexation = (1+indexation_rate)**indexation_year
	return arr_indexation



def array_elec_prices(series_end_period_year,dic_price_elec):
	electricity_prices = []
	
	for row in series_end_period_year:
		if str(row) in dic_price_elec.keys():
			electricity_prices.append(dic_price_elec[str(row)])
		else:
			electricity_prices.append(0)
	
	return electricity_prices



def calc_production_cumul(production, start_calendar_year):

	cumulative_production = np.zeros_like(production)
	for i in range(len(production)):
		if start_calendar_year[i] == 1:
			cumulative_production[i] = production[i]
		else:
			cumulative_production[i] = cumulative_production[i - 1] + production[i]

	return cumulative_production




def calc_production(request,seasonality,capacity_after_degradation, dict_scenario, key):

	seasonality=np.array(seasonality,dtype=float)

	P90 = float(request.POST['p90_10y'])/1000*seasonality*capacity_after_degradation
	P75 = float(request.POST['p75'])/1000*seasonality*capacity_after_degradation
	P50 = float(request.POST['p50'])/1000*seasonality*capacity_after_degradation

	if dict_scenario[key]["prod"] == 1:
		production = P90
	elif dict_scenario[key]["prod"] == 2:
		production = P75
	else:
		production = P50

	return production








class Flag:
	def __init__(self, model_start_dates, model_end_dates):
		self.model_start_dates = pd.to_datetime(model_start_dates)
		self.model_end_dates = pd.to_datetime(model_end_dates)

	def create_flag(self, start_date, end_date):
		self.flag = ((self.model_end_dates >= pd.to_datetime(start_date)) * (self.model_start_dates <= pd.to_datetime(end_date))).astype(int)
		return self.flag

	def create_flag_start_year(self):
		datetime_index = pd.DatetimeIndex(self.model_start_dates)
		self.flag_start_year = (datetime_index.month == 1)*1
		return self.flag_start_year

class Days:
	def __init__(self, flag):
		self.flag = flag
	
	def create_number_days_series(self, end_date_series, start_date_series):
		number_of_days = ((pd.Series(end_date_series) - pd.Series(start_date_series)).dt.days + 1) * self.flag
		return number_of_days





def get_quarters(date_list):
	date_series = pd.Series(date_list)
	quarters = pd.to_datetime(date_series, format='%Y-%m-%d').dt.quarter
	return quarters.tolist()




def create_start_period_series(series_start_period,start,end):
	start_period_series = array_time(series_start_period,start,end)
	return start_period_series


def create_end_period_series(series_end_period,start,end):
	end_period_series = array_time(series_end_period,start,end)
	return end_period_series


def array_time(timeline,start,end):	
	timeline_result = timeline.clip(lower=pd.Timestamp(start),upper=pd.Timestamp(end))
	return timeline_result


def first_day_month(date):
	first_day_month = date.replace(day=1)
	return first_day_month


def create_model_start_series(periodicity,construction_start,construction_end,liquidation_date):

	"""test = int(periodicity/3)"""
	test = math.floor(int(periodicity) / 3)
	freq_period_start = str(periodicity)+"MS"

	first_day_month_construction_start = first_day_month(construction_start)
	last_day_construction_end = last_day_month(construction_end)
	first_operations_end_date = last_day_construction_end + datetime.timedelta(days=1) + relativedelta(months=+test) + pd.tseries.offsets.QuarterEnd()*test


	first_operations_date = last_day_construction_end + datetime.timedelta(days=1) 
	first_operations_date = pd.Timestamp(first_operations_date)
	first_operations_date = pd.Series(first_operations_date)
	second_operations_date = first_operations_end_date + datetime.timedelta(days=1)
	last_day_liquidation_end = last_day_month(liquidation_date)
	start_period_construction = pd.Series(pd.date_range(first_day_month_construction_start,last_day_construction_end, freq='MS'))
	start_period_operations = pd.Series(pd.date_range(second_operations_date, last_day_liquidation_end,freq=freq_period_start))
	series_start_period = pd.concat([start_period_construction,first_operations_date,start_period_operations], ignore_index=True)
		
	return series_start_period


def create_model_end_series(periodicity,construction_start,construction_end,liquidation_date):

	"""test = int(periodicity/3)"""
	test = math.floor(int(periodicity) / 3)

	freq_period_end = str(periodicity)+"M"

	first_day_month_construction_start = first_day_month(construction_start)
	last_day_construction_end = last_day_month(construction_end)
	first_operations_end_date = last_day_construction_end + datetime.timedelta(days=1) + relativedelta(months=+test) + pd.tseries.offsets.QuarterEnd()*test

	last_day_end_liquidation_plus_freq = first_day_next_month(liquidation_date,periodicity)	
	end_period_operations = pd.Series(pd.date_range(first_operations_end_date, last_day_end_liquidation_plus_freq,freq=freq_period_end))
	end_period_construction = pd.Series(pd.date_range(first_day_month_construction_start,last_day_construction_end, freq='M'))
	series_end_period = pd.concat([end_period_construction,end_period_operations], ignore_index=True)
	
	return series_end_period





def calc_years_from_base_dates(days_series, days_in_year):
	
	keys = ['contract_index', 'merchant_index', 'opex_index', 'lease_index']
	
	years_from_base_dates = {}
	for key in keys:
		years = (days_series[key] / days_in_year).cumsum()
		years_from_base_dates[key] = years

	return years_from_base_dates



def last_day_month(period):	
	last_day_month = period.replace(day = calendar.monthrange(period.year, period.month)[1])
	return last_day_month



def first_day_next_month(date,periodicity):
	first_day_next_month = date.replace(day=1) + relativedelta(months=int(periodicity)) + datetime.timedelta(days=-1)
	return first_day_next_month



def create_season_series(seasonality,dates_series):
	
	data = {'start':dates_series['model_start_dates'],
			'end':dates_series['model_end_dates']}

	df = pd.DataFrame(data)

	df_seasonality_result = pd.DataFrame(columns=dates_series['model_end_dates'])

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




def comp_contract_priceALT(contract_type, wind_turbine_installed, rotor_diameter,production_under_contract, production_under_contract_cumul,capacity_factor, days_series,time_series,flags):
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




def create_elec_price_dict(request, prefix, construction_end, liquidation_date):
	
	construction_end_year = construction_end.year
	liquidation_date_year = liquidation_date.year

	years = [str(year) for year in range(construction_end_year, liquidation_date_year+1)]

	dic_price_elec = {}

	for i, year in enumerate(years):
		key = f'{prefix}{i+1}'
		value = float(request.POST[key])
		dic_price_elec[year] = value

	return dic_price_elec



def create_time_series(dates_series,days_series,flags):
	
	days_in_year = pd.Series(dates_series['model_end_dates']).dt.is_leap_year * 366 + (1 - pd.Series(dates_series['model_end_dates']).dt.is_leap_year) * 365
	years_in_period = days_series['model'] / days_in_year
	years_during_operations = years_in_period * flags['operations']

	quarters = get_quarters(dates_series['model_end_dates'])

	# Calculating years from COD to end of operations
	years_from_COD_eop = years_during_operations.cumsum()
	years_from_COD_bop = years_from_COD_eop - years_during_operations
	years_from_COD_avg = (years_from_COD_eop + years_from_COD_bop) / 2

	# Extracting the year part from the end period series
	series_end_period_year = pd.Series(dates_series['model_end_dates']).dt.year

	pct_in_operations_period = pd.Series(days_series['operations']) / pd.Series(days_series['model'])

	# Calculating the percentage of time in the contracted period
	pct_in_contract_period = np.where(pd.Series(days_series['operations']) > 0, pd.Series(days_series['contract']) / pd.Series(days_series['operations']),0)  # Default value when days_series['days_operations'] is zero

	years_from_base_dates = calc_years_from_base_dates(days_series, days_in_year)

	time_series = {
		'days_in_year': days_in_year.tolist(),
		'years_in_period': years_in_period.tolist(),
		'years_during_operations': years_during_operations.tolist(),
		'years_from_COD_eop': years_from_COD_eop.tolist(),
		'years_from_COD_bop': years_from_COD_bop.tolist(),
		'years_from_COD_avg': years_from_COD_avg.tolist(),
		'series_end_period_year': series_end_period_year.tolist(),
		'pct_in_contract_period': pct_in_contract_period.tolist(),
		'pct_in_operations_period': pct_in_operations_period.tolist(),
		'quarters': quarters,
		'years_from_base_date_contract_index': years_from_base_dates['contract_index'].tolist(),
		'years_from_base_date_merchant_index': years_from_base_dates['merchant_index'].tolist(),
		'years_from_base_date_opex_index': years_from_base_dates['opex_index'].tolist(),
		'years_from_base_date_lease_index': years_from_base_dates['lease_index'].tolist(),
	}
	return time_series		




def create_days_series(dates_series, flags):

	days_model = ((pd.Series(dates_series['model_end_dates']) - pd.Series(dates_series['model_start_dates'])).dt.days + 1) * 1

	days_series_dict = {
	'contract': {'flag': flags['contract'], 'start_dates': dates_series['contract_start_dates'], 'end_dates': dates_series['contract_end_dates']},
	'contract_index': {'flag': flags['contract_index_period'], 'start_dates': dates_series['contract_indexation_start_dates'], 'end_dates': dates_series['contract_indexation_end_dates']},
	'merchant_index': {'flag': flags['merchant_index_period'], 'start_dates': dates_series['merchant_indexation_start_dates'], 'end_dates': dates_series['merchant_indexation_end_dates']},
	'opex_index': {'flag': flags['opex_index_period'], 'start_dates': dates_series['opex_indexation_start_dates'], 'end_dates': dates_series['opex_indexation_end_dates']},
	'debt_interest_construction': {'flag': flags['construction'], 'start_dates': dates_series['debt_interest_construction_start_dates'], 'end_dates': dates_series['debt_interest_construction_end_dates']},
	'debt_interest_operations': {'flag': flags['debt_amo'], 'start_dates': dates_series['debt_interest_operations_start_dates'], 'end_dates': dates_series['debt_interest_operations_end_dates']},
	'operations': {'flag': flags['operations'], 'start_dates': dates_series['operations_start_dates'], 'end_dates': dates_series['operations_end_dates']},
	'lease_index': {'flag': flags['lease_index_period'], 'start_dates': dates_series['lease_indexation_start_dates'], 'end_dates': dates_series['lease_indexation_end_dates']},
	}

	days_dict = {}

	days_dict['model'] = days_model.tolist()

	for period_name, period_data in days_series_dict.items():
		days_series = Days(period_data['flag']).create_number_days_series(period_data['end_dates'], period_data['start_dates'])
		days_dict[period_name] = days_series.tolist()

	return days_dict


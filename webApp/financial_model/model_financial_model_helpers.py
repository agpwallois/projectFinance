import numpy as np
import pandas as pd
from decimal import Decimal
import math
import calendar
from datetime import date
import datetime
from dateutil.relativedelta import relativedelta


def convert_to_list(data):
	if isinstance(data, pd.Series):
		return data.tolist()
	elif isinstance(data, pd.Timestamp):
		return data.strftime('%d/%m/%Y')
	elif isinstance(data, Decimal):
		return float(data)
	elif isinstance(data, np.ndarray):
		return data.tolist()
	elif isinstance(data, np.integer):
		return int(data)
	elif isinstance(data, np.floating):
		return float(data)
	elif isinstance(data, np.bool_):
		return bool(data)
	elif isinstance(data, dict):
		return {key: convert_to_list(value) for key, value in data.items()}
	elif isinstance(data, list):
		return [convert_to_list(item) for item in data]
	else:
		return data

def calculate_tenor(final_repayment_date, construction_start):
	time_difference = final_repayment_date-construction_start
	tenor = round(time_difference.days / 365.25, 1)
	return tenor

def divide_with_condition(numerator, denominator):
	# Divide numerator by denominator, set 0 where denominator is less than or equal to 0.01
	return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0.01)

def find_last_payment_date(series_end_period, boolean_array):
	boolean_array = boolean_array > 0.1
	new_array = [date if boolean else 0 for boolean, date in zip(boolean_array, series_end_period)]
	non_zero_dates = [date for date in new_array if date != 0]
	max_date = max(non_zero_dates)
	return max_date

def date_converter(date_str):
	return date_str.strftime("%d/%m/%Y")









def create_IRR_curve(equity_cash_flows,series_end_period):

	irr_values = []

	# Iterate through each period and calculate the IRR up to that period
	for i in range(1, len(equity_cash_flows)+1):
		subset_cash_flows = equity_cash_flows.iloc[:i]
		subset_dates = pd.to_datetime(pd.Series(series_end_period).iloc[:i], dayfirst=True).dt.date

		try:
			irr = xirr(subset_dates, subset_cash_flows)*100
		except:
			irr = 0.0

		irr_values.append(max(irr,0,0))

	return irr_values 
			 

def find_payback_date(series_end_period,equity_cash_flows_cumul):

	# Find the indices where cumulative_equity is greater than or equal to zero
	valid_indices = np.where(equity_cash_flows_cumul >= 0)[0]

	if len(valid_indices) > 0:
		# Find the minimum date_series_end_period value at the valid indices
		payback_date_index = valid_indices[np.argmin(series_end_period[valid_indices])]
		payback_date = series_end_period[payback_date_index]
	else:
		payback_date = None
	"""payback_date = df.loc[df['Cumulative Equity for payback'] >= 0, 'Date Period end'].min()"""
	return payback_date

def calculate_ratio(avg_interest_rate, CFADS, senior_debt_balance_eop, dates_series):
	
	avg_i = avg_interest_rate[avg_interest_rate > 0].mean()

	discounted_CFADS = compute_npv(CFADS, avg_i, dates_series)

	ratio = divide_with_condition(discounted_CFADS, senior_debt_balance_eop)

	return ratio

def compute_npv(cfads, discount_rate, dates_series):
	npvs = []

	dates_series = pd.Series(dates_series)
	dates_series = pd.to_datetime(dates_series, dayfirst=True)

	series_end_period = dates_series.dt.date
	

	for i in range(len(cfads)):
		npv = 0
		if cfads[i] > 1:
			for j in range(i, len(cfads)):
				end_date = dates_series[j]
				start_date = dates_series[i-1]
				time_delta = (end_date - start_date).days/365.25
				npv += cfads[j] / ((1+discount_rate) ** (time_delta))

			npvs.append(npv)
		else: 
			npvs.append(0)

	return npvs

def determine_debt_constraint(debt_amount,debt_amount_gearing):
	if debt_amount > debt_amount_gearing:
		constraint = "Gearing"
	else: 
		constraint = "DSCR"
	return constraint

	
def calc_dsra_target(dsra, periodicity, DS_effective):

	look_forward=int(dsra/periodicity)	

	looking_forward_debt_service = []
	for i in range(len(DS_effective)):
		forward_debt_service = sum(DS_effective[i+1:min(i+1+look_forward, len(DS_effective))])
		looking_forward_debt_service.append(forward_debt_service)

	return looking_forward_debt_service	
	
def calc_dsra_funding(dsra_target):
	
	positive_sum = 0
	count = 0
	for num in dsra_target:
		if num > 0:
			positive_sum += num
			count += 1
		if count == 1:
			break
	return positive_sum



def array_elec_prices(series_end_period_year, dic_price_elec):
	electricity_prices = []
	
	for row in series_end_period_year:
		if str(row) in dic_price_elec.keys():
			electricity_prices.append(dic_price_elec[str(row)])
		else:
			electricity_prices.append(0)
	
	return electricity_prices





def create_elec_price_dict(self, prefix, construction_end, liquidation_date):
	
	construction_end_year = construction_end.year
	liquidation_date_year = liquidation_date.year

	years = [str(year) for year in range(construction_end_year, liquidation_date_year+1)]

	dic_price_elec = {}

	for i, year in enumerate(years):
		key = f'{prefix}{i+1}'
		value = float(getattr(self.project, key))
		dic_price_elec[year] = value

	return dic_price_elec



def create_elec_price_dict_keys(dic_price_elec):
	dic_price_elec_keys = np.array(list(dic_price_elec.keys()))
	return dic_price_elec_keys



# Helper function to format date
def format_date(date_input):

	return date_input.dt.strftime('%d/%m/%Y')



def calc_production_cumul(production, start_calendar_year):

	cumulative_production = np.zeros_like(production)
	for i in range(len(production)):
		if start_calendar_year[i] == 1:
			cumulative_production[i] = production[i]
		else:
			cumulative_production[i] = cumulative_production[i - 1] + production[i]

	return cumulative_production




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




def calc_years_from_base_dates(days_series, days_in_year):
	
	keys = ['contract_indexation', 'merchant_indexation', 'opex_indexation', 'lease_indexation']
	
	years_from_base_dates = {}
	for key in keys:
		years = (days_series[key] / days_in_year).cumsum()
		years_from_base_dates[key] = years

	return years_from_base_dates



def get_quarters(date_list):
	date_series = pd.Series(date_list)
	quarters = pd.to_datetime(date_series, format='%Y-%m-%d').dt.quarter
	return quarters


def start_period_series(series_start_period,start,end):
	start_period_series = array_time(series_start_period,start,end)
	return start_period_series


def end_period_series(series_end_period,start,end):
	end_period_series = array_time(series_end_period,start,end)
	return end_period_series


def array_time(timeline_list, start_date, end_date):    
	# Convert the timeline list to a pandas Series of Timestamps with specified date format
	timeline_series = pd.to_datetime(pd.Series(timeline_list), format='%d/%m/%Y', dayfirst=True)

	# Use the clip method to restrict the dates to the specified range
	clipped_timeline = timeline_series.clip(lower=pd.Timestamp(start_date), upper=pd.Timestamp(end_date))


	return clipped_timeline


def model_start_series(periodicity,construction_start,construction_end,liquidation_date):

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


def model_end_series(periodicity,construction_start,construction_end,liquidation_date):

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



def first_day_next_month(date,periodicity):
	first_day_next_month = date.replace(day=1) + relativedelta(months=int(periodicity)) + datetime.timedelta(days=-1)
	return first_day_next_month



def first_day_month(date):
	first_day_month = date.replace(day=1)
	return first_day_month


def last_day_month(period):	
	last_day_month = period.replace(day = calendar.monthrange(period.year, period.month)[1])
	return last_day_month

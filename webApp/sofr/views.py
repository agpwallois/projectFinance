from django.shortcuts import render

import os
from django.contrib.staticfiles import finders

import pandas as pd
import numpy as np
from scipy.optimize import minimize

import requests
from django.http import JsonResponse
from fredapi import Fred
import json
import math
import utils
import pandas as pd
from datetime import date


import QuantLib as ql


def get_historical_sofr(request):

	fred = Fred(api_key='91fc443fe45eb58cf4190b7abc549109')
	data = fred.get_series('SOFR')

	data_ffill = data.fillna(method='ffill')
	series_dict = {str(date): value for date, value in data_ffill.items()}
	
	return series_dict



# Create your views here.
def create_SOFRForwardCurve(request):




	# Deposit rates
	depo_maturities = [ql.Period(6,ql.Months), ql.Period(12, ql.Months)]
	depo_rates = [5.25, 5.5]

	# Bond rates
	bond_maturities = [ql.Period(6*i, ql.Months) for i in range(3,21)]
	bond_rates = [5.34, 4.83, 4.54, 4.37, 4.27, 4.21, 4.18, 4.15, 4.13,
				  4.13, 4.12, 4.12, 4.09, 4.0, 3.9, 3.9, 3.9, 3.9]



	# some constants and conventions
	# here we just assume for the sake of example
	# that some of the constants are the same for
	# depo rates and bond rates

	calc_date = ql.Date(15, 1, 2015)
	ql.Settings.instance().evaluationDate = calc_date

	calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
	bussiness_convention = ql.Unadjusted
	day_count = ql.Actual360()
	end_of_month = True
	settlement_days = 0
	face_amount = 100
	coupon_frequency = ql.Period(ql.Semiannual)
	settlement_days = 0

	# create deposit rate helpers from depo_rates
	depo_helpers = [ql.DepositRateHelper(ql.QuoteHandle(ql.SimpleQuote(r/100.0)),
										 m,
										 settlement_days,
										 calendar,
										 bussiness_convention,
										 end_of_month,
										 day_count )
					for r, m in zip(depo_rates, depo_maturities)]


	# create fixed rate bond helpers from fixed rate bonds
	bond_helpers = []
	for r, m in zip(bond_rates, bond_maturities):
		termination_date = calc_date + m
		schedule = ql.Schedule(calc_date,
					   termination_date,
					   coupon_frequency,
					   calendar,
					   bussiness_convention,
					   bussiness_convention,
					   ql.DateGeneration.Backward,
					   end_of_month)

		helper = ql.FixedRateBondHelper(ql.QuoteHandle(ql.SimpleQuote(face_amount)),
											settlement_days,
											face_amount,
											schedule,
											[r/100.0],
											day_count,
											bussiness_convention,
											)
		bond_helpers.append(helper)


	rate_helpers = depo_helpers + bond_helpers
	yieldcurve = ql.PiecewiseLogCubicDiscount(calc_date,
								 rate_helpers,
								 day_count)

	# get spot rates
	spots = []
	tenors = []
	for d in yieldcurve.dates():
		yrs = day_count.yearFraction(calc_date, d)
		compounding = ql.Compounded
		freq = ql.Semiannual
		zero_rate = yieldcurve.zeroRate(yrs, compounding, freq)
		tenors.append(yrs)
		eq_rate = zero_rate.equivalentRate(day_count,
										   compounding,
										   freq,
										   calc_date,
										   d).rate()
		spots.append(100*eq_rate)

	"""today = ql.Date(11, ql.December, 2012)
	ql.Settings.instance().evaluationDate = today

	helpers = [
		ql.DepositRateHelper(ql.QuoteHandle(ql.SimpleQuote(rate/100)),ql.Period(1,ql.Days),fixingDays,ql.TARGET(),ql.Following,False,ql.Actual360())
		for rate, fixingDays in [(0.04, 0), (0.04, 1), (0.04, 2)]
		]

	eonia = ql.Eonia()

	helpers += [
		ql.OISRateHelper(2, ql.Period(*tenor),ql.QuoteHandle(ql.SimpleQuote(rate/100)), eonia)
		for rate, tenor in [(0.070, (1,ql.Weeks)), (0.069, (2,ql.Weeks)),(0.078, (3,ql.Weeks)), (0.074, (1,ql.Months))]
		]

	helpers += [
		ql.DatedOISRateHelper(start_date, end_date,ql.QuoteHandle(ql.SimpleQuote(rate/100)), eonia)
		for rate, start_date, end_date in [
			( 0.046, ql.Date(16,ql.January,2013), ql.Date(13,ql.February,2013)),
			( 0.016, ql.Date(13,ql.February,2013), ql.Date(13,ql.March,2013)),
			(-0.007, ql.Date(13,ql.March,2013), ql.Date(10,ql.April,2013)),
			(-0.013, ql.Date(10,ql.April,2013), ql.Date(8,ql.May,2013)),
			(-0.014, ql.Date(8,ql.May,2013), ql.Date(12,ql.June,2013))]
		]

	helpers += [
		ql.OISRateHelper(2, ql.Period(*tenor),ql.QuoteHandle(ql.SimpleQuote(rate/100)), eonia)
		for rate, tenor in [(0.002, (15,ql.Months)), (0.008, (18,ql.Months)),
							(0.021, (21,ql.Months)), (0.036, (2,ql.Years)),
							(0.127, (3,ql.Years)), (0.274, (4,ql.Years)),
							(0.456, (5,ql.Years)), (0.647, (6,ql.Years)),
							(0.827, (7,ql.Years)), (0.996, (8,ql.Years)),
							(1.147, (9,ql.Years)), (1.280, (10,ql.Years)),
							(1.404, (11,ql.Years)), (1.516, (12,ql.Years)),
							(1.764, (15,ql.Years)), (1.939, (20,ql.Years)),
							(2.003, (25,ql.Years)), (2.038, (30,ql.Years))]
			]


	eonia_curve = ql.PiecewiseLogCubicDiscount(0, ql.TARGET(),helpers, ql.Actual365Fixed())
	eonia_curve.enableExtrapolation()

	today = eonia_curve.referenceDate()
	end = today + ql.Period(2,ql.Years)
	dates = [ ql.Date(serial) for serial in range(today.serialNumber(),end.serialNumber()+1) ]
	rates_c = [ eonia_curve.forwardRate(d, ql.TARGET().advance(d,1,ql.Days),ql.Actual360(), ql.Simple).rate() for d in dates ]


	helpers = [
		ql.DepositRateHelper(
			ql.QuoteHandle(ql.SimpleQuote(0.312 / 100)),
			ql.Period(6, ql.Months),
			3,
			ql.TARGET(),
			ql.Following,
			False,
			ql.Actual360(),
		)
	]

	euribor6m = ql.Euribor6M()


	helpers += [
		ql.FraRateHelper(
			ql.QuoteHandle(ql.SimpleQuote(rate / 100)), start, euribor6m
		)
		for rate, start in [
			(5.355, 1),
			(5.300, 2),
			(5.100, 3),
			(5.000, 4),
			(4.900, 5),
			(4.800, 6),
			(4.700, 7),
			(4.600, 8),
			(4.500, 9),
			(4.400, 10),
			(4.300, 11),
			(4.200, 12),
			(4.100, 13),
			(4.000, 14),
			(3.900, 15),
			(3.800, 16),
			(3.700, 17),
			(3.600, 18),
		]
	]

	discount_curve = ql.YieldTermStructureHandle(eonia_curve)

	helpers += [
		ql.SwapRateHelper(
			ql.QuoteHandle(ql.SimpleQuote(rate / 100)),
			ql.Period(tenor, ql.Years),
			ql.TARGET(),
			ql.Annual,
			ql.Unadjusted,
			ql.Thirty360(ql.Thirty360.BondBasis),
			euribor6m,
			ql.QuoteHandle(),
			ql.Period(0, ql.Days),
			discount_curve,
		)
		for rate, tenor in [
			(4.152, 3),
			(3.880, 5),
			(3.783, 7),
			(3.733, 10),
			(3.731, 15),
			(3.506, 30),
		]
	]

	euribor6m_curve = ql.PiecewiseLogCubicDiscount(2, ql.TARGET(), helpers, ql.Actual365Fixed())
	euribor6m_curve.enableExtrapolation()
		
	spot = euribor6m_curve.referenceDate()
	dates = [spot + ql.Period(i, ql.Months) for i in range(0, 60 * 12 + 1)]
	rates = [
		euribor6m_curve.forwardRate(
			d, euribor6m.maturityDate(d), ql.Actual360(), ql.Simple
		).rate()
		for d in dates
	]"""


	"""calendar = ql.UnitedStates()
	business_convention = ql.Following
	day_count = ql.Actual360()
	end_of_month = False


	# Dummy data: [start date, futures rate]
	futures_data = [(ql.Date(1, 4, 2024), 98.25), 
	(ql.Date(1, 7, 2024), 98.00),]

	futures_helpers = []
	for start_date, futures_rate in futures_data:
		futures_rate_helper = ql.FuturesRateHelper(ql.QuoteHandle(ql.SimpleQuote(futures_rate)),start_date,3,calendar,business_convention,end_of_month,day_count)
		futures_helpers.append(futures_rate_helper)


	sofr_forward_curve = ql.PiecewiseLogCubicDiscount(calculation_date,futures_helpers,day_count)

	future_date = ql.Date(1, 10, 2024)
	sofr_rate = sofr_forward_curve.zeroRate(future_date, day_count, ql.Continuous).rate()"""



	# User needs to input the start date (the as of date) and end date for the SOFR curve
	"""fwd_dates = pd.bdate_range(start='04/30/2020', end='05/03/2060')
	fwd_rates = np.array([0]*len(fwd_dates))
	fwd_rates = pd.Series(fwd_rates, index=fwd_dates)
	
	# User needs to input this rate https://www.newyorkfed.org/markets/reference-rates/sofr
	fwd_rates.iloc[0] = .04 

	file_path_sr1 = finders.find('AjaxPost/1m_futures_data.csv')
	file_path_sr3 = finders.find('AjaxPost/3m_futures_data.csv')
	file_path_sr3_rzd = finders.find('AjaxPost/rzd_rates.csv')

	sr1_data = pd.read_csv(file_path_sr1, header=0, index_col=0)
	sr3_data = pd.read_csv(file_path_sr3, header=0, index_col=0)

	# https://www.cmegroup.com/markets/interest-rates/stirs/one-month-sofr.quotes.html#venue=globex
	fwd_rates = set_rates(fwd_rates, sr1_boot(99.9775, 21), '05/01/2020', '05/29/2020')

	rzd_rates = pd.read_csv(file_path_sr3_rzd, index_col=0)
	rzd_rates.index = pd.to_datetime(rzd_rates.index)

	dt_rzd = pd.Series(rzd_rates.index).diff().dt.days/360
	dt_rzd = dt_rzd[1:]
	#dt_rzd
	rzd_rates = rzd_rates[:-1]
	#rzd_rates, dt_rzd
	sr3_rzd = (np.transpose(rzd_rates.values)*dt_rzd.values+1).prod()

	btd_rates = fwd_rates[0:23]
	dt_btd = pd.Series(btd_rates.index).diff().dt.days/360
	dt_btd = dt_btd[1:]
	#dt_rzd
	btd_rates = btd_rates[:-1]
	sr3_btd = (np.transpose(btd_rates.values)*dt_btd.values+1).prod()

	quote_set = sr3_data.iloc[1:7,4]
	#print(quote_set)
	start_set = sr3_data.iloc[0:6,3]
	#print(start_set) 
	end_set = sr3_data.iloc[1:7,3]
	#print(end_set)
	last_set = sr3_data.iloc[1:7,2]

	for i in range(len(start_set)):
		quote = quote_set[i]
		start = start_set[i]
		end = end_set[i]
		last = last_set[i]
		results = minimize(sr3_min, .0004,args=(sr3_pricer, quote, start, end), method="SLSQP",options={'disp': False})
		# we will keep over-writing unknown forward rates with the ones implied from SR3 futures
		fwd_rates = set_rates(fwd_rates, results.x[0], start, last)

	# Calculations associated with the rates that have been bootstrapped earlier
	btd_y1_dates = pd.bdate_range('04/30/2020', '05/03/2021') 
	dt_btd_y1 = pd.Series(btd_y1_dates).diff().dt.days/360
	dt_btd_y1 = dt_btd_y1[1:]
	#print(dt_btd_y1)
	btd_y1_rates = fwd_rates[fwd_rates.index <= '04/30/2021']/100
	swap_btd_y1 = (np.transpose(btd_y1_rates.values)*dt_btd_y1.values+1).prod()

	btd_y2_dates = pd.bdate_range('05/03/2021', '12/15/2021')
	dt_btd_y2 = pd.Series(btd_y2_dates).diff().dt.days/360
	dt_btd_y2 = dt_btd_y2[1:]

	btd_y2_rates = fwd_rates[(fwd_rates.index <= '12/14/2021') & (fwd_rates.index > '04/30/2021')]/100
	swap_btd_y2 = (np.transpose(btd_y2_rates.values)*dt_btd_y2.values+1).prod()


	results = minimize(swap_min, .04,args=(swap_pricer, .00046, '12/15/2021', '05/03/2022', swap_btd_y1, swap_btd_y2), method="SLSQP",options={'disp': False})
	fwd_rates = set_rates(fwd_rates, 100*results.x[0], '12/15/2021', '04/29/2022')

	
	flt1 = (swap_btd_y1-1)*360/365
	df1 = 1/swap_btd_y1

	fwd_dates = pd.bdate_range('04/30/2020', '05/03/2060') 
	dt_fwd = pd.Series(fwd_dates).diff().dt.days/360
	dt_fwd = dt_fwd

	flt2 = ((np.transpose(fwd_rates.values)/100*dt_fwd.values+1).prod()/swap_btd_y1-1)*360/365
	df2 = 1/(np.transpose(fwd_rates.values)/100*dt_fwd.values+1).prod()

	flt_vec = np.array([flt1,flt2])
	df_vec = np.array([df1,df2])
	smin_all = []

	n_years = [3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 30, 40]
	delta_years = [1, 1, 1, 1, 1, 1, 1, 1, 2, 3, 5, 10, 10]
	swap_rate = [.00068, .001200, 0.001550, 0.002110, 0.002610, 0.003090, 0.003510, 0.003840, \
	0.004410, 0.004930, 0.005430, 0.005660, 0.005210]

	for i in range(1,14):

		def swap_pricer2(s, swap_rate, flt_vec, df_vec):

			#append delta-years elements and solve for s
			flt_vec = np.append(flt_vec,[((1+s/36000)**365-1)*360/365]*delta_years[i-1])
			#if delta_years[i-1]>1:
			for j in range(1,delta_years[i-1]+1):
				df_vec = np.append(df_vec, df_vec[-1]/((1+s/36000)**365))

			return (np.dot(flt_vec,df_vec)-swap_rate[i-1]*(np.sum(df_vec)))

		def swap_min2(s, swap_pricer, swap_rate, flt_vec, df_vec):

			return 1000000*swap_pricer2(s, swap_rate, flt_vec, df_vec)**2

		smin = minimize(swap_min2, .0004,args=(swap_pricer2, swap_rate, flt_vec, df_vec), method="SLSQP",options={'disp': False}).x[0]
		flt_vec = np.append(flt_vec,[((1+smin/36000)**365-1)*360/365]*delta_years[i-1])
		
		for j in range(1,delta_years[i-1]+1):
			df_vec = np.append(df_vec, df_vec[-1]/((1+smin/36000)**365))
		
		smin_all.append(smin)

	# We will overwrite the remaining forward rates with the ones stored in smin_all
	start = ['04/30/2022', '04/30/2023', '04/30/2024', '04/30/2025', '04/30/2026', '04/30/2027',\
	'04/30/2028', '04/30/2029', '04/30/2030', '04/30/2032', '04/30/2035', '04/30/2040',\
	'04/30/2050']
	end = ['04/30/2023', '04/30/2024', '04/30/2025', '04/30/2026', '04/30/2027', '04/30/2028',\
	'04/30/2029', '04/30/2030', '04/30/2032', '04/30/2035', '04/30/2040', '04/30/2050',\
	'04/30/2060']

	for i in range(0,13):
		fwd_rates = set_rates(fwd_rates, smin_all[i], start[i], end[i])

	dates = fwd_rates.index.strftime('%Y-%m-%d')
	result_dict = dict(zip(dates, fwd_rates.values))"""

	return spots

# set_rates function will allow us to easily overwrite unknown SOFR forward rates
def set_rates(fwd_rates, rate, start, end):
	fwd_rates[(fwd_rates.index >= start) & (fwd_rates.index <= end)]=rate
	return fwd_rates

def sr1_boot(quote, N_days, days_passed=0, sr1_rzd=0):
	result = ((100-quote)*N_days-sr1_rzd)/(N_days - days_passed)
	return result


def sr3_pricer(sofr_fwd, quote, start, end, sr3_rzd=1, sr3_btd=1):
	"""
	sr3 is a pricing function that will allow us to imply SOFR forward rates
	
	sofr_fwd is the unknown forward rate that we will be solving for
	sr3_rzd is the accrued portion of the front SR3-0 futures (if supplied)
	"""
	fwd_dates = pd.bdate_range(start, end)
	dt_fwd = pd.Series(fwd_dates).diff().dt.days/360
	dt_fwd = dt_fwd[1:]

	sr3_pricer = (sr3_btd*sr3_rzd*(sofr_fwd*dt_fwd+1).prod()-1)*360/90

	return sr3_pricer

def sr3_min(sofr_fwd, sr3_pricer, quote, start, end, sr3_rzd=1, sr3_btd=1):
	return 1000000*(100 - quote - sr3_pricer(sofr_fwd, quote, start, end, sr3_rzd=1, sr3_btd=1))**2


def swap_pricer(sofr_fwd, swap_rate, unknown_rate_date, end, swap_btd_y1=1, swap_btd_y2=1):
	"""
	sofr_swap is a pricing function that will allow us to imply SOFR forward rates from SOFR swaps
	
	sofr_fwd is the unknown forward rate that we will be solving for
	swap_btd_y1/y2 is the cash flow portion based on the bootstrapped rates (if supplied)
	"""
	  
	fwd_dates = pd.bdate_range(unknown_rate_date, end)
	dt_fwd = pd.Series(fwd_dates).diff().dt.days/360
	dt_fwd = dt_fwd[1:]

	sofr_swap_y1 = (swap_btd_y1-1)*360/365/swap_btd_y1-swap_rate/swap_btd_y1
	sofr_swap_y2 = (swap_btd_y2*(sofr_fwd*dt_fwd+1).prod()-1)*360/365 \
	/(swap_btd_y1*swap_btd_y2*(sofr_fwd*dt_fwd+1).prod())\
	-swap_rate/(swap_btd_y1*swap_btd_y2*(sofr_fwd*dt_fwd+1).prod())
	sofr_swap = sofr_swap_y1 + sofr_swap_y2
	print(sofr_swap_y1, sofr_swap_y2)
	#return 1000000*sofr_swap**2
	return sofr_swap_y1, sofr_swap_y2

def swap_min(sofr_fwd, swap_pricer, swap_rate, unknown_rate_date, end, swap_btd_y1=1, swap_btd_y2=1):
	sofr_swap_y1, sofr_swap_y2 = swap_pricer(sofr_fwd, swap_rate, unknown_rate_date, end, swap_btd_y1, swap_btd_y2)
	return 1000000*(sofr_swap_y1+sofr_swap_y2)**2
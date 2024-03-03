from django.shortcuts import render

import os
from django.contrib.staticfiles import finders

import pandas as pd
import numpy as np
from scipy.optimize import minimize

# Create your views here.
def create_SOFRForwardCurve(request):

	# User needs to input the start date (the as of date) and end date for the SOFR curve
	fwd_dates = pd.bdate_range(start='04/30/2020', end='05/03/2060')
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

	"""rzd_rates = pd.read_csv(file_path_sr3_rzd, index_col=0)
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
	sr3_btd = (np.transpose(btd_rates.values)*dt_btd.values+1).prod()"""

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

	"""
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
		fwd_rates = set_rates(fwd_rates, smin_all[i], start[i], end[i])"""



	dates = fwd_rates.index.strftime('%Y-%m-%d')
	result_dict = dict(zip(dates, fwd_rates.values))

	return result_dict

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
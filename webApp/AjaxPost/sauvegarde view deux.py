from django.http import JsonResponse
from django.http.response import HttpResponse

from django.views.generic import ListView

from django.shortcuts import render, redirect
from .forms import ProjectForm
from .models import Project

import calendar
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import dateutil.parser

import math

import pandas as pd
import numpy as np
from django.core import serializers


class ProjectView(ListView):
	model = Project
	template_name = 'project_list.html'
	context_object_name = "projects"

def Viewdata(request):
	return render(request, 'project_view.html')

def test(request):
	
	Debti = 100
	Debt = 40
	interest = 0

	while Debti!=Debt:
		Debti = Debt
		EBITDA = 250
		interest = Debti * 0.1
		CFADS = EBITDA
		DS = EBITDA/1.3
		Debt = DS * 1/(1+interest/Debt)

	context={
		'Debt': Debt,
		'interest': interest,
		'Debti': Debti,

		}
	return render(request, "testrr.html", context)


def project_view(request,id):

	project_form = ProjectForm()
	project = Project.objects.get(id=id)

	if request.method == "POST":
		project_form = ProjectForm(request.POST, instance=project)

		if project_form.is_valid():
			project_form.save()

			""" Timing inputs """

			inp_construction_start = request.POST['start_construction']
			inp_construction_end = request.POST['end_construction']
			inp_life = int(request.POST['operating_life'])
			inp_periodicity = int(request.POST['periodicity'])

			start_period = datetime.datetime.strptime(inp_construction_start, "%Y-%m-%d").date()
			end_construction = datetime.datetime.strptime(inp_construction_end, "%Y-%m-%d").date()

			int_operating_periods = math.ceil(int(inp_life)*12/int(inp_periodicity)+1)


			date_COD = end_construction + datetime.timedelta(days=1) 
			date_operations_end = end_construction + relativedelta(years=inp_life)

			""" Capacity and Production inputs """

			inp_capacity = int(request.POST['panels_capacity'])				
			inp_degradation = float(request.POST['annual_degradation'])/100

			if int(request.POST['production_choice']) == 1:
				inp_production = int(request.POST['p50'])
			elif int(request.POST['production_choice']) == 2:
				inp_production = int(request.POST['p90_10y'])
			else: 
				inp_production = int(request.POST['P99_10y'])

			inp_availability = float(request.POST['availability'])	

			seasonality = np.array([
			float(request.POST['seasonality_m1']),
			float(request.POST['seasonality_m2']),
			float(request.POST['seasonality_m3']),
			float(request.POST['seasonality_m4']),
			float(request.POST['seasonality_m5']),
			float(request.POST['seasonality_m6']),
			float(request.POST['seasonality_m7']),
			float(request.POST['seasonality_m8']),
			float(request.POST['seasonality_m9']),
			float(request.POST['seasonality_m10']),
			float(request.POST['seasonality_m11']),
			float(request.POST['seasonality_m12']),
			])

			sum_seasonality = np.sum(seasonality)

			""" Construction costs inputs """

			arr_construction_costs = np.array([
			float(request.POST['costs_m1']),
			float(request.POST['costs_m2']),
			float(request.POST['costs_m3']),
			float(request.POST['costs_m4']),
			float(request.POST['costs_m5']),
			float(request.POST['costs_m6']),
			float(request.POST['costs_m7']),
			float(request.POST['costs_m8']),
			float(request.POST['costs_m9']),
			float(request.POST['costs_m10']),
			float(request.POST['costs_m11']),
			float(request.POST['costs_m12']),
			])

			sum_construction_costs = np.sum(arr_construction_costs)

			r = relativedelta(end_construction,start_period)
			months_construction = (r.years * 12) + r.months + 1
			months_construction = math.ceil(int(months_construction))

			number_columns = months_construction + int_operating_periods

			""" Offtake contract and Electricity price inputs """

			inp_contract_start = request.POST['start_contract']
			date_contract_start = datetime.datetime.strptime(inp_contract_start, "%Y-%m-%d").date()

			inp_contract_end = request.POST['end_contract']
			date_contract_end = datetime.datetime.strptime(inp_contract_end, "%Y-%m-%d").date()

			inp_contract_price = float(request.POST['contract_price'])
			inp_price_contract_index_rate = float(request.POST['contract_indexation'])/100

			inp_contract_indexation_start_date = request.POST['contract_indexation_start_date']
			date_contract_indexation_start = datetime.datetime.strptime(inp_contract_indexation_start_date, "%Y-%m-%d").date()

			inp_price_merchant_index_rate_start_date = request.POST['price_elec_indexation_start_date']
			date_price_elec_indexation_start = datetime.datetime.strptime(inp_price_merchant_index_rate_start_date, "%Y-%m-%d").date()

			inp_price_merchant_index_rate = float(request.POST['price_elec_indexation'])/100

			arr_years_electricity_prices = array_electricity_prices(date_COD)

			if int(request.POST['price_elec_choice']) == 1:
				dic_price_elec = {
				"2022":float(request.POST['price_elec_low_y1']),
				"2023":float(request.POST['price_elec_low_y2']),
				"2024":float(request.POST['price_elec_low_y3']),
				"2025":float(request.POST['price_elec_low_y4']),
				"2026":float(request.POST['price_elec_low_y5']),
				"2027":float(request.POST['price_elec_low_y6']),
				"2028":float(request.POST['price_elec_low_y7']),
				"2029":float(request.POST['price_elec_low_y8']),
				"2030":float(request.POST['price_elec_low_y9']),
				"2031":float(request.POST['price_elec_low_y10']),
				"2032":float(request.POST['price_elec_low_y11']),
				"2033":float(request.POST['price_elec_low_y12']),
				"2034":float(request.POST['price_elec_low_y13']),
				"2035":float(request.POST['price_elec_low_y14']),
				"2036":float(request.POST['price_elec_low_y15']),
				"2037":float(request.POST['price_elec_low_y16']),
				"2038":float(request.POST['price_elec_low_y17']),
				"2039":float(request.POST['price_elec_low_y18']),
				"2040":float(request.POST['price_elec_low_y19']),
				"2041":float(request.POST['price_elec_low_y20']),
				"2042":float(request.POST['price_elec_low_y21']),
				"2043":float(request.POST['price_elec_low_y22']),
				"2044":float(request.POST['price_elec_low_y23']),
				"2045":float(request.POST['price_elec_low_y24']),
				"2046":float(request.POST['price_elec_low_y25']),
				"2047":float(request.POST['price_elec_low_y26']),
				"2048":float(request.POST['price_elec_low_y27']),
				"2049":float(request.POST['price_elec_low_y28']),
				"2050":float(request.POST['price_elec_low_y29']),
				"2051":float(request.POST['price_elec_low_y30']),
				}
			elif int(request.POST['price_elec_choice']) == 2:
				dic_price_elec = {
				"2022":float(request.POST['price_elec_med_y1']),
				"2023":float(request.POST['price_elec_med_y2']),
				"2024":float(request.POST['price_elec_med_y3']),
				"2025":float(request.POST['price_elec_med_y4']),
				"2026":float(request.POST['price_elec_med_y5']),
				"2027":float(request.POST['price_elec_med_y6']),
				"2028":float(request.POST['price_elec_med_y7']),
				"2029":float(request.POST['price_elec_med_y8']),
				"2030":float(request.POST['price_elec_med_y9']),
				"2031":float(request.POST['price_elec_med_y10']),
				"2032":float(request.POST['price_elec_med_y11']),
				"2033":float(request.POST['price_elec_med_y12']),
				"2034":float(request.POST['price_elec_med_y13']),
				"2035":float(request.POST['price_elec_med_y14']),
				"2036":float(request.POST['price_elec_med_y15']),
				"2037":float(request.POST['price_elec_med_y16']),
				"2038":float(request.POST['price_elec_med_y17']),
				"2039":float(request.POST['price_elec_med_y18']),
				"2040":float(request.POST['price_elec_med_y19']),
				"2041":float(request.POST['price_elec_med_y20']),
				"2042":float(request.POST['price_elec_med_y21']),
				"2043":float(request.POST['price_elec_med_y22']),
				"2044":float(request.POST['price_elec_med_y23']),
				"2045":float(request.POST['price_elec_med_y24']),
				"2046":float(request.POST['price_elec_med_y25']),
				"2047":float(request.POST['price_elec_med_y26']),
				"2048":float(request.POST['price_elec_med_y27']),
				"2049":float(request.POST['price_elec_med_y28']),
				"2050":float(request.POST['price_elec_med_y29']),
				"2051":float(request.POST['price_elec_med_y30']),
				}
			else: 
				dic_price_elec = {
				"2022":float(request.POST['price_elec_high_y1']),
				"2023":float(request.POST['price_elec_high_y2']),
				"2024":float(request.POST['price_elec_high_y3']),
				"2025":float(request.POST['price_elec_high_y4']),
				"2026":float(request.POST['price_elec_high_y5']),
				"2027":float(request.POST['price_elec_high_y6']),
				"2028":float(request.POST['price_elec_high_y7']),
				"2029":float(request.POST['price_elec_high_y8']),
				"2030":float(request.POST['price_elec_high_y9']),
				"2031":float(request.POST['price_elec_high_y10']),
				"2032":float(request.POST['price_elec_high_y11']),
				"2033":float(request.POST['price_elec_high_y12']),
				"2034":float(request.POST['price_elec_high_y13']),
				"2035":float(request.POST['price_elec_high_y14']),
				"2036":float(request.POST['price_elec_high_y15']),
				"2037":float(request.POST['price_elec_high_y16']),
				"2038":float(request.POST['price_elec_high_y17']),
				"2039":float(request.POST['price_elec_high_y18']),
				"2040":float(request.POST['price_elec_high_y19']),
				"2041":float(request.POST['price_elec_high_y20']),
				"2042":float(request.POST['price_elec_high_y21']),
				"2043":float(request.POST['price_elec_high_y22']),
				"2044":float(request.POST['price_elec_high_y23']),
				"2045":float(request.POST['price_elec_high_y24']),
				"2046":float(request.POST['price_elec_high_y25']),
				"2047":float(request.POST['price_elec_high_y26']),
				"2048":float(request.POST['price_elec_high_y27']),
				"2049":float(request.POST['price_elec_high_y28']),
				"2050":float(request.POST['price_elec_high_y29']),
				"2051":float(request.POST['price_elec_high_y30']),
				}

			""" Operating costs """

			inp_opex = float(request.POST['opex'])
			inp_opex_indexation_start_date = request.POST['opex_indexation_start_date']
			date_opex_indexation_start = datetime.datetime.strptime(inp_opex_indexation_start_date, "%Y-%m-%d").date()
			inp_opex_indexation_rate = float(request.POST['opex_indexation'])/100

			""" Senior debt """

			inp_debt_commitment_fee = float(request.POST['debt_commitment_fee'])/100

			inp_all_in_interest = np.array([
				float(request.POST['debt_margin']),
				float(request.POST['debt_swap_rate']),
				float(request.POST['debt_swap_margin']),
				float(request.POST['debt_reference_rate_buffer']),
				])

			inp_debt_interest_rate = np.sum(inp_all_in_interest)/100

			inp_debt_tenor = float(request.POST['debt_tenor'])
			date_debt_maturity = start_period + relativedelta(months=+int(inp_debt_tenor*12)-1)
			date_debt_maturity = date_debt_maturity.replace(day = calendar.monthrange(date_debt_maturity.year, date_debt_maturity.month)[1])

			inp_target_DSCR = float(request.POST['debt_target_DSCR'])
			inp_debt_gearing_max = float(request.POST['debt_gearing_max'])/100

			""" Tax and accounting """

			inp_corporate_income_tax_rate = float(request.POST['corporate_income_tax'])/100

			""" Arrays instanciation """

			""" Variables instanciation """

			days_in_operation = (date_operations_end - date_COD).days

			""" Create date series """

			first_day_construction_start = first_day_month(start_period)
			last_day_construction_end = end_date_period(end_construction)

			first_day_operations_start = first_day_month(date_COD)
			first_day_operations_start_plus_six = first_day_next_month(date_COD,inp_periodicity)

			last_day_operations_end = end_date_period(date_operations_end)
			last_day_operations_end_plus_six = first_day_next_month(date_operations_end,inp_periodicity)

			freq = str(inp_periodicity)+"MS"
			freq2 = str(inp_periodicity)+"M"

			start_period_construction = pd.Series(pd.date_range(first_day_construction_start,last_day_construction_end, freq='MS')).clip(lower=pd.Timestamp(start_period))
			end_period_construction = pd.Series(pd.date_range(first_day_construction_start,last_day_construction_end, freq='M')).clip(upper=pd.Timestamp(end_construction))
			
			start_period_operations = pd.Series(pd.date_range(first_day_operations_start, last_day_operations_end,freq=freq)).clip(lower=pd.Timestamp(date_COD))
			end_period_operations = pd.Series(pd.date_range(first_day_operations_start_plus_six, last_day_operations_end_plus_six,freq=freq2)).clip(upper=pd.Timestamp(date_operations_end))

			arr_date_start_period = pd.concat([start_period_construction,start_period_operations])
			arr_date_end_period = pd.concat([end_period_construction,end_period_operations])

			arr_date_end_period_year = arr_date_end_period.dt.year

			arr_date_start_contract_period = array_time(arr_date_start_period,inp_contract_start,inp_contract_end)
			arr_date_end_contract_period = array_time(arr_date_end_period,inp_contract_start,inp_contract_end)

			arr_date_start_contract_indexation = array_time(arr_date_start_period,date_contract_indexation_start,inp_contract_end)
			arr_date_end_contract_indexation = array_time(arr_date_end_period,date_contract_indexation_start,inp_contract_end)

			arr_date_start_elec_indexation = array_time(arr_date_start_period,date_price_elec_indexation_start,date_operations_end)
			arr_date_end_elec_indexation = array_time(arr_date_end_period,date_price_elec_indexation_start,date_operations_end)

			arr_date_start_opex_indexation = array_time(arr_date_start_period,date_opex_indexation_start,date_operations_end)
			arr_date_end_opex_indexation = array_time(arr_date_end_period,date_opex_indexation_start,date_operations_end)

			""" Create flag series """

			arr_flag_operations = (arr_date_end_period>pd.to_datetime(date_COD)).astype(int)
			arr_flag_construction = 1-arr_flag_operations
			arr_flag_contract = array_flag(arr_date_end_contract_period,inp_contract_start,arr_date_start_contract_period,inp_contract_end)
			arr_flag_contract_indexation = array_flag(arr_date_end_contract_indexation,date_contract_indexation_start,arr_date_start_contract_indexation,inp_contract_end)
			arr_flag_elec_indexation = array_flag(arr_date_end_elec_indexation,date_price_elec_indexation_start,arr_date_start_elec_indexation,date_operations_end)
			arr_flag_opex_indexation = array_flag(arr_date_end_opex_indexation,date_opex_indexation_start,arr_date_start_opex_indexation,date_operations_end)
			arr_flag_debt_amortisation = (arr_date_end_period<pd.to_datetime(date_debt_maturity)).astype(int)*arr_flag_operations

			""" Create time series """

			arr_time_days_in_period = array_days(arr_date_end_period,arr_date_start_period,1)
			arr_time_days_under_contract = array_days(arr_date_end_contract_period,arr_date_start_contract_period,arr_flag_contract)

			arr_time_pct_under_contract=arr_time_days_under_contract/arr_time_days_in_period

			arr_time_days_contract_indexation = array_days(arr_date_end_contract_indexation,arr_date_start_contract_indexation,arr_flag_contract_indexation)
			arr_time_days_merchant_indexation = array_days(arr_date_end_elec_indexation,arr_date_start_elec_indexation,arr_flag_elec_indexation)
			arr_time_days_opex_indexation = array_days(arr_date_end_opex_indexation,arr_date_start_opex_indexation,arr_flag_opex_indexation)


			arr_time_days_in_year = arr_date_end_period.dt.is_leap_year*366 + (1-arr_date_end_period.dt.is_leap_year)*365
			arr_time_years_in_period = arr_time_days_in_period/arr_time_days_in_year
			arr_time_years_in_period_operations = arr_time_years_in_period*arr_flag_operations
			arr_time_years_from_COD_EOP = arr_time_years_in_period_operations.cumsum()
			arr_time_years_from_COD_BOP = arr_time_years_from_COD_EOP-arr_time_years_in_period_operations
			arr_time_years_from_COD_avg = (arr_time_years_from_COD_BOP+arr_time_years_from_COD_EOP)/2

			arr_time_years_contract_indexation=(arr_time_days_contract_indexation/arr_time_days_in_year).cumsum()
			arr_time_years_merchant_indexation=(arr_time_days_merchant_indexation/arr_time_days_in_year).cumsum()
			arr_time_years_opex_indexation=(arr_time_days_merchant_indexation/arr_time_days_in_year).cumsum()

			""" Production """

			arr_time_seasonality = array_seasonality(arr_date_start_period,arr_date_end_period,seasonality)
			arr_prod_degrad = 1/(1+inp_degradation)**arr_time_years_from_COD_avg
			arr_prod_capacity_af_degrad = inp_capacity*arr_prod_degrad
			arr_prod = inp_production/1000*arr_time_seasonality[0]*arr_prod_capacity_af_degrad*arr_flag_operations

			""" Construction """

			arr_fp_uses_construction_costs = np.hstack([arr_construction_costs,np.zeros(arr_flag_operations.size-arr_construction_costs.size)])*arr_flag_construction
			arr_construction_costs_cumul = arr_fp_uses_construction_costs.cumsum()
			total_construction_costs = max(arr_construction_costs_cumul)
			
			""" Formatting """

			arr_date_start_period_format = arr_date_start_period.dt.date
			arr_date_end_period_format = arr_date_end_period.dt.date

			arr_date_start_contract_period_format = arr_date_start_contract_period.dt.date.mask(arr_flag_contract==False, False)
			arr_date_end_contract_period_format = arr_date_end_contract_period.dt.date.mask(arr_flag_contract==False, False)

			arr_date_start_contract_indexation = arr_date_start_contract_indexation.dt.date.mask(arr_flag_contract_indexation==False, False)
			arr_date_end_contract_indexation = arr_date_end_contract_indexation.dt.date.mask(arr_flag_contract_indexation==False, False)
			
			arr_date_start_elec_indexation = arr_date_start_elec_indexation.dt.date.mask(arr_flag_elec_indexation==False, False)
			arr_date_end_elec_indexation = arr_date_end_elec_indexation.dt.date.mask(arr_flag_elec_indexation==False, False)

			arr_date_start_opex_indexation = arr_date_start_opex_indexation.dt.date.mask(arr_flag_opex_indexation==False, False)
			arr_date_end_opex_indexation = arr_date_end_opex_indexation.dt.date.mask(arr_flag_opex_indexation==False, False)

			""" Indexation """

			arr_index_merchant = array_index(inp_price_merchant_index_rate,arr_time_years_merchant_indexation)
			arr_index_contracted = array_index(inp_price_contract_index_rate,arr_time_years_contract_indexation)
			arr_index_opex = array_index(inp_opex_indexation_rate,arr_time_years_opex_indexation)

			""" Price """

			arr_price_merchant = array_elec_prices(arr_date_end_period_year,dic_price_elec)
			arr_price_merchant_aft_index = arr_price_merchant*arr_index_merchant
			
			arr_price_contracted = inp_contract_price*arr_flag_contract
			arr_price_contracted_aft_index = arr_price_contracted*arr_index_contracted

			arr_is_rev_contracted = arr_price_contracted_aft_index*arr_prod*arr_time_pct_under_contract/1000
			arr_is_rev_merchant = arr_price_merchant_aft_index*arr_prod*(1-arr_time_pct_under_contract)/1000
			arr_is_rev_total = arr_is_rev_contracted+arr_is_rev_merchant

			arr_is_operating_costs = inp_opex*arr_index_opex*arr_time_years_in_period_operations

			arr_is_depreciation = total_construction_costs*arr_time_years_in_period_operations/inp_life


	

			"""arr_sizing_debt_interest_operations = []


			arr_debt_amount_available = np.append(arr_debt_amount_available,0)
			arr_debt_commitment_fee = np.append(arr_debt_commitment_fee,0)

			arr_sizing_debt_interest_operations = np.append(arr_sizing_debt_interest_operations,debt_BoP*inp_debt_interest_rate*days_in_period/360) 

			debt_repayment = arr_debt_repayment[months_construction+i]
			cumul_debt_repayment += debt_repayment
			arr_debt_EoP = np.append(arr_debt_EoP,debt_BoP-debt_repayment)"""

			""" EBITDA """

			arr_is_EBITDA = arr_is_rev_total-arr_is_operating_costs
			arr_is_EBITDA_margin = np.divide(arr_is_EBITDA,arr_is_rev_total, out=np.zeros_like(arr_is_EBITDA), where=arr_is_rev_total!=0)*100
			arr_is_EBIT = arr_is_EBITDA-arr_is_depreciation


			debt_amount = 1000
			debt_amount_target = 2000
			arr_debt_repayment = np.full(number_columns, -100)
			arr_sizing_debt_repayment_target = np.full(number_columns, -200)


			while abs(debt_amount-debt_amount_target)>10:

				debt_amount = debt_amount_target
				arr_debt_repayment = -arr_sizing_debt_repayment_target

				""" Debt """

				arr_debt_drawn = (arr_construction_costs_cumul*inp_debt_gearing_max).clip(upper=debt_amount)
				cumul_debt_drawn  = max(arr_debt_drawn)
				arr_debt_EoP = (arr_debt_drawn+arr_debt_repayment.cumsum()).clip(lower=0)
				arr_debt_BoP = np.roll(arr_debt_EoP, 1)
				arr_debt_interest = arr_debt_BoP*inp_debt_interest_rate*arr_time_days_in_period/360
				arr_sizing_debt_interest_operations = arr_debt_interest*arr_flag_debt_amortisation

				arr_is_EBT = arr_is_EBIT-arr_debt_interest
				arr_is_corporate_tax = -inp_corporate_income_tax_rate*arr_is_EBT.clip(lower=0)
				arr_is_net_income = arr_is_EBT-arr_is_corporate_tax

				""" Debt sizing """

				arr_sizing_CFADS = (arr_is_EBIT-arr_is_corporate_tax)*arr_flag_debt_amortisation
				arr_sizing_target_DS_sizing = arr_sizing_CFADS/inp_target_DSCR

				arr_sizing_debt_avg_interest = np.divide(arr_sizing_debt_interest_operations,arr_debt_BoP,out=np.zeros_like(arr_sizing_debt_interest_operations), where=arr_debt_BoP!=0)/arr_time_days_in_period*360
				arr_sizing_debt_period_discount_factor = (1/(1+(arr_sizing_debt_avg_interest*arr_time_days_in_period/360)))*arr_flag_debt_amortisation+arr_flag_construction
				arr_sizing_debt_period_discount_factor_cumul = arr_sizing_debt_period_discount_factor.cumprod()

				debt_amount_DSCR = sum(arr_sizing_target_DS_sizing*arr_sizing_debt_period_discount_factor_cumul)
				debt_amount_gearing = total_construction_costs*inp_debt_gearing_max
				debt_amount_target = min(debt_amount_DSCR,debt_amount_gearing)

				""" Debt sculpting """
				"""npv_CFADS = sum(arr_sizing_CFADS*arr_sizing_debt_period_discount_factor_cumul)
				DSCR_sculpting = npv_CFADS/cumul_debt_drawn



				
				arr_sizing_debt_repayment_target = (arr_sizing_CFADS/DSCR_sculpting-arr_sizing_debt_interest_operations).clip(lower=0)"""


				arr_sizing_debt_repayment_target = (arr_sizing_target_DS_sizing-arr_sizing_debt_interest_operations).clip(lower=0)


				"""npv_CFADS = arr_sizing_CFADS*arr_sizing_debt_period_discount_factor_cumul
				DSCR_sculpting = npv_CFADS/cumul_debt_drawn
				arr_sizing_target_DS_sculpting=arr_sizing_CFADS/inp_target_DSCR
				arr_sizing_debt_repayment_target = (arr_sizing_target_DS_sculpting-arr_sizing_debt_interest_operations)*arr_flag_debt_amortisation
				arr_sizing_debt_repayment_target = np.clip(arr_sizing_debt_repayment_target,0,a_max=None)"""

				arr_debt_service_repayment = -arr_debt_repayment
				arr_debt_service = (arr_sizing_debt_interest_operations-arr_debt_repayment)
				arr_ratios_DSCR = np.divide(arr_sizing_CFADS,arr_debt_service, out=np.zeros_like(arr_sizing_CFADS), where=arr_debt_service!=0)



			summary_debt = np.array([debt_amount,debt_amount_DSCR,debt_amount_gearing,debt_amount_target,cumul_debt_drawn])
			data_dump_sidebar = np.array([date_COD,date_operations_end,sum_seasonality,sum_construction_costs])

			d = {
			'Total rev': arr_is_rev_total, 
			'Contracted rev': arr_is_rev_contracted, 
			}



			dataf = pd.DataFrame(d)
			dataf.reset_index(drop=True, inplace=True)



			return JsonResponse(
							{

							"dataf":dataf.to_json(),

							"data_dump_sidebar":data_dump_sidebar.tolist(),
		
							"arr_date_start_period_format":arr_date_start_period_format.tolist(),
							"arr_date_end_period_format":arr_date_end_period_format.tolist(),
							"arr_date_end_period_year":arr_date_end_period_year.tolist(),



							"arr_debt_interest":arr_debt_interest.tolist(),
							"arr_sizing_debt_interest_operations":arr_sizing_debt_interest_operations.tolist(),

							"arr_debt_service_repayment":arr_debt_service_repayment.tolist(),
							"arr_debt_service":arr_debt_service.tolist(),
							"arr_ratios_DSCR":arr_ratios_DSCR.tolist(),

							"arr_date_start_contract_period_format":arr_date_start_contract_period_format.tolist(),
							"arr_date_end_contract_period_format":arr_date_end_contract_period_format.tolist(),
							
							"arr_date_start_contract_indexation":arr_date_start_contract_indexation.tolist(),
							"arr_date_end_contract_indexation":arr_date_end_contract_indexation.tolist(),

							"arr_date_start_elec_indexation":arr_date_start_elec_indexation.tolist(),
							"arr_date_end_elec_indexation":arr_date_end_elec_indexation.tolist(),

							"arr_date_start_opex_indexation":arr_date_start_opex_indexation.tolist(),
							"arr_date_end_opex_indexation":arr_date_end_opex_indexation.tolist(),

							"arr_flag_debt_amortisation":arr_flag_debt_amortisation.tolist(),


							"arr_flag_construction":arr_flag_construction.tolist(),
							"arr_flag_operations":arr_flag_operations.tolist(),
							"arr_flag_contract":arr_flag_contract.tolist(),
							"arr_flag_contract_indexation":arr_flag_contract_indexation.tolist(),
							"arr_flag_elec_indexation":arr_flag_elec_indexation.tolist(),
							"arr_flag_opex_indexation":arr_flag_elec_indexation.tolist(),



							"arr_time_days_in_period":arr_time_days_in_period.tolist(),
							"arr_time_days_under_contract":arr_time_days_under_contract.tolist(),
							"arr_time_pct_under_contract":arr_time_pct_under_contract.tolist(),



							"arr_time_days_contract_indexation":arr_time_days_contract_indexation.tolist(),
							"arr_time_days_merchant_indexation":arr_time_days_merchant_indexation.tolist(),
							"arr_time_days_opex_indexation":arr_time_days_merchant_indexation.tolist(),


							"arr_index_merchant":arr_index_merchant.tolist(),
							"arr_index_contracted":arr_index_contracted.tolist(),
							"arr_index_opex":arr_index_opex.tolist(),


							"arr_time_years_contract_indexation":arr_time_years_contract_indexation.tolist(),
							"arr_time_years_merchant_indexation":arr_time_years_merchant_indexation.tolist(),
							"arr_time_years_opex_indexation":arr_time_years_merchant_indexation.tolist(),


							"arr_price_merchant":arr_price_merchant,
							"arr_price_merchant_aft_index":arr_price_merchant_aft_index.tolist(),

							"arr_price_contracted":arr_price_contracted.tolist(),
							"arr_price_contracted_aft_index":arr_price_contracted_aft_index.tolist(),



							"arr_time_days_in_year":arr_time_days_in_year.tolist(),
							"arr_time_years_in_period":arr_time_years_in_period.tolist(),
							"arr_time_years_in_period_operations":arr_time_years_in_period_operations.tolist(),
							"arr_time_years_from_COD_BOP":arr_time_years_from_COD_BOP.tolist(),
							"arr_time_years_from_COD_EOP":arr_time_years_from_COD_EOP.tolist(),
							"arr_time_years_from_COD_avg":arr_time_years_from_COD_avg.tolist(),

							"arr_time_seasonality":arr_time_seasonality.tolist(),
							"arr_prod_degrad":arr_prod_degrad.tolist(),
							"arr_prod_capacity_af_degrad":arr_prod_capacity_af_degrad.tolist(),
							"arr_prod":arr_prod.tolist(),

							"arr_is_rev_contracted":arr_is_rev_contracted.tolist(),
							"arr_is_rev_merchant":arr_is_rev_merchant.tolist(),
							"arr_is_rev_total":arr_is_rev_total.tolist(),

							"arr_is_operating_costs":arr_is_operating_costs.tolist(),

							"arr_is_EBITDA":arr_is_EBITDA.tolist(),
							"arr_is_EBITDA_margin":arr_is_EBITDA_margin.tolist(),
							"arr_is_depreciation":arr_is_depreciation.tolist(),

							"arr_is_EBIT":arr_is_EBIT.tolist(),
							"arr_is_EBT":arr_is_EBT.tolist(),
							"arr_is_corporate_tax":arr_is_corporate_tax.tolist(),
							"arr_is_net_income":arr_is_net_income.tolist(),


							"arr_debt_BoP":arr_debt_BoP.tolist(),
							"arr_debt_drawn":arr_debt_drawn.tolist(),
							"arr_debt_repayment":arr_debt_repayment.tolist(),

							"arr_debt_EoP":arr_debt_EoP.tolist(),



							"arr_sizing_CFADS":arr_sizing_CFADS.tolist(),
							"arr_sizing_target_DS_sizing":arr_sizing_target_DS_sizing.tolist(),
							"arr_sizing_debt_avg_interest":arr_sizing_debt_avg_interest.tolist(),
							"arr_sizing_debt_period_discount_factor":arr_sizing_debt_period_discount_factor.tolist(),
							"arr_sizing_debt_period_discount_factor_cumul":arr_sizing_debt_period_discount_factor_cumul.tolist(),




							"seasonality":seasonality.tolist(),

							"arr_fp_uses_construction_costs":arr_fp_uses_construction_costs.tolist(),
							"arr_years_electricity_prices":arr_years_electricity_prices.tolist(),



							"arr_construction_costs":arr_construction_costs.tolist(),
							"arr_construction_costs_cumul":arr_construction_costs_cumul.tolist(),
							"summary_debt":summary_debt.tolist(),

						},safe=False, status=200)
		else:
			errors = project_form.errors.as_json()
			return JsonResponse({"errors": errors}, status=400)

	else:
		project_form = ProjectForm(instance=project)

	context={
		'project_form': project_form,
		'project':project,
		}
	
	return render(request, "project_view.html", context)


"""USED"""

def array_time(timeline,start,end):	
	timeline_result = timeline.clip(lower=pd.Timestamp(start),upper=pd.Timestamp(end))
	return timeline_result

def array_flag(timeline_end,start,timeline_start,end):	
	flag_result = (timeline_end>pd.to_datetime(start))*(timeline_start<pd.to_datetime(end))
	return flag_result

def array_days(arr_end_date,arr_start_date,flag):
	number_days = ((arr_end_date-arr_start_date).dt.days + 1)*flag
	return number_days

def array_index(indexation_rate,indexation_year):
	arr_indexation = (1+indexation_rate)**indexation_year
	return arr_indexation

def array_elec_prices(arr_date_end_period_year,dic_price_elec):
	electricity_prices = []
	
	for row in arr_date_end_period_year:
		if str(row) in dic_price_elec.keys():
			electricity_prices.append(dic_price_elec[str(row)])
	
	return electricity_prices


def array_seasonality(arr_date_start_period,arr_date_end_period,seasonality):
	data = {'start':arr_date_start_period,
			'end':arr_date_end_period}

	df = pd.DataFrame(data)

	df_seasonality_result = pd.DataFrame(columns=arr_date_end_period)

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

	return arr_time_seasonality

def array_electricity_prices(start_date):
	arr_years_electricity_prices = np.array([])
	year = start_date.year
	for i in range(0,30):
		arr_years_electricity_prices = np.append(arr_years_electricity_prices,year+i)
	return arr_years_electricity_prices


"""UNUSED"""


def end_period(start_period,inp_periodicity,periodicity_switch,latest_date):	
	start_period_plus_periodicity = start_period + relativedelta(months=+int(inp_periodicity)-1)*periodicity_switch
	end_period = min(latest_date,start_period_plus_periodicity.replace(day = calendar.monthrange(start_period_plus_periodicity.year, start_period_plus_periodicity.month)[1]))
	return end_period


def end_date_period(period):	
	end_date_period = period.replace(day = calendar.monthrange(period.year, period.month)[1])
	return end_date_period

def end_date_period_test(period):	
	end_date_period = period.replace(day = calendar.monthrange(period.year, period.month)[1]) + datetime.timedelta(days=1)
	return end_date_period

def first_day_previous_month(date):
	first_day_previous_month = date.replace(day=1) + relativedelta(months=-1)
	return first_day_previous_month

def first_day_month(date):
	first_day_month = date.replace(day=1)
	return first_day_month

def first_day_next_month(date):
	first_day_next_month = date.replace(day=1) + relativedelta(months=1)
	return first_day_next_month

def first_day_next_month(date,periodicity):
	first_day_next_month = date.replace(day=1) + relativedelta(months=periodicity) + datetime.timedelta(days=-1)
	return first_day_next_month

def previous_end_date_period(period):	
	end_date_period = period + relativedelta(months=-int(1))
	end_date_period.replace(day = calendar.monthrange(end_date_period.year, end_date_period.month)[1])
	return end_date_period

def days_in_period(start_period,end_period):
	days_in_period = (end_period + datetime.timedelta(days=1) - start_period).days
	return days_in_period

def years_in_period(start_period,end_period):
	days_in_period = (end_period + datetime.timedelta(days=1) - start_period).days
	days_year = 366 if calendar.isleap(end_period.year) else 365
	years_in_period = days_in_period/days_year
	return years_in_period

def array_time_array(start_date, end_date, start_period, end_period):
	days_to_consider_in_period = max(0,((min(end_date,end_period)-max(start_date,start_period)).days+1))
	days_year = 366 if calendar.isleap(end_period.year) else 365
	years_of_timeline = days_to_consider_in_period/days_year
	return years_of_timeline

def interests(debt_drawn, interest_rate, days_in_period):
	interests = debt_drawn*interest_rate*days_in_period/360
	return interests

def commitment_fee(amount_available, commitment_fee_rate, days_in_period):
	commitment_fee = amount_available*commitment_fee_rate*days_in_period/360
	return commitment_fee				

def days_in_month(start_date, end_date):

	dates_in_period = pd.date_range(start=start_date, end=end_date).values.astype('datetime64[D]').tolist()
	arr_time_days_in_period_per_months = np.array([])
	arr_time_days_in_period = np.array([])
	days_in_month = 0

	for i in range(1,13):
		count = 0
		try:
			for value in dates_in_period:
				
				if value.month == i:
					count += 1
					days_in_month = calendar.monthrange(value.year, value.month)[1]
			
			arr_time_days_in_period_per_months = np.append(arr_time_days_in_period_per_months,count/days_in_month)

		except ZeroDivisionError:

			arr_time_days_in_period_per_months = np.append(arr_time_days_in_period_per_months,0)

	return arr_time_days_in_period_per_months




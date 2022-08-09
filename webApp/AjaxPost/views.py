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


def compute_days_per_month(start_date, end_date):

	dates_in_period = pd.date_range(start=start_date, end=end_date).values.astype('datetime64[D]').tolist()
	arr_days_per_months = np.array([])
	arr_days = np.array([])
	days_month = 0

	for i in range(1,13):
		count = 0
		try:
			for value in dates_in_period:
				
				if value.month == i:
					count += 1
					days_month = calendar.monthrange(value.year, value.month)[1]
			
			arr_days_per_months = np.append(arr_days_per_months,count/days_month)

		except ZeroDivisionError:

			arr_days_per_months = np.append(arr_days_per_months,0)

	return arr_days_per_months


def create_array_electricity_prices(start_date):

	arr_years_electricity_prices = np.array([])
	year = start_date.year

	for i in range(0,30):
		arr_years_electricity_prices = np.append(arr_years_electricity_prices,year+i)

	return arr_years_electricity_prices

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
			final_date = end_construction + relativedelta(years=inp_life) + datetime.timedelta(days=1)

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

			construction_costs = np.array([
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

			sum_construction_costs = np.sum(construction_costs)

			r = relativedelta(end_construction,start_period)
			months_construction = (r.years * 12) + r.months + 1
			months_construction = math.ceil(int(months_construction))

			""" Offtake contract and Electricity price inputs """

			inp_contract_start = request.POST['start_contract']
			date_contract_start = datetime.datetime.strptime(inp_contract_start, "%Y-%m-%d").date()

			inp_contract_end = request.POST['end_contract']
			date_contract_end = datetime.datetime.strptime(inp_contract_end, "%Y-%m-%d").date()

			inp_contract_price = float(request.POST['contract_price'])
			inp_contract_indexation_rate = float(request.POST['contract_indexation'])/100

			inp_contract_indexation_start_date = request.POST['contract_indexation_start_date']
			date_contract_indexation_start = datetime.datetime.strptime(inp_contract_indexation_start_date, "%Y-%m-%d").date()

			inp_price_elec_indexation_start_date = request.POST['price_elec_indexation_start_date']
			date_price_elec_indexation_start = datetime.datetime.strptime(inp_price_elec_indexation_start_date, "%Y-%m-%d").date()

			inp_price_elec_indexation = float(request.POST['price_elec_indexation'])

			arr_years_electricity_prices = create_array_electricity_prices(date_COD)

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

			days_in_operation = (final_date - date_COD).days
			debt_amount = 99
			debt_amount_DSCR = 100
			arr_debt_target_repayment = np.array([])
			DSCR_sculpting = 2

			for i in range(0,months_construction+int_operating_periods):
				arr_debt_target_repayment = np.append(arr_debt_target_repayment,1)

			""" Construction period """

			while debt_amount != debt_amount_DSCR:

				start_period = datetime.datetime.strptime(inp_construction_start, "%Y-%m-%d").date()
				cumul_pct_year = 0
				cumul_year_contract_indexation = 0
				cumul_year_electricity_price_indexation = 0
				cumul_year_opex_indexation = 0
				cumul_construction_costs = 0
				cumul_debt_drawn = 0
				cumul_debt_repayment = 0
				cumul_equity_drawn = 0
	
				"""arr_debt_repayment = np.array([])"""

				debt_amount = debt_amount_DSCR
				arr_debt_repayment= arr_debt_target_repayment

				arr_start_period = np.array([])
				arr_end_period = np.array([])
				arr_period_type = np.array([])

				arr_start_period_financing_plan = np.array([])
				arr_end_period_financing_plan = np.array([])

				arr_period_type = np.array([])
				arr_days = np.array([])
				arr_pct_year = np.array([])
				arr_pct_year_operations = np.array([])
				arr_years_from_COD_BOP = np.array([])
				arr_years_from_COD_EOP = np.array([])

				arr_days_months = np.array([])
				arr_seasonality = np.array([])

				arr_degradation = np.array([])
				arr_capacity_after_degradation = np.array([])

				arr_contract_indexation = np.array([])
				arr_days_contract_in_period_pct = np.array([])
				
				arr_electricity_price = np.array([])
				arr_electricity_price_indexation = np.array([])

				arr_revenues_contracted = np.array([])
				arr_revenues_merchant = np.array([])
				
				arr_opex = np.array([])
				arr_opex_indexation = np.array([])

				arr_EBITDA = np.array([]) 
				arr_EBITDA_margin = np.array([])

				arr_construction = np.array([])
				arr_construction_costs = np.array([])

				arr_depreciation = np.array([])

				arr_debt_amount_available = np.array([])
				arr_debt_upfront_fee = np.array([])
				arr_debt_commitment_fee = np.array([])

				arr_debt_BoP = np.array([])
				arr_debt_drawn = np.array([])
				arr_debt_EoP = np.array([])
				arr_debt_interest = np.array([])
				arr_debt_interest_construction = np.array([])
				arr_debt_interest_operations = np.array([])
				arr_debt_amortisation = np.array([])
				arr_CFADS = np.array([])
				arr_target_DS_sizing = np.array([])
				arr_cumul_period_discount_factor = np.array([])
				arr_DSCR = np.array([])
				arr_debt_service = np.array([])

				arr_test = np.array([])


				arr_equity_drawn = np.array([])


				for i in range(0, months_construction):

					arr_test = np.append(arr_test,1)
					arr_start_period = np.append(arr_start_period,start_period)
					arr_start_period_financing_plan = np.append(arr_start_period_financing_plan,start_period)
					
					end_period = min(end_construction,start_period.replace(day = calendar.monthrange(start_period.year, start_period.month)[1]))
					
					arr_end_period = np.append(arr_end_period,end_period)
					arr_end_period_financing_plan = np.append(arr_end_period_financing_plan,end_period)

					days_period = (end_period + datetime.timedelta(days=1) - start_period).days
					arr_days = np.append(arr_days,days_period)
					
					days_year = 366 if calendar.isleap(end_period.year) else 365
					arr_pct_year = np.append(arr_pct_year,days_period/days_year)
					
					arr_construction = np.append(arr_construction,construction_costs[i])
					cumul_construction_costs += construction_costs[i]
					arr_construction_costs = np.append(arr_construction_costs,cumul_construction_costs)


					""" Senior debt """
					arr_debt_amortisation = np.append(arr_debt_amortisation,0)

					arr_debt_BoP = np.append(arr_debt_BoP,cumul_debt_drawn)
					arr_debt_interest = np.append(arr_debt_interest,cumul_debt_drawn*inp_debt_interest_rate*days_period/360)
					arr_debt_interest_construction = np.append(arr_debt_interest_construction,cumul_debt_drawn*inp_debt_interest_rate*days_period/360)
					arr_debt_interest_operations = np.append(arr_debt_interest_operations,0) 
					
					debt_amount_available = max(0,debt_amount-cumul_debt_drawn)

					debt_drawn = min(debt_amount_available,construction_costs[i]*inp_debt_gearing_max)
					equity_drawn = construction_costs[i]-debt_drawn
					cumul_debt_drawn += debt_drawn
					cumul_equity_drawn += equity_drawn
					arr_debt_drawn = np.append(arr_debt_drawn,debt_drawn)
					arr_equity_drawn = np.append(arr_equity_drawn,equity_drawn)

					if i == 0: 
						arr_debt_amount_available = np.append(arr_debt_amount_available,debt_amount)
					else: 
						arr_debt_amount_available = np.append(arr_debt_amount_available,debt_amount_available)

					arr_debt_commitment_fee = np.append(arr_debt_commitment_fee,debt_amount_available*inp_debt_commitment_fee*days_period/360)
					"""arr_debt_repayment = np.append(arr_debt_repayment,0)"""

					arr_debt_EoP = np.append(arr_debt_EoP,cumul_debt_drawn)

					""" XXX """

					arr_depreciation = np.append(arr_depreciation,0)

					arr_years_from_COD_BOP = np.append(arr_years_from_COD_BOP,0)
					arr_years_from_COD_EOP = np.append(arr_years_from_COD_EOP,0)
					arr_degradation = np.append(arr_degradation,0)
					arr_seasonality = np.append(arr_seasonality,0)
					arr_electricity_price = np.append(arr_electricity_price,0)
					arr_days_contract_in_period_pct = np.append(arr_days_contract_in_period_pct,0)
					arr_period_type = np.append(arr_period_type,0)
					arr_pct_year_operations = np.append(arr_pct_year_operations,0)
					arr_opex = np.append(arr_opex,0)
					arr_revenues_merchant = np.append(arr_revenues_merchant,0)
					arr_revenues_contracted = np.append(arr_revenues_contracted,0)

					cumul_year_contract_indexation += create_array_indexation(date_contract_indexation_start,final_date,start_period,end_period)
					"""cumul_year_electricity_price_indexation += create_array_indexation(date_price_elec_indexation_start,final_date,start_period,end_period)
					cumul_year_opex_indexation += create_array_indexation(date_opex_indexation_start,final_date,start_period,end_period)"""
					
					arr_contract_indexation = np.append(arr_contract_indexation,(1+inp_contract_indexation_rate)**cumul_year_contract_indexation)
					"""arr_electricity_price_indexation = np.append(arr_electricity_price_indexation,(1+inp_price_elec_indexation)**cumul_year_electricity_price_indexation)
					arr_opex_indexation = np.append(arr_opex_indexation,(1+inp_opex_indexation_rate)**cumul_year_opex_indexation)"""

					start_period = end_period + datetime.timedelta(days=1)

				""" Operations period """
			
				for i in range(0, int_operating_periods):

					""" Timeline """

					arr_start_period = np.append(arr_start_period,start_period)
					start_period_plus_periodicity = start_period + relativedelta(months=+int(inp_periodicity)-1)
					end_period = min(final_date,start_period_plus_periodicity.replace(day = calendar.monthrange(start_period_plus_periodicity.year, start_period_plus_periodicity.month)[1]))
					arr_end_period = np.append(arr_end_period,end_period)

					days_each_month_year = compute_days_per_month(start_period,end_period)
					arr_seasonality = np.append(arr_seasonality,np.sum(days_each_month_year*seasonality))

					days_period = (end_period + datetime.timedelta(days=1) - start_period).days
					arr_days = np.append(arr_days,days_period)

					days_period_pct_of_operations = days_period/days_in_operation
					arr_depreciation = np.append(arr_depreciation,cumul_construction_costs*days_period_pct_of_operations)

					days_year = 366 if calendar.isleap(end_period.year) else 365
					pct_year = days_period/days_year
					arr_pct_year = np.append(arr_pct_year,pct_year)
					arr_pct_year_operations = np.append(arr_pct_year_operations,pct_year)

					cumul_pct_year = cumul_pct_year + pct_year

					arr_years_from_COD_EOP = np.append(arr_years_from_COD_EOP,cumul_pct_year)
					arr_years_from_COD_BOP = np.append(arr_years_from_COD_BOP,cumul_pct_year-pct_year)
					arr_years_from_COD_avg = np.add(arr_years_from_COD_BOP,arr_years_from_COD_EOP)/2

					days_contract_in_period_pct = create_array_indexation(date_contract_start,date_contract_end,start_period,end_period)/pct_year
					arr_days_contract_in_period_pct = np.append(arr_days_contract_in_period_pct,days_contract_in_period_pct)

					"""cumul_year_contract_indexation += create_array_indexation(date_contract_indexation_start,final_date,start_period,end_period)"""
					"""cumul_year_electricity_price_indexation += create_array_indexation(date_price_elec_indexation_start,final_date,start_period,end_period)
					cumul_year_opex_indexation += create_array_indexation(date_opex_indexation_start,final_date,start_period,end_period)"""
					"""arr_contract_indexation = np.append(arr_contract_indexation,(1+inp_contract_indexation_rate)**cumul_year_contract_indexation)"""

					arr_contract_indexation = np.append(arr_contract_indexation,(1+0.5))
					"""arr_electricity_price_indexation = np.append(arr_electricity_price_indexation,(1+inp_price_elec_indexation)**cumul_year_electricity_price_indexation)
					arr_opex_indexation = np.append(arr_opex_indexation,(1+inp_opex_indexation_rate)**cumul_year_opex_indexation)"""

					""" Senior debt """
					if end_period < date_debt_maturity:
						debt_amortisation = 1
					else: 
						debt_amortisation = 0

					arr_debt_amortisation = np.append(arr_debt_amortisation,debt_amortisation)

					debt_BoP = max(cumul_debt_drawn-cumul_debt_repayment,0)
					arr_debt_BoP = np.append(arr_debt_BoP,debt_BoP)

					arr_debt_amount_available = np.append(arr_debt_amount_available,0)
					arr_debt_commitment_fee = np.append(arr_debt_commitment_fee,0)
					"""arr_debt_drawn = np.append(arr_debt_drawn,0)"""
					arr_debt_interest = np.append(arr_debt_interest,debt_BoP*inp_debt_interest_rate*days_period/360)
					arr_debt_interest_operations = np.append(arr_debt_interest_operations,debt_BoP*inp_debt_interest_rate*days_period/360) 

					debt_repayment = arr_debt_repayment[months_construction+i]
					cumul_debt_repayment += debt_repayment
					"""arr_debt_repayment = np.append(arr_debt_repayment,debt_repayment)"""
					arr_debt_EoP = np.append(arr_debt_EoP,debt_BoP-debt_repayment)
					
					""" XXX """

					start_period = end_period + datetime.timedelta(days=1)
					arr_period_type = np.append(arr_period_type,1)

					""" Production """
					"""arr_degradation = np.append(arr_degradation,1/(1+inp_degradation)**cumul_pct_year)"""

					arr_degradation = np.append(arr_degradation,1/(1+inp_degradation))
					arr_capacity_after_degradation = arr_degradation * inp_capacity

					production = inp_production/1000*arr_capacity_after_degradation*arr_seasonality

					""" Electricity price """

					for key in dic_price_elec.keys():
						if key == str(end_period.year):
							arr_electricity_price = np.append(arr_electricity_price,dic_price_elec[key])

					arr_opex = np.append(arr_opex,inp_opex)

				""" Revenues """
				""" A REMETTRE INDEXATION PRIX ELECTRICITE """
				arr_revenues_contracted = inp_contract_price*arr_contract_indexation*production*arr_days_contract_in_period_pct/1000
				arr_revenues_merchant = arr_electricity_price*1*production*(1-arr_days_contract_in_period_pct)/1000
				arr_revenues_total = np.add(arr_revenues_contracted,arr_revenues_merchant)

				""" Operating costs """
				""" A REMETTRE INDEXATION OPEX"""
				arr_operating_costs = arr_opex*1*arr_pct_year_operations

				""" EBITDA """
				arr_EBITDA = arr_revenues_total-arr_operating_costs
				arr_EBITDA_margin = np.divide(arr_EBITDA,arr_revenues_total, out=np.zeros_like(arr_EBITDA), where=arr_revenues_total!=0)*100
				arr_EBIT = arr_EBITDA-arr_depreciation
				arr_EBT = arr_EBIT-arr_debt_interest_operations
				arr_corpore_tax = -arr_EBT*inp_corporate_income_tax_rate
				arr_net_income = arr_EBT-arr_corpore_tax

				arr_CFADS = (arr_EBIT-arr_corpore_tax)*arr_debt_amortisation
				arr_target_DS_sizing = arr_CFADS/inp_target_DSCR
				arr_target_DS_sculpting = arr_CFADS/DSCR_sculpting

				arr_target_repayment = (arr_target_DS_sculpting-arr_debt_interest_operations)*arr_debt_amortisation
				arr_debt_target_repayment = np.clip(arr_target_repayment,0,a_max=None)

				arr_avg_interest = np.divide(arr_debt_interest_operations,arr_debt_BoP,out=np.zeros_like(arr_debt_interest_operations), where=arr_debt_BoP!=0)/arr_days*360
				arr_period_discount_factor = (1/(1+(arr_avg_interest*arr_days/360)))*arr_debt_amortisation

				for i in range(len(arr_debt_amortisation)):
					if i == 0:
						arr_cumul_period_discount_factor = np.append(arr_cumul_period_discount_factor,1)
					else:
						if arr_debt_amortisation[i] == 1:
							arr_cumul_period_discount_factor = np.append(arr_cumul_period_discount_factor,arr_cumul_period_discount_factor[i-1]*arr_period_discount_factor[i])
						else: 
							arr_cumul_period_discount_factor = np.append(arr_cumul_period_discount_factor,1)

				arr_cumul_period_discount_factor = arr_cumul_period_discount_factor*arr_debt_amortisation

				debt_amount_DSCR = np.dot(arr_target_DS_sizing,arr_cumul_period_discount_factor)
				debt_amount_gearing = cumul_construction_costs
				npv_CFADS = np.dot(arr_CFADS,arr_cumul_period_discount_factor)
				DSCR_sculpting = npv_CFADS/cumul_debt_drawn
				arr_debt_service = (arr_debt_repayment+arr_debt_interest)
				arr_DSCR = np.divide(arr_CFADS,arr_debt_service, out=np.zeros_like(arr_CFADS), where=arr_debt_service!=0)

			arr_debt_BoP = np.round(arr_debt_BoP, decimals=2)
			"""arr_debt_repayment = np.round(arr_debt_repayment, decimals=2)"""
			arr_debt_EoP = np.round(arr_debt_EoP, decimals=2)
			arr_debt_interest = np.round(arr_debt_interest, decimals=2)
			arr_debt_target_repayment = np.round(arr_debt_target_repayment, decimals=2)
			arr_revenues_contracted = np.round(arr_revenues_contracted, decimals=2)
			arr_revenues_merchant = np.round(arr_revenues_merchant, decimals=2)
			arr_revenues_total = np.round(arr_revenues_total, decimals=2)
			arr_EBITDA = np.round(arr_EBITDA, decimals=2)
			arr_depreciation = np.round(arr_depreciation, decimals=2)
			arr_EBIT = np.round(arr_EBIT, decimals=2)
			arr_debt_interest_operations = np.round(arr_debt_interest_operations, decimals=2)
			arr_EBT = np.round(arr_EBT, decimals=2)
			arr_corpore_tax = np.round(arr_corpore_tax, decimals=2)
			arr_net_income = np.round(arr_net_income, decimals=2)


			data_dump_sidebar = np.array([date_COD,final_date,sum_seasonality,sum_construction_costs,date_debt_maturity])
			data_dump_summary = np.array([debt_amount_DSCR,debt_amount,DSCR_sculpting,inp_debt_gearing_max])

			return JsonResponse(
							{
							"BoP":arr_start_period.tolist(),
							"EoP":arr_end_period.tolist(),
							"BoP_FP":arr_start_period_financing_plan.tolist(),
							"EoP_FP":arr_end_period_financing_plan.tolist(),

							"data_dump_sidebar":data_dump_sidebar.tolist(),
							"data_dump_summary":data_dump_summary.tolist(),

							"Operations":arr_period_type.tolist(),
							"seasonality":seasonality.tolist(),
							"arr_seasonality":arr_seasonality.tolist(),
							"arr_days":arr_days.tolist(),
							"Pct arr_pct_year":arr_pct_year.tolist(),
							"Years from COD BoP":arr_years_from_COD_BOP.tolist(),
							"Years from COD EoP":arr_years_from_COD_EOP.tolist(),
							"Years from COD avg":arr_years_from_COD_avg.tolist(),
							"arr_degradation":arr_degradation.tolist(),
							"arr_capacity_after_degradation":arr_capacity_after_degradation.tolist(),
							"arr_seasonality":arr_seasonality.tolist(),
							"production":production.tolist(),
							"arr_days_contract_in_period_pct":arr_days_contract_in_period_pct.tolist(),
							"arr_test":arr_test.tolist(),

							"arr_revenues_contracted":arr_revenues_contracted.tolist(),
							"arr_revenues_merchant":arr_revenues_merchant.tolist(),
							"arr_revenues_total":arr_revenues_total.tolist(),
							"arr_operating_costs":arr_operating_costs.tolist(),
							"arr_EBITDA":arr_EBITDA.tolist(),
							"arr_EBITDA_margin":arr_EBITDA_margin.tolist(),
							"arr_depreciation":arr_depreciation.tolist(),
							"arr_EBIT":arr_EBIT.tolist(),
							"arr_debt_interest_operations":arr_debt_interest_operations.tolist(),
							"arr_EBT":arr_EBT.tolist(),
							"arr_corpore_tax":arr_corpore_tax.tolist(),
							"arr_net_income":arr_net_income.tolist(),

							"arr_construction":arr_construction.tolist(),
							"arr_construction_costs":arr_construction_costs.tolist(),
							"arr_debt_interest_construction":arr_debt_interest_construction.tolist(),

							"arr_CFADS":arr_CFADS.tolist(),
							"arr_target_DS_sizing":arr_target_DS_sizing.tolist(),
							"arr_debt_target_repayment":arr_debt_target_repayment.tolist(),

							"arr_avg_interest":arr_avg_interest.tolist(),
							"arr_period_discount_factor":arr_period_discount_factor.tolist(),
							"arr_cumul_period_discount_factor":arr_cumul_period_discount_factor.tolist(),

							"arr_debt_amount_available":arr_debt_amount_available.tolist(),
							"arr_debt_commitment_fee":arr_debt_commitment_fee.tolist(),
							"arr_debt_BoP":arr_debt_BoP.tolist(),
							"arr_debt_drawn":arr_debt_drawn.tolist(),
							"arr_debt_repayment":arr_debt_repayment.tolist(),
							"arr_debt_EoP":arr_debt_EoP.tolist(),
							"arr_debt_interest":arr_debt_interest.tolist(),
							"arr_DSCR":arr_DSCR.tolist(),
							"arr_debt_service":arr_debt_service.tolist(),


							"arr_equity_drawn":arr_equity_drawn.tolist(),


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
	

def create_array_indexation(start_date_indexation, end_date_indexation, start_period, end_period):

	days_to_index_period = max(0,((min(end_date_indexation,end_period)-max(start_date_indexation,start_period)).days+1))
	days_year = 366 if calendar.isleap(end_period.year) else 365
	year_to_index = days_to_index_period/days_year

	return year_to_index
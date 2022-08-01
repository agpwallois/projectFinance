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
	dates_in_period = compute_days_per_month('2018-01-20', '2018-12-31')
	context={
		'dates_in_period': dates_in_period,
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

			date_COD = end_construction + datetime.timedelta(days=1) 
			final_date = end_construction + relativedelta(years=inp_life) + datetime.timedelta(days=1)

			""" Capacity and Production inputs """

			inp_capacity = int(request.POST['panels_capacity'])				
			inp_degradation = float(request.POST['annual_degradation'])

			inp_p50 = request.POST.get('P50',False)
			inp_p90_10y = int(request.POST['p90_10y'])	
			inp_P99_10y = int(request.POST['P99_10y'])	
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

			inp_costs_m1 = request.POST['end_construction']
			inp_costs_m2 = request.POST['end_construction']
			inp_costs_m3 = request.POST['end_construction']
			inp_costs_m4 = request.POST['end_construction']
			inp_costs_m5 = request.POST['end_construction']
			inp_costs_m6 = request.POST['end_construction']
			inp_costs_m7 = request.POST['end_construction']
			inp_costs_m8 = request.POST['end_construction']
			inp_costs_m9 = request.POST['end_construction']
			inp_costs_m10 = request.POST['end_construction']
			inp_costs_m11 = request.POST['end_construction']
			inp_costs_m12 = request.POST['end_construction']

			r = relativedelta(end_construction,start_period)
			months_construction = (r.years * 12) + r.months + 1
			months_construction = math.ceil(int(months_construction))

			""" Offtake contract and Electricity price inputs """

			inp_contract_start = request.POST['start_contract']
			date_contract_start = datetime.datetime.strptime(inp_contract_start, "%Y-%m-%d").date()

			inp_contract_end = request.POST['end_contract']
			date_contract_end = datetime.datetime.strptime(inp_contract_end, "%Y-%m-%d").date()

			inp_contract_price = float(request.POST['contract_price'])
			inp_contract_indexation_rate = float(request.POST['contract_indexation'])

			inp_contract_indexation_start_date = request.POST['contract_indexation_start_date']
			date_contract_indexation_start = datetime.datetime.strptime(inp_contract_indexation_start_date, "%Y-%m-%d").date()

			inp_price_elec_indexation_start_date = request.POST['price_elec_indexation_start_date']
			date_price_elec_indexation_start = datetime.datetime.strptime(inp_price_elec_indexation_start_date, "%Y-%m-%d").date()

			inp_price_elec_indexation = float(request.POST['price_elec_indexation'])

			arr_years_electricity_prices = create_array_electricity_prices(date_COD)

			price_elec_low = np.array([
			float(request.POST['price_elec_low_y1']),
			float(request.POST['price_elec_low_y2']),
			float(request.POST['price_elec_low_y3']),
			float(request.POST['price_elec_low_y4']),
			float(request.POST['price_elec_low_y5']),
			float(request.POST['price_elec_low_y6']),
			float(request.POST['price_elec_low_y7']),
			float(request.POST['price_elec_low_y8']),
			float(request.POST['price_elec_low_y9']),
			float(request.POST['price_elec_low_y10']),
			float(request.POST['price_elec_low_y11']),
			float(request.POST['price_elec_low_y12']),
			float(request.POST['price_elec_low_y13']),
			float(request.POST['price_elec_low_y14']),
			float(request.POST['price_elec_low_y15']),
			float(request.POST['price_elec_low_y16']),
			float(request.POST['price_elec_low_y17']),
			float(request.POST['price_elec_low_y18']),
			float(request.POST['price_elec_low_y19']),
			float(request.POST['price_elec_low_y20']),
			float(request.POST['price_elec_low_y21']),
			float(request.POST['price_elec_low_y22']),
			float(request.POST['price_elec_low_y23']),
			float(request.POST['price_elec_low_y24']),
			float(request.POST['price_elec_low_y25']),
			float(request.POST['price_elec_low_y26']),
			float(request.POST['price_elec_low_y27']),
			float(request.POST['price_elec_low_y28']),
			float(request.POST['price_elec_low_y29']),
			float(request.POST['price_elec_low_y30']),
			])

			dic_price_elec_medium = {
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

			price_elec_high = np.array([
			float(request.POST['price_elec_high_y1']),
			float(request.POST['price_elec_high_y2']),
			float(request.POST['price_elec_high_y3']),
			float(request.POST['price_elec_high_y4']),
			float(request.POST['price_elec_high_y5']),
			float(request.POST['price_elec_high_y6']),
			float(request.POST['price_elec_high_y7']),
			float(request.POST['price_elec_high_y8']),
			float(request.POST['price_elec_high_y9']),
			float(request.POST['price_elec_high_y10']),
			float(request.POST['price_elec_high_y11']),
			float(request.POST['price_elec_high_y12']),
			float(request.POST['price_elec_high_y13']),
			float(request.POST['price_elec_high_y14']),
			float(request.POST['price_elec_high_y15']),
			float(request.POST['price_elec_high_y16']),
			float(request.POST['price_elec_high_y17']),
			float(request.POST['price_elec_high_y18']),
			float(request.POST['price_elec_high_y19']),
			float(request.POST['price_elec_high_y20']),
			float(request.POST['price_elec_high_y21']),
			float(request.POST['price_elec_high_y22']),
			float(request.POST['price_elec_high_y23']),
			float(request.POST['price_elec_high_y24']),
			float(request.POST['price_elec_high_y25']),
			float(request.POST['price_elec_high_y26']),
			float(request.POST['price_elec_high_y27']),
			float(request.POST['price_elec_high_y28']),
			float(request.POST['price_elec_high_y29']),
			float(request.POST['price_elec_high_y30']),
			])

			""" Arrays instanciation """

			arr_start_period = np.array([])
			arr_end_period = np.array([])
			arr_period_type = np.array([])

			arr_period_type = np.array([])
			arr_days = np.array([])
			arr_pct_year = np.array([])
			arr_years_from_COD_BOP = np.array([])
			arr_years_from_COD_EOP = np.array([])
			pct_year_cumul = 0

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

			cumul_year_contract_indexation = 0
			cumul_year_electricity_price_indexation = 0

	
			""" Construction period """

			for i in range(0, months_construction):
				arr_start_period = np.append(arr_start_period,start_period)
				end_period = min(end_construction,start_period.replace(day = calendar.monthrange(start_period.year, start_period.month)[1]))
				arr_end_period = np.append(arr_end_period,end_period)



				days_period = (end_period + datetime.timedelta(days=1) - start_period).days
				arr_days = np.append(arr_days,days_period)
				
				days_year = 366 if calendar.isleap(end_period.year) else 365
				arr_pct_year = np.append(arr_pct_year,days_period/days_year)

				arr_years_from_COD_BOP = np.append(arr_years_from_COD_BOP,0)
				arr_years_from_COD_EOP = np.append(arr_years_from_COD_EOP,0)
				arr_degradation = np.append(arr_degradation,0)
				arr_seasonality = np.append(arr_seasonality,0)
				arr_electricity_price = np.append(arr_electricity_price,0)
				arr_days_contract_in_period_pct = np.append(arr_days_contract_in_period_pct,0)
				arr_period_type = np.append(arr_period_type,0)


				cumul_year_contract_indexation += create_array_indexation(date_contract_indexation_start,final_date,start_period,end_period)
				cumul_year_electricity_price_indexation += create_array_indexation(date_price_elec_indexation_start,final_date,start_period,end_period)

				arr_contract_indexation = np.append(arr_contract_indexation,(1+inp_contract_indexation_rate)**cumul_year_contract_indexation)
				arr_electricity_price_indexation = np.append(arr_electricity_price_indexation,(1+inp_price_elec_indexation)**cumul_year_electricity_price_indexation)


				start_period = end_period + datetime.timedelta(days=1)

			""" Operations period """
			
			int_operating_periods = math.ceil(int(inp_life)*12/int(inp_periodicity)+1)

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

				days_year = 366 if calendar.isleap(end_period.year) else 365
				pct_year = days_period/days_year
				arr_pct_year = np.append(arr_pct_year,pct_year)

				pct_year_cumul = pct_year_cumul + pct_year



				arr_years_from_COD_EOP = np.append(arr_years_from_COD_EOP,pct_year_cumul)
				arr_years_from_COD_BOP = np.append(arr_years_from_COD_BOP,pct_year_cumul-pct_year)
				arr_years_from_COD_avg = np.add(arr_years_from_COD_BOP,arr_years_from_COD_EOP)/2


				days_contract_in_period_pct = create_array_indexation(date_contract_start,date_contract_end,start_period,end_period)/pct_year
				arr_days_contract_in_period_pct = np.append(arr_days_contract_in_period_pct,days_contract_in_period_pct)

				cumul_year_contract_indexation += create_array_indexation(date_contract_indexation_start,final_date,start_period,end_period)
				cumul_year_electricity_price_indexation += create_array_indexation(date_price_elec_indexation_start,final_date,start_period,end_period)

				arr_contract_indexation = np.append(arr_contract_indexation,(1+inp_contract_indexation_rate)**cumul_year_contract_indexation)
				arr_electricity_price_indexation = np.append(arr_electricity_price_indexation,(1+inp_price_elec_indexation)**cumul_year_electricity_price_indexation)
				
				start_period = end_period + datetime.timedelta(days=1)
				arr_period_type = np.append(arr_period_type,1)

				""" Production """

				arr_degradation = np.append(arr_degradation,1/(1+inp_degradation/100)**pct_year_cumul)
				arr_capacity_after_degradation = arr_degradation * inp_capacity

				production = np.multiply(arr_capacity_after_degradation,arr_seasonality)*inp_p90_10y*10**-3

				""" Electricity price """

				for key in dic_price_elec_medium.keys():
					if key == str(end_period.year):
						arr_electricity_price = np.append(arr_electricity_price,dic_price_elec_medium[key])

				""" Revenues """

			arr_revenues_contracted = np.multiply(production,arr_days_contract_in_period_pct)
			arr_revenues_contracted = np.multiply(arr_revenues_contracted,arr_contract_indexation)*inp_contract_price/1000
			
			arr_revenues_merchant = np.multiply(production,1-arr_days_contract_in_period_pct)
			arr_revenues_merchant = np.multiply(arr_revenues_merchant,arr_electricity_price)
			arr_revenues_merchant = np.multiply(arr_revenues_merchant,arr_electricity_price_indexation)/1000

			arr_revenues_total = np.add(arr_revenues_contracted,arr_revenues_merchant)


			data_dump_sidebar = np.array([date_COD,final_date,sum_seasonality,])
			
			return JsonResponse(
							{
							"BoP":arr_start_period.tolist(),
							"EoP":arr_end_period.tolist(),
							"data_dump_sidebar":data_dump_sidebar.tolist(),
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

							"arr_years_electricity_prices":arr_years_electricity_prices.tolist(),
							"arr_electricity_price":arr_electricity_price.tolist(),

							"arr_contract_indexation":arr_contract_indexation.tolist(),
							"arr_electricity_price_indexation":arr_electricity_price_indexation.tolist(),

							"arr_revenues_contracted":arr_revenues_contracted.tolist(),
							"arr_revenues_merchant":arr_revenues_merchant.tolist(),



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
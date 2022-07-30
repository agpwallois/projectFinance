from django.http import JsonResponse
from django.http.response import HttpResponse

from django.views.generic import ListView

from django.shortcuts import render, redirect
from .forms import ProjectForm, TimelineForm, ProductionForm, ConstructionForm, RevenuesForm
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

			inp_construction_start = request.POST['start_construction']
			inp_construction_end = request.POST['end_construction']
			inp_life = int(request.POST['operating_life'])
			inp_periodicity = int(request.POST['periodicity'])

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

			inp_contract_start = request.POST['start_contract']
			inp_contract_end = request.POST['end_contract']
			inp_contract_price = request.POST['contract_price']
			inp_contract_indexation_start_date = request.POST['contract_indexation_start_date']
			inp_contract_indexation_rate = float(request.POST['contract_indexation'])

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



			start_period = datetime.datetime.strptime(inp_construction_start, "%Y-%m-%d").date()
			end_construction = datetime.datetime.strptime(inp_construction_end, "%Y-%m-%d").date()
			date_contract_start = datetime.datetime.strptime(inp_contract_start, "%Y-%m-%d").date()
			date_contract_end = datetime.datetime.strptime(inp_contract_end, "%Y-%m-%d").date()
			date_contract_indexation_start = datetime.datetime.strptime(inp_contract_indexation_start_date, "%Y-%m-%d").date()


			r = relativedelta(end_construction,start_period)
			months_construction = (r.years * 12) + r.months + 1
			months_construction = math.ceil(int(months_construction))

			final_date = end_construction + relativedelta(years=inp_life) + datetime.timedelta(days=1)

## CONSTRUCTION ##
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

				arr_days_contract_in_period_pct = np.append(arr_days_contract_in_period_pct,0)

				arr_contract_indexation = np.append(arr_contract_indexation,0)



				start_period = end_period + datetime.timedelta(days=1)
				arr_period_type = np.append(arr_period_type,0)

## OPERATIONS ##
			int_operating_periods = math.ceil(int(inp_life)*12/int(inp_periodicity)+1)

			for i in range(0, int_operating_periods):

			### Timeline ###
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

				days_contract_in_period = max(0,((min(date_contract_end,end_period)-max(date_contract_start,start_period)).days+1))
				days_contract_in_period_pct = days_contract_in_period/days_period
				arr_days_contract_in_period_pct = np.append(arr_days_contract_in_period_pct,days_contract_in_period_pct)
				
				start_period = end_period + datetime.timedelta(days=1)
				arr_period_type = np.append(arr_period_type,1)

				arr_contract_indexation = np.append(arr_contract_indexation,(1+inp_contract_indexation_rate)**(days_contract_in_period/days_year))

			### Production ###

				arr_degradation = np.append(arr_degradation,1/(1+inp_degradation/100)**pct_year_cumul)
				arr_capacity_after_degradation = arr_degradation * inp_capacity

				production = np.multiply(arr_capacity_after_degradation,arr_seasonality)*inp_p90_10y*10**-3

			### Electricity price ###

				"""arr_contract_indexation = np.append(arr_contract_indexation,max(0,end_period-date_contract_start))"""

			
			return JsonResponse(
							{
							"BoP":arr_start_period.tolist(),
							"EoP":arr_end_period.tolist(),
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
							"arr_contract_indexation":arr_contract_indexation.tolist(),
							"arr_contract_indexation":arr_contract_indexation.tolist(),
							"arr_contract_indexation":arr_contract_indexation.tolist(),
							"arr_contract_indexation":arr_contract_indexation.tolist(),
							"arr_contract_indexation":arr_contract_indexation.tolist(),

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
	


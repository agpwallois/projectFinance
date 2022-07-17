from django.http import JsonResponse
from django.http.response import HttpResponse

from django.views.generic import ListView

from django.shortcuts import render, redirect
from .forms import SProjectForm, TimelineForm, ProductionForm, ConstructionForm, RevenuesForm, OpexForm
from .models import SProject

import calendar
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta

import math

import pandas as pd
import numpy as np
from django.core import serializers


class ProjectView(ListView):
	model = SProject
	template_name = 'project_list.html'
	context_object_name = "projects"

def Viewdata(request):
	return render(request, 'project_view.html')

def income_statement(valeurinitiale):
	revenues_real = np.array([])

	for i in range(1,10): 
		revenues_real = np.append(valeurinitiale)

	m=[
	revenues_real,
	revenues_real,
	]

	return m

def project_view(request,id):
	timeline_form = TimelineForm()
	production_form = ProductionForm()
	construction_form = ConstructionForm()
	revenues_form = RevenuesForm()
	opex_form = OpexForm()

	Sproject = SProject.objects.get(id=id)

	if request.method == "POST":
		timeline_form = TimelineForm(request.POST, instance=Sproject)
		production_form = ProductionForm(request.POST, instance=Sproject)
		construction_form = ConstructionForm(request.POST, instance=Sproject)
		revenues_form = RevenuesForm(request.POST, instance=Sproject)
		opex_form = OpexForm(request.POST, instance=Sproject)

		if timeline_form.is_valid() and production_form.is_valid() and construction_form.is_valid() and revenues_form.is_valid() and opex_form.is_valid():
			timeline_form.save()
			production_form.save()
			construction_form.save()
			revenues_form.save()
			opex_form.save()

			inp_construction_start = request.POST['start_construction']
			inp_construction_end = request.POST['end_construction']
			inp_life = int(request.POST['operating_life'])
			inp_periodicity = request.POST['periodicity']

			inp_capacity = int(request.POST['panels_capacity'])				
			inp_degradation = int(request.POST['annual_degradation'])

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

			inp_revenues = request.POST['revenues']
			inp_inflation = request.POST['inflation']
			inp_opex = request.POST['opex']

			arr_start_period = np.array([])
			arr_end_period = np.array([])
			arr_period_type = np.array([])

			arr_period_type = np.array([])
			arr_days = np.array([])
			arr_pct_year = np.array([])
			arr_years_from_COD_BOP = np.array([])
			arr_years_from_COD_EOP = np.array([])
			pct_year_cumul = 0



			arr_degradation = np.array([])
			arr_capacity_after_degradation = np.array([])


			start_period = datetime.datetime.strptime(str(inp_construction_start), "%Y-%m-%d").date()
			end_construction = datetime.datetime.strptime(str(inp_construction_end), "%Y-%m-%d").date()

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
				
				days_period = (end_period + datetime.timedelta(days=1) - start_period).days
				arr_days = np.append(arr_days,days_period)
				
				days_year = 366 if calendar.isleap(end_period.year) else 365
				pct_year = days_period/days_year
				arr_pct_year = np.append(arr_pct_year,pct_year)
				pct_year_cumul = pct_year_cumul + pct_year
				arr_years_from_COD_EOP = np.append(arr_years_from_COD_EOP,pct_year_cumul)
				arr_years_from_COD_BOP = np.append(arr_years_from_COD_BOP,pct_year_cumul-pct_year)
				arr_years_from_COD_avg = np.add(arr_years_from_COD_BOP,arr_years_from_COD_EOP)/2


				start_period = end_period + datetime.timedelta(days=1)
				arr_period_type = np.append(arr_period_type,1)

			### Production ###

				arr_degradation = np.append(arr_degradation,1/(1+inp_degradation/100)**pct_year_cumul)
				arr_capacity_after_degradation = arr_degradation * inp_capacity





			"""arr_timeline = np.array([])
			arr_revenues_real = np.array([])
			arr_inflation = np.array([])
			arr_revenues_nom = np.array([])
			arr_opex_real = np.array([])
			arr_opex_nom = np.array([])
			arr_ebitda = np.array([])"""

			"""for i in range(0,):
				arr_timeline = np.append(arr_timeline,int(inp_start_year)+i)
				arr_revenues_real = np.append(arr_revenues_real,int(inp_revenues))
				arr_inflation = np.append(arr_inflation,(1+float(inp_inflation)/100)**(i+1))
				arr_opex_real = np.append(arr_opex_real,int(inp_opex))

			arr_revenues_nom = np.multiply(arr_revenues_real, arr_inflation)
			arr_opex_nom = np.multiply(arr_opex_real, arr_inflation)
			arr_ebitda = np.subtract(arr_revenues_nom, arr_opex_nom)"""

			arr_start_period = arr_start_period.tolist()
			arr_end_period = arr_end_period.tolist()
			arr_period_type = arr_period_type.tolist()
			arr_days = arr_days.tolist()
			arr_pct_year = arr_pct_year.tolist()
			arr_years_from_COD_BOP = arr_years_from_COD_BOP.tolist()
			arr_years_from_COD_EOP = arr_years_from_COD_EOP.tolist()
			arr_years_from_COD_avg = arr_years_from_COD_avg.tolist()
			arr_degradation = arr_degradation.tolist()
			arr_capacity_after_degradation = arr_capacity_after_degradation.tolist()


			"""arr_timeline = arr_timeline.tolist()
			arr_inflation = np.around(arr_inflation, decimals=3).tolist()
			arr_revenues_nom = np.around(arr_revenues_nom, decimals=2).tolist()			
			arr_opex_nom = np.around(arr_opex_nom, decimals=2).tolist()
			arr_ebitda = np.around(arr_ebitda, decimals=2).tolist()"""
			
			return JsonResponse(
							{
							"BoP":arr_start_period,
							"EoP":arr_end_period,
							"Operations":arr_period_type,
							"Days":arr_days,
							"Pct year":arr_pct_year,
							"Years from COD BoP":arr_years_from_COD_BOP,
							"Years from COD EoP":arr_years_from_COD_EOP,
							"Years from COD avg":arr_years_from_COD_avg,
							"arr_degradation":arr_degradation,
							"arr_capacity_after_degradation":arr_capacity_after_degradation,



						},safe=False, status=200)
		else:
			errors = timeline_form.errors.as_json()
			return JsonResponse({"errors": errors}, status=400)

	else:
		timeline_form = TimelineForm(instance=Sproject)
		construction_form = ConstructionForm(instance=Sproject)
		revenues_form = RevenuesForm(instance=Sproject)
		opex_form = OpexForm(instance=Sproject)

	context={
		'timeline_form': timeline_form,
		'production_form': production_form,
		'construction_form': construction_form,
		'revenues_form': revenues_form,
		'Sproject':Sproject,
		'opex_form':opex_form,
		}
	
	return render(request, "project_view.html", context)
	

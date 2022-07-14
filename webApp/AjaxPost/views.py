from django.http import JsonResponse
from django.http.response import HttpResponse

from django.views.generic import ListView

from django.shortcuts import render, redirect
from .forms import SProjectForm, TimelineForm, ConstructionForm, RevenuesForm, OpexForm
from .models import SProject

import calendar
import datetime

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
	construction_form = ConstructionForm()
	revenues_form = RevenuesForm()
	opex_form = OpexForm()
	Sproject = SProject.objects.get(id=id)

	if request.method == "POST":
		timeline_form = TimelineForm(request.POST, instance=Sproject)
		construction_form = ConstructionForm(request.POST, instance=Sproject)
		revenues_form = RevenuesForm(request.POST, instance=Sproject)
		opex_form = OpexForm(request.POST, instance=Sproject)

		if timeline_form.is_valid() and construction_form.is_valid() and revenues_form.is_valid() and opex_form.is_valid():
			timeline_form.save()
			construction_form.save()
			revenues_form.save()
			opex_form.save()

			inp_construction_start = request.POST['start_construction']
			inp_construction_end = request.POST['end_construction']

			inp_start_year = request.POST['start_year']
			inp_length = request.POST['length']
			inp_periodicity = request.POST['periodicity']

			inp_revenues = request.POST['revenues']
			inp_inflation = request.POST['inflation']
			inp_opex = request.POST['opex']

			arr_start_period = np.array([])
			arr_end_period = np.array([])
			arr_days = np.array([])

			start_period = datetime.datetime.strptime(str(inp_construction_start), "%Y-%m-%d").date()

			for i in range(0, 3):
				arr_start_period = np.append(arr_start_period,start_period)
				end_period = start_period.replace(day = calendar.monthrange(start_period.year, start_period.month)[1])
				arr_end_period = np.append(arr_end_period,end_period)
				arr_days = np.append(arr_days,(end_period + datetime.timedelta(days=1) - start_period).days)
				start_period = end_period + datetime.timedelta(days=1)

			arr_start_period = np.append(arr_start_period,start_period)
			end_period = datetime.datetime.strptime(str(inp_construction_end), "%Y-%m-%d").date()
			arr_end_period = np.append(arr_end_period,end_period)
			arr_days = np.append(arr_days,(end_period + datetime.timedelta(days=1) - start_period).days)
			start_period = end_period + datetime.timedelta(days=1)


			for i in range(0, 5):
				arr_start_period = np.append(arr_start_period,start_period)
				end_period = start_period.replace(day = calendar.monthrange(start_period.year, start_period.month)[1])
				arr_end_period = np.append(arr_end_period,end_period)
				arr_days = np.append(arr_days,(end_period + datetime.timedelta(days=1) - start_period).days)
				start_period = end_period + datetime.timedelta(days=1)




			arr_timeline = np.array([])
			arr_revenues_real = np.array([])
			arr_inflation = np.array([])
			arr_revenues_nom = np.array([])
			arr_opex_real = np.array([])
			arr_opex_nom = np.array([])
			arr_ebitda = np.array([])

			for i in range(0,int(inp_length)):
				arr_timeline = np.append(arr_timeline,int(inp_start_year)+i)
				arr_revenues_real = np.append(arr_revenues_real,int(inp_revenues))
				arr_inflation = np.append(arr_inflation,(1+float(inp_inflation)/100)**(i+1))
				arr_opex_real = np.append(arr_opex_real,int(inp_opex))

			arr_revenues_nom = np.multiply(arr_revenues_real, arr_inflation)
			arr_opex_nom = np.multiply(arr_opex_real, arr_inflation)
			arr_ebitda = np.subtract(arr_revenues_nom, arr_opex_nom)

			arr_start_period = arr_start_period.tolist()
			arr_end_period = arr_end_period.tolist()
			arr_days = arr_days.tolist()

			arr_timeline = arr_timeline.tolist()
			arr_inflation = np.around(arr_inflation, decimals=3).tolist()
			arr_revenues_nom = np.around(arr_revenues_nom, decimals=2).tolist()			
			arr_opex_nom = np.around(arr_opex_nom, decimals=2).tolist()
			arr_ebitda = np.around(arr_ebitda, decimals=2).tolist()
			
			return JsonResponse(
							{
							"Start of period":arr_start_period,
							"End of period":arr_end_period,
							"Days":arr_days,
							"Year":arr_timeline,
							"Inflation":arr_inflation,
							"Revenues":arr_revenues_nom,
							"Opex":arr_opex_nom,
							"EBITDA":arr_ebitda,
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
		'construction_form': construction_form,
		'revenues_form': revenues_form,
		'Sproject':Sproject,
		'opex_form':opex_form,
		}
	
	return render(request, "project_view.html", context)
	

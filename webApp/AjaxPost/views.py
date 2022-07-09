from django.http import JsonResponse
from django.http.response import HttpResponse

from django.shortcuts import render, redirect
from .forms import SProjectForm, TimelineForm, RevenuesForm
from .models import SProject

import pandas as pd
import numpy as np
from django.core import serializers


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
	revenues_form = RevenuesForm()
	Sproject = SProject.objects.get(id=id)

	if request.method == "POST":
		timeline_form = TimelineForm(request.POST, instance=Sproject)
		revenues_form = RevenuesForm(request.POST, instance=Sproject)

		if timeline_form.is_valid() and revenues_form.is_valid():
			timeline_form.save()
			revenues_form.save()

			inp_start_year = request.POST['start_year']
			inp_length = request.POST['length']
			"""inp_periodicity = request.POST['periodicity']"""
			inp_revenues = request.POST['revenues']
			"""inp_inflation = request.POST['inflation']"""
			"""inp_opex = request.POST['opex']"""

			arr_timeline = np.array([])
			arr_revenues_real = np.array([])

			for i in range(1,int(inp_length)):
				arr_timeline = np.append(arr_timeline,int(inp_start_year)+i)
				arr_revenues_real = np.append(arr_revenues_real,int(inp_revenues))

			arr_timeline = arr_timeline.tolist()
			arr_revenues_real = arr_revenues_real.tolist()

			"""test = income_statement(revenues_initial)"""

			resp = [arr_timeline]
			
			return JsonResponse(
							{
							"Year":arr_timeline,
							"Revenues":arr_revenues_real
						},safe=False, status=200)
		else:
			errors = timeline_form.errors.as_json()
			return JsonResponse({"errors": errors}, status=400)

	else:
		timeline_form = TimelineForm(instance=Sproject)
		revenues_form = RevenuesForm(instance=Sproject)



	"""income_statement = Sproject.income_statement()"""

	context={
		'timeline_form': timeline_form,
		'revenues_form': revenues_form,
		'Sproject':Sproject,
		'income_statement':income_statement,
		}
	
	return render(request, "project_view.html", context)
	

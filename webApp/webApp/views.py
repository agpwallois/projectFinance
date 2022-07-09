from django.http import HttpResponse
from django.shortcuts import render, redirect
from webApp.models import Project
from webApp.models import webApp
from webApp.forms import ProjectForm, TimelineForm, RevenuesForm, OpexForm
from django.views.generic import ListView
import pandas as pd
from tabulate import tabulate

class ProjectView(ListView):
	model = Project
	template_name = 'project_list.html'
	context_object_name = "projects"

def project_detail(request, id): 
	project = Project.objects.get(id=id)

	income_statement = project.income_statement()
	income_statement_df = pd.DataFrame(income_statement,index= ["Year", "Date", "Inflation", "Revenues (real)","Revenues (nominal)","Operating expenses","EBITDA"])

	styler = income_statement_df.style
	styler = styler.hide(axis='columns')

	styler = styler.format(formatter="{:.0f}", subset=pd.IndexSlice[['Year', 'Date'], :])
	styler = styler.format(formatter="{:.1f}", subset=pd.IndexSlice[['Revenues (real)','Revenues (nominal)','Operating expenses','EBITDA'], :])
	styler = styler.format(formatter="{:.2f}", subset=pd.IndexSlice[['Inflation'], :])

	index = {'selector': 'th.row_heading', 'props': 
	         [('background-color', '#ffff'), 
	         ('color', '#3B454E'), 
	         ('text-align', 'left'),
	         ('font-size', '12px'),
	         ('padding-left', '10px'),
	         ('padding-right', '10px')]}

	table = {'selector': 'td', 'props': 
	         [('text-align', 'center'),
	         ('font-size', '12px'),
	         ('padding-left', '10px'),
	         ('padding-right', '10px')]}

	styler = styler.set_table_styles([index,table])

	income_statement_df = styler.to_html()

	if request.method == 'POST':
		form_project = ProjectForm(request.POST, instance=project)
		if form_project.is_valid():
			form_project.save()
			return redirect('project-detail', project.id)
	
	else:
		form_project = ProjectForm(instance=project)


	if request.method == 'POST':
		form_time = TimelineForm(request.POST, instance=project)
		if form_time.is_valid():
			form_time.save()
			return redirect('project-detail', project.id)
	
	else:
		form_time = TimelineForm(instance=project)


	if request.method == 'POST':
		form_rev = RevenuesForm(request.POST, instance=project)
		if form_rev.is_valid():
			form_rev.save()
			return redirect('project-detail', project.id)
	
	else:
		form_rev = RevenuesForm(instance=project)


	if request.method == 'POST':
		form_opex = OpexForm(request.POST, instance=project)
		if form_opex.is_valid():
			form_opex.save()
			return redirect('project-detail', project.id)
	
	else:
		form_opex = OpexForm(instance=project)

	context={
		'project': project,
		'form_project':form_project,
		'form_time':form_time,
		'form_rev':form_rev,
		'form_opex':form_opex,
		'income_statement': income_statement,
		'income_statement_df': income_statement_df,
		}

	return render(request, 'webApp/project_detail.html', context)


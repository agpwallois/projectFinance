import json
from collections import defaultdict

from django.db.models import Count, Sum, Case, When, Value, IntegerField, F
from django.shortcuts import render

from financial_model.model_project import Project
from financial_model.model_financial_model import FinancialModel
from financial_model.model_solar_financial_model import SolarFinancialModel
from financial_model.model_wind_financial_model import WindFinancialModel


def projects_dashboard(request):
	projects = get_projects()
	financial_models = get_financial_models()

	project_counts_tech, project_counts_country = calculate_project_counts()

	capacity_per_tech = calculate_capacity('technology')
	capacity_per_country = calculate_capacity('country')

	assign_calculated_value_to_projects(projects)

	project_data = get_project_data(projects)

	yearly_revenues_technology, yearly_revenues_country = calculate_yearly_revenues(projects)

	context = {
		'projects': projects,
		'financial_models': financial_models,

		'project_counts_tech': project_counts_tech,
		'project_counts_country': project_counts_country,
		'capacity_per_tech': capacity_per_tech,
		'capacity_per_country': capacity_per_country,
		'project_data': project_data,
		'yearly_revenues_technology': yearly_revenues_technology,
		'yearly_revenues_country': yearly_revenues_country,
	}

	return render(request, 'dashboard/projects_list.html', context)


def get_projects():
	return Project.objects.all()

def get_financial_models():
	return FinancialModel.objects.all()

def calculate_project_counts():
	tech_counts = Project.objects.values('technology').annotate(total_projects=Count('id'))
	country_counts = Project.objects.values('country').annotate(total_projects=Count('id'))
	return tech_counts, country_counts

def calculate_capacity(filter_by):
	return Project.objects.filter(project_status='Development').values(filter_by).annotate(
		total_capacity=Sum(
			Case(
				When(technology='Wind', then=F('wind_turbine_installed') * F('capacity_per_turbine') * 1000),
				default=F('panels_capacity'),
				output_field=IntegerField(),
			)
		)
	)

def assign_calculated_value_to_projects(projects):
	for project in projects:
		if project.technology == 'Wind':
			project.calculated_value = project.wind_turbine_installed * project.capacity_per_turbine * 1000
		else:
			project.calculated_value = project.panels_capacity

def get_project_data(projects):
	project_data = {}
	for project in projects:
		try:
			sponsor_result = SolarFinancialModel.objects.get(
				project=project, identifier='sponsor_production_choice'
			).financial_model
			project_data[project.id] = sponsor_result
		except SolarFinancialModel.DoesNotExist:
			project_data[project.id] = None
	return project_data

def calculate_yearly_revenues(projects):
	technology_yearly_total_revenues_sum = defaultdict(lambda: defaultdict(int))
	country_yearly_total_revenues_sum = defaultdict(lambda: defaultdict(int))

	for project in projects:
		try:
			sponsor_result = SolarFinancialModel.objects.get(
				project=project, identifier='sponsor_production_choice'
			).financial_model

			technology = project.technology
			country = project.country

			years = sponsor_result['time_series']['series_end_period_year']
			revenues = sponsor_result['revenues']['total']

			for year_str in years:
				year = int(year_str)
				current_sum = revenues[years.index(year_str)] if year_str in years else 0

				technology_yearly_total_revenues_sum[technology][year] += current_sum
				country_yearly_total_revenues_sum[country][year] += current_sum

		except SolarFinancialModel.DoesNotExist:
			continue

	yearly_revenues_technology = json.dumps(technology_yearly_total_revenues_sum)
	yearly_revenues_country = json.dumps(country_yearly_total_revenues_sum)

	return yearly_revenues_technology, yearly_revenues_country

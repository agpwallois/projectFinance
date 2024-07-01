import json
from collections import defaultdict

from django.db.models import Count, Sum, Case, When, Value, IntegerField, F
from django.shortcuts import render

from financial_model.models import Project, SponsorCaseResult



def projects_dashboard(request):
	projects = Project.objects.all()
	project_data = {}
	
	project_counts_tech = Project.objects.values('technology').annotate(total_projects=Count('id'))
	project_counts_country = Project.objects.values('country').annotate(total_projects=Count('id'))


	capacity_per_tech = Project.objects.filter(financial_close_check=False).values('technology').annotate(
		total_capacity=Sum(
			Case(
				When(technology='Wind', then=F('wind_turbine_installed') * F('capacity_per_turbine') * 1000),
				default=F('panels_capacity'),
				output_field=IntegerField(),
			)
		)
	)

	capacity_per_country = Project.objects.filter(financial_close_check=False).values('country').annotate(
		total_capacity=Sum(
			Case(
				When(technology='Wind', then=F('wind_turbine_installed') * F('capacity_per_turbine') * 1000),
				default=F('panels_capacity'),
				output_field=IntegerField(),
			)
		)
	)

	for project in projects:
		if project.technology == 'Wind':
			project.calculated_value = project.wind_turbine_installed * project.capacity_per_turbine * 1000
		else:
			project.calculated_value = project.panels_capacity


	for project in projects:
		try:
			sponsor_result = SponsorCaseResult.objects.get(project=project).sponsor_case_result
			project_data[project.id] = sponsor_result
		except SponsorCaseResult.DoesNotExist:
			# Handle the case where computed data doesn't exist for a project
			project_data[project.id] = None


	technology_yearly_total_revenues_sum = defaultdict(dict)
	country_yearly_total_revenues_sum = defaultdict(dict)

	for project in projects:
		try:
			sponsor_result = SponsorCaseResult.objects.get(project=project).sponsor_case_result
			technology = project.technology
			country = project.country

			for year, value in sponsor_result['Dates']['Period end'].items():
				year = int(year)

				current_sum = sponsor_result['IS']['Total revenues'].get(str(year), 0)

				technology_yearly_total_revenues_sum[technology][year] = \
				technology_yearly_total_revenues_sum[technology].get(year, 0) + current_sum

				country_yearly_total_revenues_sum[country][year] = \
				country_yearly_total_revenues_sum[country].get(year, 0) + current_sum

		except SponsorCaseResult.DoesNotExist:
			pass
	

	yearly_revenues_technology = json.dumps(technology_yearly_total_revenues_sum)
	yearly_revenues_country = json.dumps(country_yearly_total_revenues_sum)



	context = {'projects': projects,
				'project_counts_tech': project_counts_tech,
				'project_counts_country': project_counts_country,
				'capacity_per_tech': capacity_per_tech,
				'capacity_per_country': capacity_per_country,
				'project_data': project_data,
				'yearly_revenues_technology': yearly_revenues_technology,
				'yearly_revenues_country': yearly_revenues_country,
			
	}


	return render(request, 'dashboard/projects_list.html', context)

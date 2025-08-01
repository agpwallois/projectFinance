import json
from collections import defaultdict

from django.db.models import Count, Sum, Case, When, Value, IntegerField, F
from django.shortcuts import render, redirect

from financial_model.model_project import Project
from financial_model.model_fm import FinancialModel
from financial_model.model_solar_fm import SolarFinancialModel
from financial_model.model_wind_fm import WindFinancialModel
import logging
from django.contrib.auth.decorators import login_required
from authentication.utils import get_user_company
from django.contrib import messages

logger = logging.getLogger(__name__)

@login_required
def projects_dashboard(request):
	company = get_user_company(request.user)
	if not company:
		messages.error(request, 'Your account is not associated with any company.')
		return redirect('logout')
	
	projects = get_projects(company)
	financial_models = get_financial_models()

	project_counts_tech, project_counts_country = calculate_project_counts(projects)

	capacity_in_development_per_tech = calculate_capacity_in_development(projects, 'technology')
	capacity_in_development_per_country = calculate_capacity_in_development(projects, 'country')

	total_capacity_in_operations = calculate_capacity_in_operations(projects)
	total_valuation_in_operations = calculate_valuation_in_operations(projects)

	lowest_project_IRR_in_development = get_lowest_irr_project(projects, 'Development')
	highest_project_IRR_in_development = get_highest_irr_development_project(projects)
	lowest_project_IRR_in_operations = get_lowest_irr_project(projects, 'Operational')

	assign_calculated_value_to_projects(projects)

	project_data = get_project_data(projects)

	yearly_revenues_technology, yearly_revenues_country = calculate_yearly_revenues(projects)

	"""logger.error(yearly_revenues_technology)
	logger.error(yearly_revenues_country)"""

	projects_in_development = projects.filter(project_status="Development")
	projects_in_operations = projects.filter(project_status="Operational")

	total_capacity_in_development = capacity_in_development_per_tech.aggregate(Sum('total_capacity'))['total_capacity__sum']

	context = {
		'projects': projects,

		'projects_in_development': projects_in_development,
		'projects_in_operations': projects_in_operations,
		
		'total_capacity_in_development': total_capacity_in_development,
		'total_capacity_in_operations': total_capacity_in_operations,

		'total_valuation_in_operations': total_valuation_in_operations,

		'lowest_project_IRR_in_development': lowest_project_IRR_in_development,
		'highest_project_IRR_in_development': highest_project_IRR_in_development,
		'lowest_project_IRR_in_operations': lowest_project_IRR_in_operations,

		'financial_models': financial_models,

		'project_counts_tech': project_counts_tech,
		'project_counts_country': project_counts_country,

		'capacity_in_development_per_tech': capacity_in_development_per_tech,
		'capacity_in_development_per_country': capacity_in_development_per_country,

		'project_data': project_data,
		'yearly_revenues_technology': yearly_revenues_technology,
		'yearly_revenues_country': yearly_revenues_country,
	}

	return render(request, 'dashboard/projects_list.html', context)


@login_required
def create_project(request):
	company = get_user_company(request.user)
	
	if not company:
		messages.error(request, 'Your account is not associated with any company.')
		return redirect('logout')
	
	if request.method == 'POST':
		name = request.POST.get('name')
		technology = request.POST.get('technology') 
		country = request.POST.get('country')
		
		# Validation simple
		if not name or not technology or not country:
			messages.error(request, 'All fields are required.')
			return render(request, 'dashboard/create_project.html', {'company': company})
		
		# Créer le projet
		project = Project.objects.create(
			company=company,
			creator=request.user,
			name=name,
			technology=technology,
			country=country
		)
		
		return redirect('project_list')
	
	return render(request, 'dashboard/create_project.html', {'company': company})


@login_required
def delete_project(request):
	"""View for deleting projects."""
	company = get_user_company(request.user)
	
	if not company:
		messages.error(request, 'Your account is not associated with any company.')
		return redirect('logout')
	
	if request.method == 'POST':
		# Get selected project IDs from the form
		project_ids = request.POST.getlist('project_ids')
		
		if not project_ids:
			messages.error(request, 'No projects selected for deletion.')
			return redirect('delete_project')
		
		try:
			# Get projects that belong to the user's company
			projects_to_delete = Project.objects.filter(
				id__in=project_ids,
				company=company
			)
			
			# Check if all selected projects belong to the user's company
			if len(projects_to_delete) != len(project_ids):
				messages.error(request, 'You can only delete projects from your own company.')
				return redirect('delete_project')
			
			# Get project names for the success message
			deleted_project_names = list(projects_to_delete.values_list('name', flat=True))
			deleted_count = projects_to_delete.count()
			
			# Delete the projects
			projects_to_delete.delete()
			
			# Success message
			if deleted_count == 1:
				messages.success(request, f'Project "{deleted_project_names[0]}" has been deleted successfully.')
			else:
				messages.success(request, f'{deleted_count} projects have been deleted successfully.')
			
			return redirect('project_list')
			
		except Exception as e:
			logger.error(f'Error deleting projects: {str(e)}')
			messages.error(request, 'An error occurred while deleting the projects. Please try again.')
			return redirect('delete_project')
	
	# GET request - show the project selection page
	projects = Project.objects.filter(company=company).order_by('-created_date')
	
	# Add calculated values for display
	for project in projects:
		if project.technology.startswith('Wind'):
			project.calculated_value = project.wind_turbine_installed * project.capacity_per_turbine * 1000
		else:
			project.calculated_value = project.panels_capacity
	
	context = {
		'projects': projects,
		'company': company,
	}
	
	return render(request, 'dashboard/delete_project.html', context)


def get_projects(company):
	return Project.objects.filter(company=company)

def get_financial_models():
	return FinancialModel.objects.all()

def calculate_project_counts(projects):
	"""Calculate project counts by technology and country from filtered projects queryset."""
	tech_counts = projects.values('technology').annotate(total_projects=Count('id'))
	country_counts = projects.values('country').annotate(total_projects=Count('id'))
	return tech_counts, country_counts

def calculate_capacity_in_development(projects, filter_by):
	"""Calculate capacity in development from filtered projects queryset."""
	return projects.filter(project_status='Development').values(filter_by).annotate(
		total_capacity=Sum(
			Case(
				When(technology='Wind', then=F('wind_turbine_installed') * F('capacity_per_turbine') * 1000),
				default=F('panels_capacity'),
				output_field=IntegerField(),
			)
		)
	)

def calculate_capacity_in_operations(projects):
	"""Calculate the total capacity across all operational projects from filtered projects queryset."""
	return projects.filter(project_status='Operational').aggregate(
		total_capacity=Sum(
			Case(
				When(technology='Wind', then=F('wind_turbine_installed') * F('capacity_per_turbine') * 1000),
				default=F('panels_capacity'),
				output_field=IntegerField(),
			)
		)
	)['total_capacity'] or 0

def get_lowest_irr_project(projects, project_status):
	"""Get project with lowest IRR for given status from filtered projects queryset."""
	project = projects.filter(
		project_status=project_status,
		sponsor_irr__isnull=False
	).order_by('sponsor_irr').first()
	
	if project:
		return {'name': project.name, 'irr': project.sponsor_irr}
	return None

def get_highest_irr_development_project(projects):
	"""Get project with highest IRR in Development from filtered projects queryset."""
	project = projects.filter(
		project_status='Development',
		sponsor_irr__isnull=False
	).order_by('-sponsor_irr').first()
	
	if project:
		return {'name': project.name, 'irr': project.sponsor_irr}
	return None
	
def calculate_valuation_in_operations(projects):
	"""Calculate the total valuation across all operational projects from filtered projects queryset."""
	return projects.filter(project_status='Operational').aggregate(
		total_valuation=Sum(F('valuation'))
	)['total_valuation'] or 0

def assign_calculated_value_to_projects(projects):
	"""Assign calculated values to projects from filtered projects queryset."""
	for project in projects:
		if project.technology.startswith('Wind'):
			project.calculated_value = project.wind_turbine_installed * project.capacity_per_turbine * 1000
		else:
			# For all Solar variations (Solar - ground-mounted, Solar - rooftop, etc.)
			project.calculated_value = project.panels_capacity

def get_project_data(projects):
	"""Get project financial data from filtered projects queryset."""
	project_data = {}
	for project in projects:
		try:
			# Choose the right model based on project technology
			# Check if technology starts with 'Solar' to handle variations like 'Solar - ground-mounted'
			if project.technology.startswith('Solar'):
				sponsor_result = SolarFinancialModel.objects.get(
					project=project, identifier='sponsor'
				).financial_model
			elif project.technology.startswith('Wind'):
				sponsor_result = WindFinancialModel.objects.get(
					project=project, identifier='sponsor'
				).financial_model
			else:
				logger.warning(f"Unknown technology type: {project.technology} for project {project.name}")
				project_data[project.id] = None
				continue
			
			project_data[project.id] = sponsor_result
		except (SolarFinancialModel.DoesNotExist, WindFinancialModel.DoesNotExist):
			logger.info(f"No financial model with identifier='sponsor' for project {project.name}")
			project_data[project.id] = None
		except Exception as e:
			logger.error(f"Error getting project data for {project.name}: {str(e)}")
			project_data[project.id] = None
	return project_data

def calculate_yearly_revenues(projects):
	"""Calculate yearly revenues for operational projects from filtered projects queryset."""
	technology_yearly_total_revenues_sum = defaultdict(lambda: defaultdict(float))
	country_yearly_total_revenues_sum = defaultdict(lambda: defaultdict(float))
	total_yearly_revenues_sum = defaultdict(float)
	
	# Filter for operational projects only
	operational_projects = [p for p in projects if p.project_status == "Operational"]

	logger.error(operational_projects)
	
	for project in operational_projects:
		try:
			# Get financial model based on technology
			"""if project.technology.startswith('Solar'):"""
			model = SolarFinancialModel.objects.get(project=project, identifier='sponsor_base_case')
			"""elif project.technology.startswith('Wind'):
				model = WindFinancialModel.objects.get(project=project, identifier='sponsor_base_case')
			else:
				continue"""
			
			sponsor_result = model.financial_model
			
			# Validate data structure
			if (not sponsor_result or 
				'time_series' not in sponsor_result or 
				'revenues' not in sponsor_result or
				'series_end_period_year' not in sponsor_result['time_series'] or
				'total' not in sponsor_result['revenues']):
				continue
			
			years = sponsor_result['time_series']['series_end_period_year']
			revenues = sponsor_result['revenues']['total']
			
			if not years or not revenues or len(years) != len(revenues):
				continue
			
			# Process revenue data
			for i, year_str in enumerate(years):
				try:
					year = int(year_str)
					revenue = float(revenues[i]) if revenues[i] is not None else 0.0
					
					technology_yearly_total_revenues_sum[project.technology][year] += revenue
					country_yearly_total_revenues_sum[project.country][year] += revenue
					total_yearly_revenues_sum[year] += revenue
					
				except (ValueError, TypeError):
					continue
					
		except (SolarFinancialModel.DoesNotExist, WindFinancialModel.DoesNotExist):
			continue
		except Exception:
			continue
	
	# Convert to regular dicts and add totals
	technology_dict = {tech: dict(years) for tech, years in technology_yearly_total_revenues_sum.items()}
	country_dict = {country: dict(years) for country, years in country_yearly_total_revenues_sum.items()}
	
	return json.dumps(technology_dict), json.dumps(country_dict)
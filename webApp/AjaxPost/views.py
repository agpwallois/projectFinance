# Standard library imports
import calendar
import datetime
import time
from collections import defaultdict
# Third-party imports
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
from dateutil import parser
from dateutil.parser import ParserError
from pyxirr import xirr
import traceback
import math
import copy


# Django imports
from django.http import JsonResponse
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models import Sum, Case, When, Value, IntegerField, F

# Application-specific imports
from .forms import ProjectForm
from .models import Project, ComputationResult, SponsorCaseResult
from .property_taxes import property_tax, tfpb_standard_reduction
import requests
from django.urls import reverse
from api_integration.views import get_data
from sofr.views import create_SOFRForwardCurve
from sofr.views import get_historical_sofr

import json
from .taxes import data
from .FinancialModel import FinancialModel
from .WindProject import WindProject
from .SolarProject import SolarProject

def testsimple(request):
	# Call the get_data function to get the response
	response = json.loads(get_data(request, "VERMENTON").content)
	taux_value = response['data']['results'][0]['taux']

	# Pass the 'response' data as a context variable to the template
	context = {
	'response_content': taux_value,

	}



	return render(request, 'testsimple.html', context)

def test(request, id):
	if request.method == "POST":
		return function_test(request, id)
	else:
		return handle_get_request(request, id)

def function_test(request,id):
	project = get_object_or_404(Project, id=id)
	project_form = ProjectForm(request.POST, instance=project)

	if not project_form.is_valid():
		return JsonResponse({'error': project_form.errors.as_json()}, status=400)
		
	try: 
		inp = create_input_dict(request)
		date_series = create_dates_series(inp)
		"""'Date Period start': format_date(date_series,'start_period').tolist(),"""
		"""'Date Period end': format_date(date_series,'end_period').tolist(),"""

		data_detailed = {
			'Date Period start': format_date(date_series,'start_period').tolist(),
			'Date Period end': format_date(date_series,'end_period').tolist(),

		}

		df = pd.DataFrame(data_detailed)
		
		test = datetime.datetime(2023,11,30) + relativedelta(months=+3) + pd.tseries.offsets.QuarterEnd()

		project_form.save()

		return JsonResponse({
			"df":data_detailed,
			"test":test,

			},safe=False, status=200)

	except Exception as e:
		
		error_data = {
			'error_type': e.__class__.__name__,
			'message': str(e)
		}

		return JsonResponse(error_data,safe=False, status=400)


################################################################

def project_list(request):
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


	return render(request, 'projects_list.html', context)



def project_view(request, id):
	project = get_object_or_404(Project, id=id)
	if request.method == "POST":
		return handle_post_request(request, project, id)
	else:
		return handle_get_request(request, project, id)

def handle_post_request(request, project, id):
	project_form = ProjectForm(request.POST, instance=project)

	if not project_form.is_valid():
		return JsonResponse({'error': project_form.errors.as_json()}, status=400)

	return process_project(request, project, project_form)

def handle_get_request(request, project, id):
	
	project_form = ProjectForm(instance=project)
	context = {
		'project_form': project_form,
		'project': project,
	}
	return render(request, "project_view.html", context)


def process_project(request, project, project_form):
	"""
	Process a financial project based on the provided request and project form data.

	This function creates a base lender model from the request data, applies various sensitivity
	analyses to generate different financial scenarios, and then formats the results for display
	in a dashboard.

	Parameters:
	request (HttpRequest): The HTTP request object containing the project data.
	project_form (Form): The form object containing the project form data.

	Returns:
	JsonResponse: A JSON response containing the computed data, dashboard tables, and execution times.
			  If an error occurs during processing, the response will contain error data.

	Raises:
	Exception: If an error occurs during processing, the function will catch the exception,
		   extract the traceback information, and return a JSON response containing
		   the error type, message, and line number.
	"""
	try: 

		try: 
			computation_result = ComputationResult.objects.get(project=project)
			scenarios = computation_result.financial_close_result
			dashboard_sensitivity_tables = computation_result.dashboard_tables


		except ComputationResult.DoesNotExist:


			lender_base_case = create_lender_base_case(request)
			scenarios = {'Lender Case': lender_base_case.create_dict_result()}

			dashboard_sensitivity_tables  = {'Lender Case': scenarios['Lender Case']['dict_results']['Sensi']}

			SENSITIVITIES = ['Sensi Production', 'Sensi Inflation', 'Sensi Opex', 'Sponsor Case']

			for sensitivity in SENSITIVITIES:
				model_copy = copy.deepcopy(lender_base_case)
				model_copy.apply_sensitivity(sensitivity_type=sensitivity)
				model_copy.create_sensi()
				sensitivity_key = f"{sensitivity}"

				sensitivity_results  = model_copy.create_dict_result()

				scenarios[sensitivity_key] = sensitivity_results 		
				dashboard_sensitivity_tables[sensitivity_key] = sensitivity_results['dict_results']['Sensi']

			scenarios = convert_numpy_types(scenarios)

			# Save the computed scenario to the ComputationResult model
			computation_result = ComputationResult.objects.update_or_create(
					project=project,
					defaults={'financial_close_result': scenarios, 'dashboard_tables': dashboard_sensitivity_tables}
			)

			project_form.save()

		computation_scn_displayed, dashboard_tables = select_scn_and_display(project_form, scenarios, dashboard_sensitivity_tables)

		return JsonResponse({
			"df":computation_scn_displayed,
			"tables":dashboard_tables,

			},safe=False, status=200)

	except Exception as e:
		traceback_info = traceback.extract_tb(e.__traceback__)
		last_trace = traceback_info[-1]
		error_data = {
			'error_type': e.__class__.__name__,
			'message': str(e),
			'line_number': last_trace.lineno
		}

		return JsonResponse(error_data,safe=False, status=400)


def format_computation(scenarios, scenario_to_display):

	computation_displayed = scenarios[scenario_to_display]['dict_computation']
	computation_construction = extract_construction_values_for_charts(computation_displayed)
	computation_displayed_sums = calc_sum_nested_dict(computation_displayed)
	computation_displayed_sums_per_year = calc_annual_sum_for_charts(computation_displayed)
	computation_displayed_end_year = extract_EoY_values_for_charts(computation_displayed)

	return {
		'computation_displayed': computation_displayed,
		'computation_construction': computation_construction,
		'computation_displayed_sums': computation_displayed_sums,
		'computation_displayed_sums_per_year': computation_displayed_sums_per_year,
		'computation_displayed_end_year': computation_displayed_end_year
	}

def convert_numpy_types(data):
	if isinstance(data, dict):
		return {key: convert_numpy_types(value) for key, value in data.items()}
	elif isinstance(data, list):
		return [convert_numpy_types(element) for element in data]
	elif isinstance(data, np.integer):
		return int(data)
	elif isinstance(data, np.floating):
		return float(data)
	elif isinstance(data, np.ndarray):
		return data.tolist()
	else:
		return data

def select_scn_and_display(project_form, scenarios, dashboard_sensitivity_tables):
	
	scenario_to_display = determine_scenario_to_display(project_form)
	computation_scn_displayed = format_computation(scenarios, scenario_to_display)
	dashboard_tables = generate_dashboard_tables(scenario_to_display, scenarios, dashboard_sensitivity_tables)

	return computation_scn_displayed, dashboard_tables

def create_lender_base_case(request):
	if request.POST['technology'].startswith('Solar'):
		return SolarProject(request)
	return WindProject(request)


def calc_sum_nested_dict(computation_displayed):
	all_sums = {}

	# Iterate through keys in the outer dictionary
	for dictkey, subkey_data in computation_displayed.items():
		sums = {}

		# Iterate through subkeys within each key
		for subkey, series in subkey_data.items():
			sum_val = sum([x for x in series if isinstance(x, (int, float))])
			sums[subkey] = sum_val

		# Store sums for the current key in the all_sums dictionary
		all_sums[dictkey] = sums

	return all_sums

def calc_annual_sum_for_charts(computation_displayed):

	year_sum = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

	dates = computation_displayed.get("Dates", {})
	period_end_series = dates.get("Period end", [])

	if not period_end_series:
		return year_sum

	for i in range(len(period_end_series)):
		date_str = period_end_series[i]
		# Extract the year from the date string
		year = date_str.split("/")[-1]

		for key, sub_dict in computation_displayed.items():
			if key == "Dates":
				for subkey, series in sub_dict.items():
					year_sum[key][subkey][year] = year
			else: 
				for subkey, series in sub_dict.items():
					if len(series) > i:
						value = series[i]
						# Convert the value to float if it's not already
						value = float(value) if isinstance(value, (int, float)) else 0.0
						# Accumulate the values for each year
						year_sum[key][subkey][year] += value

	return dict(year_sum)

def extract_EoY_values_for_charts(computation_displayed):
	
	values_on_december_31 = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

	dates = computation_displayed.get("Dates", {})
	period_end_series = dates.get("Period end", [])

	if not period_end_series:
		return values_on_december_31

	for i in range(len(period_end_series)):
		end_date_str = period_end_series[i]
		year = end_date_str.split("/")[-1]

		for key, sub_dict in computation_displayed.items():
			if key != "Dates":
				for subkey, series in sub_dict.items():
					if len(series) > i:
						if end_date_str.startswith("31/12") or i == len(period_end_series) - 1:
							value = series[i]
							value = float(value) if isinstance(value, (int, float)) else 0.0
							values_on_december_31[key][subkey][year] += value

	return values_on_december_31

def extract_construction_values_for_charts(computation_displayed):
	
	values_in_construction = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

	flags = computation_displayed.get("FlagsC", {})
	construction_period = flags.get("Construction", [])

	for i in range(len(construction_period)):
		construction = construction_period[i]

		for key, sub_dict in computation_displayed.items():
			for subkey, series in sub_dict.items():
				if len(series) > i:
					if construction == True: 
						value = series[i]
						values_in_construction[key][subkey][i] = value
	return values_in_construction


def generate_dashboard_tables(scenario_to_display, scenarios, table_sensi):

	output_table_formats = {
	"Effective gearing": "{:.2%}",
	"Average DSCR": "{:.2f}x",
	"Debt IRR": "{:.2%}",
	"Share capital IRR": "{:.2%}",
	"Shareholder loan IRR": "{:.2%}",
	"Equity IRR": "{:.2%}",
	"Project IRR (pre-tax)": "{:.2%}",
	"Project IRR (post-tax)": "{:.2%}",
	"Financing plan": None,
	"Balance sheet	": None,
	"Maturity": None,
	}


	results_displayed = {
		'Uses': create_table(scenarios[scenario_to_display]['dict_uses_sources']['Uses'], output_table_formats),
		'Sources': create_table(scenarios[scenario_to_display]['dict_uses_sources']['Sources'], output_table_formats),
		'Project IRR': create_table(scenarios[scenario_to_display]['dict_results']['Project IRR'], output_table_formats),
		'Equity metrics': create_table(scenarios[scenario_to_display]['dict_results']['Equity metrics'], output_table_formats),
		'Debt metrics': create_table(scenarios[scenario_to_display]['dict_results']['Debt metrics'], output_table_formats),
		'Audit': create_table(scenarios[scenario_to_display]['dict_results']['Audit'], output_table_formats),
		'Sensi': create_dashboard_sensitivity_tables (table_sensi),
	}



	return results_displayed




def create_table(results, specific_formats=None):
	table = {}

	# Default format to be applied if no specific format is provided
	default_format = "{:.1f}"

	for metric, data in results.items():
		# Determine the format to use for this metric
		fmt = specific_formats.get(metric, default_format) if specific_formats else default_format

		# Check if the format is None
		if fmt is None:
			formatted_val = data  # Keep the data as is
		elif isinstance(data, str):
			try:
				# Convert string to float and format it, if possible
				formatted_val = fmt.format(float(data))
			except (ValueError, TypeError):
				# If conversion fails, or format code is incompatible, keep the data as is
				formatted_val = data
		else:
			try:
			# Apply the formatting to non-string data
				formatted_val = fmt.format(data)
			except (ValueError, TypeError):
				formatted_val = data


		table[metric] = {0: formatted_val}

	return table



def create_dashboard_sensitivity_tables (results):
	metrics = [("Min DSCR", "{:.2f}x"), ("Avg. DSCR", "{:.2f}x"), 
	("Min LLCR", "{:.2f}x"), ("Equity IRR", "{:.2%}"), 
	("Audit", None)]  # Specific format only for "Audit"

	dashboard_sensitivity_tables  = {"": [metric[0] for metric in metrics]}

	# Initialize an empty list to hold all rows including the blank one
	all_rows = []

	for scenario, data in results.items():
		scenario_data = []
		for j, value in enumerate(data.values()):
			format_string = metrics[j][1]
			if format_string:  # Apply formatting if specified
				formatted_value = format_string.format(value)
			else:
				formatted_value = value  # No formatting
			scenario_data.append(formatted_value)

		all_rows.append((scenario, scenario_data))

		# After the first scenario, append a blank row
		if len(all_rows) == 1:
			all_rows.append(('Blank Row', [''] * len(metrics)))

	# Add the processed rows to the dashboard_sensitivity_tables  dictionary
	for scenario, data in all_rows:
		dashboard_sensitivity_tables [scenario] = data

	return dashboard_sensitivity_tables 


def determine_scenario_to_display(project_form):
	
	calculation_type = project_form.cleaned_data.get('calculation_type')
	calculation_type_mapping = {
		"sensi-p50": "Sponsor Case",
		"sensi-opex": "Sensi Opex",
		"sensi-inflation": "Sensi Inflation",
		"sensi-production": "Sensi Production",
	}

	if calculation_type in calculation_type_mapping:
		key = calculation_type_mapping[calculation_type]
	else:
		key = "Lender Case"
	

	return key
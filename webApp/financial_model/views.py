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
from datetime import date
from decimal import Decimal

# Django imports
from django.http import JsonResponse
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

# Application-specific imports
from .forms import ProjectForm
from .models import Project, ComputationResult, SponsorCaseResult, LenderCase
from .property_taxes import property_tax, tfpb_standard_reduction
import requests
from django.urls import reverse

import json
from .taxes import data
from .FinancialModel import FinancialModel, FinancialModelTEST
from .WindProject import WindProject
from .SolarProject import SolarProject
from .SensitivityModel import SensitivityModel




def project_financial_model(request, id):
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
	return render(request, "financial_model/project_view.html", context)


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
		project_form_hash = json.dumps(project_form.cleaned_data, cls=CustomEncoder)
		try:

			stored_scenarios_results = ComputationResult.objects.get(project=project)
			stored_project_form_hash = stored_scenarios_results.form_data

			# Check if the form data has changed
			if stored_project_form_hash == project_form_hash:
				scenarios = stored_scenarios_results.all_scenarios_results
				dashboard_sensitivity_tables = stored_scenarios_results.all_dashboard_tables
			else: 
				raise ComputationResult.DoesNotExist

		except ComputationResult.DoesNotExist:

			lender_base_case = create_lender_base_case(request)

			financial_model_test = FinancialModelTEST(request)
			
			LenderCase.objects.update_or_create(
				project=project,
				defaults={
					'lender_case': financial_model_test.to_json(),
				}
			)

			lender_case_test = LenderCase.objects.get(project=project)
			see_lender_case_test = lender_case_test.lender_case	


			scenarios, dashboard_sensitivity_tables = calculate_scenarios(request,lender_base_case)
			save_computation_result(project, project_form, scenarios, dashboard_sensitivity_tables)

		computation_scn_displayed, dashboard_tables = display_selected_scenario(project_form, scenarios, dashboard_sensitivity_tables)

		return create_json_response(computation_scn_displayed, dashboard_tables, scenarios)
	except Exception as e:
		return handle_exception(e)



def save_computation_result(project, project_form, scenarios, dashboard_sensitivity_tables):
	stored_form_data_hash = json.dumps(project_form.cleaned_data, cls=CustomEncoder)
	ComputationResult.objects.update_or_create(
		project=project,
		defaults={
			'all_scenarios_results': scenarios,
			'all_dashboard_tables': dashboard_sensitivity_tables,
			'form_data': stored_form_data_hash
		}
	)
	project_form.save()




def calculate_scenarios(request, lender_base_case):
	"""
	Calculate different financial scenarios based on sensitivities.

	This function takes a request and a lender base case to calculate multiple
	financial scenarios. It applies various sensitivity analyses to the base
	case, recalculates the financial model for each sensitivity, and compiles
	the results into a dictionary format.

	Parameters:
	request (RequestType): The request object containing necessary parameters for sensitivity analysis.
	lender_base_case (LenderBaseCaseType): The base case object representing the lender's financial scenario.

	Returns:
	tuple: A tuple containing:
		- scenarios (dict): A dictionary where keys are the scenario names (including the base case and sensitivities) 
		  and values are the corresponding results as dictionaries.
		- dashboard_sensitivity_tables (dict): A dictionary where keys are the scenario names and values are the 
		  sensitivity analysis results.
	"""
	scenarios = {'Lender Case': lender_base_case.create_dict_result()}
	dashboard_sensitivity_tables  = {'Lender Case': scenarios['Lender Case']['dict_results']['Sensi']}
	SENSITIVITIES = ['sensi_production', 'sensi_opex', 'sensi_inflation', 'sponsor_production_choice']
	for sensitivity in SENSITIVITIES:
		model_copy = SensitivityModel(request, lender_base_case)
		model_copy.apply_sensitivity(sensitivity_type=sensitivity)
		model_copy.recalc_financial_model()
		sensitivity_key = f"{sensitivity}"
		sensitivity_results = model_copy.create_dict_result()
		scenarios[sensitivity_key] = sensitivity_results
		dashboard_sensitivity_tables[sensitivity_key] = sensitivity_results['dict_results']['Sensi']
		scenarios = convert_numpy_types(scenarios)
	return scenarios, dashboard_sensitivity_tables




def create_json_response(computation_scn_displayed, dashboard_tables, scenarios):
	"""
	Create a JSON response with computed scenario data, dashboard tables, and other relevant information.

	This function generates a JSON response containing the displayed computation scenario,
	dashboard tables, sidebar data from the lender case scenario, and the current form data hash.

	Parameters:
	computation_scn_displayed (DataFrameType): The displayed computation scenario data.
	dashboard_tables (dict): A dictionary containing the dashboard tables.
	scenarios (dict): A dictionary containing all scenarios, including the 'Lender Case'.
	project_form_hash (str): A hash string representing the current form data.

	Returns:
	JsonResponse: A Django JsonResponse object containing the provided data.
	"""
	return JsonResponse({
		"df": computation_scn_displayed,
		"tables": dashboard_tables,
		"sidebar_data": scenarios['Lender Case']['dict_sidebar_data'],



	}, safe=False, status=200)


def handle_exception(e):
	traceback_info = traceback.extract_tb(e.__traceback__)
	last_trace = traceback_info[-1]
	error_data = {
		'error_type': e.__class__.__name__,
		'message': str(e),
		'line_number': last_trace.lineno
	}
	return JsonResponse(error_data, safe=False, status=400)






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

def display_selected_scenario(project_form, scenarios, dashboard_sensitivity_tables):
	
	scenario_to_display = determine_scenario_to_display(project_form)
	computation_scn_displayed = format_computation(scenarios, scenario_to_display)
	dashboard_tables = generate_dashboard_tables(scenario_to_display, scenarios, dashboard_sensitivity_tables)

	return computation_scn_displayed, dashboard_tables

def create_lender_base_case(request):
	if request.POST['technology'].startswith('Solar'):
		return SolarProject(request)
	return WindProject(request)



class DecimalEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, Decimal):
			return float(obj)
		return super().default(obj)

class DateEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, date):
			return obj.isoformat()
		return super().default(obj)

class CustomEncoder(DateEncoder, DecimalEncoder):
	pass


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


def hash_form_data(form_data):
	"""Generate a SHA-256 hash of the form data."""
	form_data_str = json.dumps(form_data, sort_keys=True)
	return hashlib.sha256(form_data_str.encode('utf-8')).hexdigest()


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
		"sensi-p50": "sponsor_production_choice",
		"sensi-opex": "sensi_opex",
		"sensi-inflation": "sensi_inflation",
		"sensi-production": "sensi_production",
	}

	if calculation_type in calculation_type_mapping:
		key = calculation_type_mapping[calculation_type]
	else:
		key = "Lender Case"
	

	return key
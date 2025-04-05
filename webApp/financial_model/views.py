# Standard library imports
import calendar
import datetime
import time
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
from .model_project import Project
from .model_solar_financial_model import SolarFinancialModel
from .model_wind_financial_model import WindFinancialModel
from .property_taxes import property_tax, tfpb_standard_reduction
import requests
from django.urls import reverse
import logging
import concurrent.futures

from concurrent.futures import ThreadPoolExecutor

from .views_helpers import (
	build_dashboard_table,
	build_dashboard_table_sensi,
	build_dashboard_table_sensi_sponsor,

)

import json
from typing import Dict, Any, Tuple, Optional
from django.views import View
from django.forms.models import model_to_dict
from django.core.exceptions import ObjectDoesNotExist

logger = logging.getLogger(__name__)

def timer_decorator(method):
	@wraps(method)
	def timed(*args, **kwargs):
		start_time = time.time()
		result = method(*args, **kwargs)
		end_time = time.time()
		elapsed_time = end_time - start_time

		# Store the result in a class attribute
		cls = args[0].__class__
		if not hasattr(cls, 'execution_times'):
			cls.execution_times = {}
		cls.execution_times[method.__name__] = elapsed_time

		print(f"Execution time of {method.__name__}: {elapsed_time:.4f} seconds")
		return result

	return timed

class FinancialModelView(View):




	# settings.py or configuration file

	FINANCIAL_MODEL_SCENARIOS = {
		'lender_base_case': {
			'model_type': 'lender',
			'sensitivities': {},
		},
		'lender_sensi_prod': {
			'model_type': 'lender',
			'sensitivities': {'production': 'sensi_production'}, 
		},
		'lender_sensi_inf': {
			'model_type': 'lender',
			'sensitivities': {'inflation': 'sensi_inflation'},
		},
		'lender_sensi_opex': {
			'model_type': 'lender',
			'sensitivities': {'opex': 'sensi_opex'},
		},
		'sponsor_base_case': {
			'model_type': 'sponsor',
			'sensitivities': {},
		},
		'sponsor_sensi_prod': {
			'model_type': 'sponsor',
			'sensitivities': {'production': 'sensi_production_sponsor'},
		},
		'sponsor_sensi_inf': {
			'model_type': 'sponsor',
			'sensitivities': {'inflation': 'sensi_inflation_sponsor'},
		},
		'sponsor_sensi_opex': {
			'model_type': 'sponsor',
			'sensitivities': {'opex': 'sensi_opex_sponsor'},
		},
	}


	""" GET METHOD """

	def get(self, request, id: int):
		"""Handle GET requests for financial model data"""    
		project = get_object_or_404(Project, id=id)
		context = {'project_form': ProjectForm(instance=project), 'project': project}
	
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return self._process_get_request(request, project)
			
		return render(request, "financial_model/project_view.html", context)

	def _process_get_request(self, request, project: Project) -> JsonResponse:
		"""Process AJAX requests for financial model data"""
		"""scenario = request.GET.get('scenario')"""
		scenario = "lender_base_case"
		financial_models = self._get_financial_models(project)
		selected_model = financial_models.get(scenario)
		logger.error(financial_models.items())
		
		if not selected_model:
			return JsonResponse({'error': 'Invalid scenario'}, status=400)
			
		dashboard_data = self._build_dashboard(selected_model, financial_models)
		table_sensi_diff = self._compute_differences(dashboard_data['Sensi'])
		table_sensi_diff_IRR = self._compute_differences(dashboard_data['Sensi_IRR'])

		charts_data_constr, charts_data_eoy, charts_data_sum_year = selected_model.extract_values_for_charts()

		displayed_metrics = self._collect_displayed_metrics(financial_models)
		
		return self._prepare_json_response(selected_model, financial_models, displayed_metrics, dashboard_data, table_sensi_diff, table_sensi_diff_IRR, charts_data_constr, charts_data_eoy, charts_data_sum_year)

	def _get_financial_models(self, project: Project) -> Dict[str, SolarFinancialModel]:
		"""Retrieve all financial models for a project"""
		financial_models = {}
		
		for scenario_id, scenario_config in self.FINANCIAL_MODEL_SCENARIOS.items():
			try:
				model = SolarFinancialModel.objects.get(
					project=project, 
					identifier=scenario_id
				)
				financial_models[scenario_id] = model
				logger.error("Retrieved")
			except SolarFinancialModel.DoesNotExist:
				# Create missing models on demand
				logger.error("Missing")
				model = self._create_model(project, scenario_id, scenario_config)
				financial_models[scenario_id] = model
				
		return financial_models

	""" POST METHOD """

	def post(self, request, id):
		"""Handle POST requests for financial model updates"""
		project = get_object_or_404(Project, id=id)
		project_form = ProjectForm(request.POST, instance=project)

		if not project_form.is_valid():
			return JsonResponse({'error': project_form.errors.as_json()}, status=400)

		project_form.save()
		"""scenario = request.POST.get('scenario')"""
		scenario = "lender_base_case"
		return self._create_financial_models(request, project, project_form, scenario)

		

	def _create_financial_models(self, request, project, project_form, selected_scenario):
			"""
			Create or update financial models based on the scenario and project form data.
			"""

			# Create or retrieve models for all scenarios
			financial_models = {}
			for scenario_id, scenario_config in self.FINANCIAL_MODEL_SCENARIOS.items():
				model = self._create_model(project, scenario_id, scenario_config)
				financial_models[scenario_id] = model
				logger.error("Created")

			logger.error(financial_models.items())

			# Retrieve the selected model
			selected_model = financial_models.get(selected_scenario, financial_models['lender_base_case'])

			# Generate Dashboard Tables
			dashboard_tables = self._build_dashboard(selected_model, financial_models)
			table_sensi_diff = self._compute_differences(dashboard_tables['Sensi'])
			table_sensi_diff_IRR = self._compute_differences(dashboard_tables['Sensi_IRR'])

			# Format Data for Charts
			charts_data_constr, charts_data_eoy, charts_data_sum_year = selected_model.extract_values_for_charts()

			displayed_metrics = self._collect_displayed_metrics(financial_models)



			project.sponsor_irr = financial_models['sponsor_base_case'].financial_model['dict_results']['Sensi_IRR']['Equity IRR'] * 100

			valuation_keys = list(financial_models['sponsor_base_case'].financial_model['dict_results']['Valuation'].keys())
			valuation_value = financial_models['sponsor_base_case'].financial_model['dict_results']['Valuation'][valuation_keys[1]]
			rounded_value = 1000

			project.valuation = rounded_value
			project.save()

			# Prepare and return JSON response
			return self._prepare_json_response(selected_model, financial_models, displayed_metrics, dashboard_tables, table_sensi_diff, table_sensi_diff_IRR, charts_data_constr, charts_data_eoy, charts_data_sum_year)


	def _create_model(self, project: Project, scenario_id: str, scenario_config: dict) -> SolarFinancialModel:
		"""
		Create or update a financial model based on the given scenario configuration.
		All models except Lender_base_case depend on Lender_base_case.
		"""
		# First ensure Lender_base_case exists as it's needed for dependency
		if scenario_id != 'lender_base_case':
			lender_base_case, lender_created = SolarFinancialModel.objects.get_or_create(
				project=project,
				identifier='lender_base_case',
				defaults={'financial_model': {}}
			)
			
			# Create the base case model if it's new or empty
			if lender_created or not lender_base_case.financial_model:
				lender_base_case.create_financial_model(
					model_type='lender',
					debt_sizing_sculpting=True
				)
				
			# Set dependency to Lender_base_case for all other models
			depends_on = lender_base_case
		else:
			# Lender_base_case has no dependency
			depends_on = None

		# Get or create the model instance
		model, created = SolarFinancialModel.objects.get_or_create(
			project=project,
			identifier=scenario_id,  # Use the mapping to get the identifier
			defaults={'financial_model': {}}
		)
		
		# Update the dependency
		model.depends_on = depends_on
		model.save()

				# Apply sensitivities based on the scenario configuration
		# Apply sensitivities based on the scenario configuration
		sensi_params = {}
		for param_name, project_field in scenario_config.get('sensitivities', {}).items():
			model_type = scenario_config['model_type']
			logger.error(model_type)
			
			# Determine proper parameter names based on model type
			if model_type == 'sponsor':
				# For sponsor models, use _sponsor suffix
				if param_name == 'production':
					sensi_params['sensi_production_sponsor'] = getattr(project, project_field)
					logger.error(sensi_params['sensi_production_sponsor'] )
				elif param_name == 'inflation':
					sensi_params['sensi_inflation_sponsor'] = getattr(project, project_field)
				elif param_name == 'opex':
					sensi_params['sensi_opex_sponsor'] = getattr(project, project_field)
				else:
					sensi_params[param_name] = getattr(project, project_field)
			else:
				# For lender models, use standard names
				if param_name == 'production':
					sensi_params['sensi_production'] = getattr(project, project_field)
				elif param_name == 'inflation':
					sensi_params['sensi_inflation'] = getattr(project, project_field)
				elif param_name == 'opex':
					sensi_params['sensi_opex'] = getattr(project, project_field)
				else:
					sensi_params[param_name] = getattr(project, project_field)



		# Debt sizing is only enabled for Lender_base_case
		debt_sizing_sculpting = (scenario_id == 'lender_base_case')

		# Create financial model
		model.create_financial_model(
			model_type=scenario_config['model_type'],
			debt_sizing_sculpting=debt_sizing_sculpting,
			**sensi_params
		)

		return model

	""" COMMON GET POST METHODS """

	def _collect_displayed_metrics(self, financial_models):

		displayed_metrics = {
			"sponsor_IRR": f"{financial_models['sponsor_base_case'].financial_model['dict_results']['Sensi_IRR']['Equity IRR'] * 100:.1f}%",  # Percentage with 1 decimal
			"lender_DSCR": f"{financial_models['lender_base_case'].financial_model['dict_results']['Sensi']['Min DSCR']:.2f}x",  # 2 decimals + "x"
			"total_uses": f"{financial_models['lender_base_case'].financial_model['dict_uses_sources']['Uses']['Total']:,.1f}",  # Thousands separator + 1 decimal
		}
		sidebar_data = financial_models['sponsor_base_case'].financial_model['dict_sidebar']
		displayed_metrics.update(sidebar_data)

		return displayed_metrics


	def _prepare_json_response(
		self, 
		model: SolarFinancialModel, 
		financial_models: Dict,
		displayed_metrics: Dict, 
		dashboard_tables: Dict, 
		table_sensi_diff: Dict,
		table_sensi_diff_IRR: Dict,
		charts_data_constr: Dict, 
		charts_data_eoy: Dict,
		charts_data_sum_year: Dict, 

	) -> JsonResponse:
		"""Prepare JSON response with all financial model data"""
		try:
			return JsonResponse({
				"df": model.financial_model,
				"tables": dashboard_tables,
				"table_sensi_diff": table_sensi_diff,
				"table_sensi_diff_IRR": table_sensi_diff_IRR, 
				"charts_data_constr": charts_data_constr,
				"df_annual": charts_data_sum_year,
				"df_eoy": charts_data_eoy,
				
				"sidebar_data": displayed_metrics, 
			}, safe=False)
		except Exception as e:
			"""sidebar_data": model.financial_model['dict_sidebar'],"""
			return self._handle_exception(e)




	def _handle_exception(self, e: Exception) -> JsonResponse:
		traceback_info = traceback.extract_tb(e.__traceback__)
		last_trace = traceback_info[-1]
		error_data = {
			'error_type': e.__class__.__name__,
			'message': str(e),
			'line_number': last_trace.lineno
		}
		return JsonResponse(error_data, safe=False, status=400)

	def _build_dashboard(
		self, 
		selected_model: SolarFinancialModel, 
		financial_models: Dict[str, SolarFinancialModel]
	) -> Dict[str, Any]:
		"""Build dashboard data from financial models"""


		table_sensi = {
			key: model.financial_model['dict_results']['Sensi']
			for key, model in financial_models.items()
			if key.startswith("lender")
		}


		table_sensi_IRR = {
			key: model.financial_model['dict_results']['Sensi_IRR']
			for key, model in financial_models.items()
			if key.startswith("sponsor")
		}
		
		data = selected_model.financial_model

		return self._build_dashboard_tables(
			data['dict_uses_sources'],
			data['dict_results'],
			table_sensi, 
			table_sensi_IRR,
		)

	def _compute_differences(self, table_sensi):
		# Check if the table has a header row (key '')
		headers = table_sensi.get('', None)
		
		# Remove the header row if it exists and create the table data
		table_data = {k: v for k, v in table_sensi.items() if k != ''} if headers else table_sensi.copy()

		# Create a DataFrame from the remaining dictionary
		df = pd.DataFrame.from_dict(table_data, orient='index')
		
		# Check if the DataFrame is empty or has no valid columns
		if df.empty:
			print("Warning: DataFrame is empty.")
			return table_sensi
		
		# Set column names if the header row exists and if it matches the number of columns
		if headers:
			if isinstance(headers, list) and len(headers) == len(df.columns):
				df.columns = headers
			else:
				print("Warning: Header length mismatch or invalid header format.")
		
		# Check that we have enough columns (at least one numeric column and the Audit column)
		if df.shape[1] < 2:
			print("Warning: Input dictionary has insufficient columns.")
			return table_sensi

		# Function to convert formatted strings to numeric values
		def convert_to_numeric(val):
			if isinstance(val, str):
				if val.strip() == '':
					return np.nan
				if '%' in val:
					try:
						return float(val.strip('%')) / 100
					except ValueError:
						return np.nan
				elif 'x' in val:
					try:
						return float(val.strip('x'))
					except ValueError:
						return np.nan
				try:
					return float(val)
				except ValueError:
					return np.nan
			return val

		# Create a numeric version of the dataframe for calculations (excluding the last column 'Audit')
		numeric_df = df.copy()
		for col in numeric_df.columns[:-1]:
			numeric_df[col] = numeric_df[col].apply(convert_to_numeric)

		# Use the first data row as the base case (baseline) for comparison, excluding the Audit column
		base_case = numeric_df.iloc[0, :-1].to_numpy()

		# Dictionary to store differences
		differences = {}

		# Compute differences relative to the base case
		for index, row in numeric_df.iterrows():
			current_row = row[:-1].to_numpy()
			diff = current_row - base_case
			differences[index] = {}
			for i, col in enumerate(df.columns[:-1]):
				differences[index][col] = diff[i]
			# Copy the Audit column unchanged
			differences[index][df.columns[-1]] = row[df.columns[-1]]

		# Convert the differences into a DataFrame
		df_diff = pd.DataFrame.from_dict(differences, orient='index')
		
		# For the base case row, set the differences to NaN (to avoid meaningless differences)
		df_diff.iloc[0, :-1] = np.nan

		# Reformat differences based on their original type ('x' or '%')
		def reformat_value(value, original_value):
			if isinstance(original_value, str):
				if 'x' in original_value:
					return f"{value:.2f}x"  # Format as 'x'
				elif '%' in original_value:
					return f"{value*100:.2f}%"  # Format as '%'
			return value

		# Apply reformatting to the difference DataFrame
		for col in df_diff.columns[:-1]:
			for idx in df_diff.index:
				original_value = df.at[idx, col]
				df_diff.at[idx, col] = reformat_value(df_diff.at[idx, col], original_value)

		# Convert the DataFrame to a dictionary
		result = df_diff.to_dict(orient='index')

		# Helper function to recursively replace np.nan with None
		def replace_nan(obj):
			if isinstance(obj, dict):
				return {k: replace_nan(v) for k, v in obj.items()}
			elif isinstance(obj, list):
				return [replace_nan(item) for item in obj]
			elif isinstance(obj, float) and pd.isna(obj):
				return None
			else:
				return obj

		# Return the cleaned dictionary, now fully JSON serializable
		return replace_nan(result)

	def _build_dashboard_tables(
		self, 
		dict_uses_sources: Dict, 
		dict_results: Dict, 
		table_sensi: Dict,
		table_sensi_IRR: Dict,
	) -> Dict[str, Any]:
		"""Build formatted dashboard tables"""
		output_formats = {
			"Effective gearing": "{:.2%}",
			"Average DSCR": "{:.2f}x",
			"Debt IRR": "{:.2%}",
			"Share capital IRR": "{:.2%}",
			"Shareholder loan IRR": "{:.2%}",
			"Equity IRR": "{:.2%}",
			"Project IRR (pre-tax)": "{:.2%}",
			"Project IRR (post-tax)": "{:.2%}"
		}

		sorted_uses = dict(sorted(dict_uses_sources['Uses'].items(), key=lambda item: item[1], reverse=True))
		
		return {
			'Uses': build_dashboard_table(sorted_uses, output_formats),
			'Sources': build_dashboard_table(dict_uses_sources['Sources'], output_formats),
			'Project IRR': build_dashboard_table(dict_results['Project IRR'], output_formats),
			'Equity metrics': build_dashboard_table(dict_results['Equity metrics'], output_formats),
			'Debt metrics': build_dashboard_table(dict_results['Debt metrics'], output_formats),
			'Audit': build_dashboard_table(dict_results['Audit'], output_formats),
			'Valuation': build_dashboard_table(dict_results['Valuation'], output_formats),
			'Sensi': build_dashboard_table_sensi(table_sensi),
			'Sensi_IRR': build_dashboard_table_sensi_sponsor(table_sensi_IRR),
		}

	def _project_form_changed(self, project_form):
		"""
		Return true if the user changed any assumptions of the project form, except for sensitivities assumptions.
		This is used to determine if all models need to be regenerated.
		"""
		# Define fields that are considered sensitivity parameters
		excluded_fields = {
			'sensi_production', 'sensi_inflation', 'sensi_opex', 
			'sensi_production_sponsor', 'sensi_inflation_sponsor', 'sensi_opex_sponsor'
		}
		
		# Get all changed fields excluding sensitivity parameters
		changed_fields = set(project_form.changed_data) - excluded_fields
		
		# Log the non-sensitivity fields that changed
		logger.error(f"Changed non-sensitivity fields: {changed_fields}")
		
		# Return True if any non-sensitivity field changed
		return bool(changed_fields)

	def _project_form_sensi_changed(self, project_form, sensitivity_type):
		"""
		Check if a specific sensitivity parameter changed.
		This is used to determine which sensitivity models need to be regenerated.
		"""
		# Convert the changed data to a set
		changed_fields = set(project_form.changed_data)
		
		# Check if the sensitivity parameter is in the changed fields
		logger.error(f"Checking if sensitivity {sensitivity_type} has changed")
		result = sensitivity_type in changed_fields
		logger.error(f"Sensitivity {sensitivity_type} changed: {result}")
		
		return result






	"""def _create_financial_models(self, request, project, project_form, scenario):
		# First create lender base model as it's required for others
		base_lender_model = self._create_model(project, "lender_case")
		
		# Now create sponsor base model which depends on lender model
		base_sponsor_model = self._create_model(project, "sponsor_case")
		
		# Initialize financial models dictionary with base cases
		financial_models = {
			'Lender_base_case': base_lender_model,
			'Sponsor_base_case': base_sponsor_model
		}
		
		# Create all sensitivity models
		for scenario_key, model_type in self.SCENARIO_MAP.items():
			# Skip base cases which we've already created
			if model_type in ["lender_case", "sponsor_case"]:
				continue
			model = self._create_model(project, model_type)
			financial_models[scenario_key] = model

		logger.error(financial_models.items())

		# Get selected model
		selected_model = financial_models.get(scenario, base_lender_model)
		
		# Generate Dashboard Tables
		dashboard_tables = self._build_dashboard(selected_model, financial_models)
		table_sensi_diff = self._compute_differences(dashboard_tables['Sensi'])
		table_sensi_diff_IRR = self._compute_differences(dashboard_tables['Sensi_IRR'])
	

		# Format Data for Charts
		charts_data_constr, charts_data_eoy, charts_data_sum_year = selected_model.extract_values_for_charts()
		
		# Prepare and return JSON response
		return self._prepare_json_response(selected_model, dashboard_tables, table_sensi_diff, table_sensi_diff_IRR, charts_data_constr, charts_data_eoy, charts_data_sum_year)"""



				
	"""def _create_model(self, project: Project, model_type: str) -> SolarFinancialModel:
		# Create or update a financial model of the specified type
		# First, ensure lender base case exists as it's needed for dependency
		if model_type != "lender_case":
			lender_base, _ = SolarFinancialModel.objects.get_or_create(
				project=project,
				identifier="lender_case",
				defaults={'financial_model': {}}
			)
			if not lender_base.financial_model:
				lender_base.create_financial_model(
					model_type='lender_case',
					debt_sizing_sculpting=True
				)
		
		# Now create or get the requested model
		model, created = SolarFinancialModel.objects.get_or_create(
			project=project,
			identifier=model_type,
			defaults={'financial_model': {}}
		)
		
		# Determine model parameters
		is_lender_case = model_type.startswith('lender_case') or model_type.startswith('sensi_') and not model_type.endswith('_sponsor')
		is_sponsor_case = model_type.startswith('sponsor_case') or model_type.endswith('_sponsor')
		is_base_case = model_type in ['lender_case', 'sponsor_case']
		
		# Set sensitivity parameters
		sensi_params = {}
		if not is_base_case:
			# Handle sponsor case sensitivities differently
			if is_sponsor_case:
				if 'sensi_production' in model_type:
					sensi_params['sensi_production'] = project.sensi_production_sponsor
				elif 'sensi_inflation' in model_type:
					sensi_params['sensi_inflation'] = project.sensi_inflation_sponsor
				elif 'sensi_opex' in model_type:
					sensi_params['sensi_opex'] = project.sensi_opex_sponsor
			else:
				# Handle lender case sensitivities
				if 'sensi_production' in model_type:
					sensi_params['sensi_production'] = project.sensi_production
				elif 'sensi_inflation' in model_type:
					sensi_params['sensi_inflation'] = project.sensi_inflation
				elif 'sensi_opex' in model_type:
					sensi_params['sensi_opex'] = project.sensi_opex
		
		# Set dependency for non-lender base cases
		if model_type != "lender_case":
			lender_base = SolarFinancialModel.objects.get(project=project, identifier="lender_case")
			model.depends_on = lender_base
			model.save()
		
		# Create the financial model
		base_model_type = 'lender_case' if is_lender_case else 'sponsor_case'
		model.create_financial_model(
			model_type=base_model_type,
			debt_sizing_sculpting=(is_lender_case),
			**sensi_params
		)
		
		return model"""


	"""	SCENARIO_MAP = {
		'Lender_base_case': "Lender Base Case",
		'Lender_sensi_prod': "sensi_production",
		'Lender_sensi_inf': "sensi_inflation", 
		'Lender_sensi_opex': "sensi_opex",
		'Sponsor_base_case': "sponsor",
		'Sponsor_sensi_prod': "sensi_production_sponsor",
		'Sponsor_sensi_inf': "sensi_inflation_sponsor",
		'Sponsor_sensi_opex': "sensi_opex_sponsor",

		}"""
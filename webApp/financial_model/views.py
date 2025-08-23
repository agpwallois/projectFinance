
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
from django.http import Http404
from authentication.utils import get_user_company
from functools import wraps


# Django imports
from django.http import JsonResponse
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Application-specific imports
from .forms import ProjectForm
from .model_project import Project
from .model_solar_fm import SolarFinancialModel
from .model_wind_fm import WindFinancialModel
from .property_taxes import property_tax, tfpb_standard_reduction
import requests
from django.urls import reverse
import logging
import concurrent.futures
from django.utils.decorators import method_decorator

from concurrent.futures import ThreadPoolExecutor

from .views_helpers import (
	build_dashboard_cards,
	build_dashboard_cards_sensi,
	build_dashboard_cards_sensi_sponsor,

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

@method_decorator(login_required, name='dispatch')
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

	def dispatch(self, request, *args, **kwargs):
		"""Override dispatch to add company-based authorization"""
		# First call the parent dispatch to handle login_required
		response = super().dispatch(request, *args, **kwargs)
		return response
	
	def _check_project_access(self, request, project_id):
		"""Check if user has access to this project based on company"""
		try:
			# Get user's company
			user_company = get_user_company(request.user)
			
			if not user_company:
				messages.error(request, 'Your account is not associated with any company.')
				return False
			
			# Get the project and check if it belongs to user's company
			project = get_object_or_404(Project, id=project_id)
			
			if project.company != user_company:
				# Project doesn't belong to user's company
				return False
				
			return True
			
		except Exception as e:
			logger.error(f"Error checking project access: {e}")
			return False

	def _get_model_class(self, project):
		"""Get the appropriate model class based on project technology"""
		if project.technology.startswith('Solar'):
			return SolarFinancialModel
		elif project.technology.startswith('Wind'):  
			return WindFinancialModel
		else:
			raise ValueError(f"Unknown technology: {project.technology}")

	""" GET METHOD """
	"""@timer_decorator"""
	def get(self, request, id: int):
		# Check project access first
		if not self._check_project_access(request, id):
			raise Http404("Project not found or access denied")

		"""Handle GET requests for financial model data"""    
		project = get_object_or_404(Project, id=id)
		context = {'project_form': ProjectForm(instance=project), 'project': project}

		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return self._process_get_request(request, project)
			
		return render(request, "financial_model/project_view.html", context)
	
	"""@timer_decorator"""
	def _process_get_request(self, request, project: Project) -> JsonResponse:
		"""Process AJAX requests for financial model data"""
		
		# Get all the financial models
		financial_models = self._get_financial_models(project)

		# Get the selected financial model
		scenario = request.GET.get('scenario')
		selected_fm = financial_models.get(scenario)
		"""logger.error(financial_models.items())"""
		
		if not selected_fm:
			return JsonResponse({'error': 'Invalid scenario'}, status=400)
			
		return self._build_response_data(selected_fm, financial_models)

	""" POST METHOD """
	def post(self, request, id):
		"""Handle POST requests for financial model updates"""

		# Check project access first
		if not self._check_project_access(request, id):
			raise Http404("Project not found or access denied")
			
		project = get_object_or_404(Project, id=id)
			
		project_form = ProjectForm(request.POST, instance=project)

		if not project_form.is_valid():
			# DETAILED ERROR LOGGING
			logger.error(f"Form validation failed!")
			logger.error(f"Form errors: {project_form.errors}")
			
			# Check which required fields are missing
			for field_name, field in project_form.fields.items():
				if field.required and not request.POST.get(field_name):
					logger.error(f"MISSING REQUIRED FIELD: {field_name}")
			
			# Extract clean error messages from form errors
			error_messages = []
			for field, errors in project_form.errors.items():
				if field == '__all__':
					# Non-field errors
					for error in errors:
						error_messages.append(str(error))
				else:
					# Field-specific errors
					for error in errors:
						error_messages.append(f"{field}: {error}")
			
			return JsonResponse({
				'error': 'Form validation failed',
				'validation_errors': error_messages,
				'missing_fields': [name for name, field in project_form.fields.items() 
								if field.required and not request.POST.get(name)]
			}, status=400)

		project_form.save()
		return self._create_financial_models(request, project, project_form)
			
	"""@timer_decorator"""
	def _create_financial_models(self, request, project, project_form):
		"""Create or update financial models based on the scenario and project form data."""

		
		for field_name in ['capacity_per_turbine', 'wind_turbine_installed', 'panels_capacity', 'annual_degradation']:
			if field_name in project_form.changed_data:
				initial_value = project_form.initial.get(field_name)
				cleaned_value = project_form.cleaned_data.get(field_name)
		
		# Check what type of changes to the form occurred
		non_sensi_changed = self._project_form_changed(project_form)
		
		if non_sensi_changed:
			# Create or update all financial models
			financial_models = self._create_all_financial_models(project)
			
		else: 
			# Only sensitivity fields changed - update models selectively
			financial_models = self._update_selective_financial_models(project, project_form)
		
		# Get the selected financial model
		scenario = request.POST.get('scenario')
		selected_fm = self._get_selected_fm(scenario, financial_models)
		
		# Update project financials
		self._update_project_financials(project, financial_models)
		
		return self._build_response_data(selected_fm, financial_models)

	def _update_selective_financial_models(self, project, project_form):
		"""Update only the financial models affected by sensitivity changes."""
		# Get existing models (without creating missing ones since we'll recreate them anyway)
		financial_models = self._get_financial_models(project)
		
		# Define sensitivity field mappings
		sensitivity_mappings = {
			'sensi_production': ['lender_sensi_prod'],
			'sensi_inflation': ['lender_sensi_inf'], 
			'sensi_opex': ['lender_sensi_opex'],
			'sensi_production_sponsor': ['sponsor_sensi_prod'],
			'sensi_inflation_sponsor': ['sponsor_sensi_inf'],
			'sensi_opex_sponsor': ['sponsor_sensi_opex']
		}
		
		# Track which models need updating
		models_to_update = set()
		
		# Check each sensitivity field for changes
		for sensi_field, affected_scenarios in sensitivity_mappings.items():
			if self._project_form_sensi_changed(project_form, sensi_field):
				models_to_update.update(affected_scenarios)
		
		# Update only the affected models
		for scenario_id in models_to_update:
			if scenario_id in self.FINANCIAL_MODEL_SCENARIOS:
				scenario_config = self.FINANCIAL_MODEL_SCENARIOS[scenario_id]
				financial_models[scenario_id] = self._create_fm(project, scenario_id, scenario_config)
		
		return financial_models

	"""@timer_decorator"""
	def _get_financial_models(self, project: Project) -> Dict[str, Any]:
		"""Retrieve all financial models for a project with optimized queries"""
		model_class = self._get_model_class(project)
		scenario_ids = list(self.FINANCIAL_MODEL_SCENARIOS.keys())
		
		# OPTIMIZED: Single query using the composite index
		# This will use the fm_project_identifier_idx index efficiently
		existing_models = model_class.objects.filter(
			project=project,
			identifier__in=scenario_ids
		).select_related('depends_on')  # Prefetch dependencies to avoid N+1 queries
		
		# Create lookup dictionary
		models_by_id = {model.identifier: model for model in existing_models}
		
		# Build result and create missing models
		financial_models = {}
		
		for scenario_id, scenario_config in self.FINANCIAL_MODEL_SCENARIOS.items():
			if scenario_id in models_by_id:
				financial_models[scenario_id] = models_by_id[scenario_id]
			else:
				# Create missing model
				model = self._create_fm(project, scenario_id, scenario_config)
				financial_models[scenario_id] = model
		
		return financial_models

	# Alternative method for getting a single model (if needed):
	def _get_single_financial_model(self, project: Project, scenario_id: str):
		"""Get a single financial model with optimized query"""
		model_class = self._get_model_class(project)
		
		try:
			# This query will use the composite index efficiently
			return model_class.objects.select_related('depends_on').get(
				project=project,
				identifier=scenario_id
			)
		except model_class.DoesNotExist:
			scenario_config = self.FINANCIAL_MODEL_SCENARIOS.get(scenario_id)
			if scenario_config:
				return self._create_fm(project, scenario_id, scenario_config)
			else:
				raise ValueError(f"Unknown scenario: {scenario_id}")

	# Optimized method for bulk operations:
	def _bulk_get_or_create_models(self, project: Project, scenario_ids: list):
		"""Efficiently get or create multiple models"""
		model_class = self._get_model_class(project)
		
		# Get existing models in one query
		existing_models = model_class.objects.filter(
			project=project,
			identifier__in=scenario_ids
		).select_related('depends_on')
		
		existing_ids = {model.identifier for model in existing_models}
		missing_ids = set(scenario_ids) - existing_ids
		
		# Bulk create missing models if any
		if missing_ids:
			models_to_create = []
			for scenario_id in missing_ids:
				scenario_config = self.FINANCIAL_MODEL_SCENARIOS.get(scenario_id)
				if scenario_config:
					model = model_class(
						project=project,
						identifier=scenario_id,
						financial_model={}
					)
					models_to_create.append(model)
			
			if models_to_create:
				model_class.objects.bulk_create(models_to_create)
				# Re-fetch to get the created models with IDs
				existing_models = model_class.objects.filter(
					project=project,
					identifier__in=scenario_ids
				).select_related('depends_on')
		
		return {model.identifier: model for model in existing_models}
		
	"""@timer_decorator"""
	def _build_response_data(self, selected_fm, financial_models: Dict[str, Any]) -> JsonResponse:
		"""Build the JSON response data for both GET and POST requests"""
		# Generate dashboard data
		dashboard_data = self._generate_dashboard_data(selected_fm, financial_models)

		# Collect displayed metrics
		displayed_metrics = self._collect_displayed_metrics(financial_models)

		# Extract chart data
		charts_data = self._extract_charts_data(selected_fm)

		# Extract financial statements data

		financial_statements = self._extract_financial_statements(selected_fm)

		return self._prepare_json_response(
			selected_fm, 
			financial_models, 
			displayed_metrics, 
			dashboard_data, 
			charts_data, 
			financial_statements,

		)

	def _create_all_financial_models(self, project):
		"""
		Create financial models for all scenarios.

		Returns:
		dict: Dictionary mapping scenario IDs to their financial models
		"""
		financial_models = {}

		for scenario_id, scenario_config in self.FINANCIAL_MODEL_SCENARIOS.items():
			model = self._create_fm(project, scenario_id, scenario_config)
			financial_models[scenario_id] = model

		return financial_models


	def _get_selected_fm(self, scenario, financial_models):
		"""
		Retrieve the selected financial model or fall back to default.

		Args:
			financial_models (dict): All available financial models
			scenario (str): The scenario ID to select
			
		Returns:
			FinancialModel: The selected financial model
		"""
		return financial_models.get(scenario, financial_models['lender_base_case'])


	def _update_project_financials(self, project, financial_models):
		"""
		Update project with calculated financial metrics.

		Args:
			project: The project instance to update
			financial_models (dict): All financial models
		"""
		sponsor_model = financial_models['sponsor_base_case']

		# Update sponsor IRR
		sponsor_irr = sponsor_model.financial_model['dict_results']['Sensi_IRR']['Equity IRR']
		project.sponsor_irr = sponsor_irr * 100

		# Update valuation
		project.valuation = self._calculate_project_valuation(sponsor_model)

		project.save()


	def _extract_charts_data(self, selected_fm):
		"""
		Extract and format data needed for chart generation.

		Returns:
			dict: Chart data organized by type
		"""
		logger.info(f"Extracting charts data for model: {selected_fm.identifier}")
		
		charts_data_constr, charts_data_eoy, charts_data_sum_year = selected_fm.extract_values_for_charts()
		
		# Debug log the extracted data
		logger.info(f"charts_data_constr keys: {list(charts_data_constr.keys()) if charts_data_constr else 'None'}")
		logger.info(f"charts_data_eoy keys: {list(charts_data_eoy.keys()) if charts_data_eoy else 'None'}")
		logger.info(f"charts_data_sum_year keys: {list(charts_data_sum_year.keys()) if charts_data_sum_year else 'None'}")
		
		# Check if we have actual data
		if charts_data_sum_year and 'opex' in charts_data_sum_year:
			sample_opex = charts_data_sum_year['opex'].get('total', {})
			if sample_opex:
				first_value = list(sample_opex.values())[0] if sample_opex else 'No data'
				logger.info(f"Sample OPEX total first value: {first_value}")
		
		return {
			'construction': charts_data_constr,
			'end_of_year': charts_data_eoy,
			'sum_year': charts_data_sum_year,
		}


	def _calculate_project_valuation(self, sponsor_model):
		"""
		Calculate and return the project valuation.

		Args:
			sponsor_model: The sponsor base case financial model
			
		Returns:
			float: Calculated project valuation
		"""
		valuation_data = sponsor_model.financial_model['dict_results']['Valuation']
		valuation_keys = list(valuation_data.keys())

		# Get the second valuation key's value
		valuation_value = valuation_data[valuation_keys[1]]

		# Apply rounding logic (placeholder for actual calculation)
		rounded_value = 1000  # TODO: Implement actual valuation calculation

		return valuation_value



	"""@timer_decorator"""
	def _create_fm(self, project: Project, scenario_id: str, scenario_config: dict):
		"""
		Create or update a financial model based on the given scenario configuration.
		All models except Lender_base_case depend on Lender_base_case.
		"""
		model_class = self._get_model_class(project)
		
		# First ensure Lender_base_case exists as it's needed for dependency
		if scenario_id != 'lender_base_case':
			lender_base_case, lender_created = model_class.objects.get_or_create(
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
		model, created = model_class.objects.get_or_create(
			project=project,
			identifier=scenario_id,  # Use the mapping to get the identifier
			defaults={'financial_model': {}}
		)
		
		# Update the dependency
		model.depends_on = depends_on
		model.save()

		# Apply sensitivities based on the scenario configuration
		sensi_params = {}
		for param_name, project_field in scenario_config.get('sensitivities', {}).items():
			model_type = scenario_config['model_type']
			"""logger.error(model_type)"""
			
			# Determine proper parameter names based on model type
			if model_type == 'sponsor':
				# For sponsor models, use _sponsor suffix
				if param_name == 'production':
					sensi_params['sensi_production_sponsor'] = getattr(project, project_field)
					"""logger.error(sensi_params['sensi_production_sponsor'] )"""
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

	def _collect_displayed_metrics(self, financial_models):

		displayed_metrics = {
			"sponsor_IRR": f"{financial_models['sponsor_base_case'].financial_model['dict_results']['Sensi_IRR']['Equity IRR'] * 100:.2f}%",  # Percentage with 1 decimal
			"lender_DSCR": f"{financial_models['lender_base_case'].financial_model['dict_results']['Sensi']['Min DSCR']:.2f}x",  # 2 decimals + "x"
			"total_uses": f"{financial_models['lender_base_case'].financial_model['dict_uses_sources']['Uses']['Total']:,.1f}",  # Thousands separator + 1 decimal
			"gearing": financial_models['lender_base_case'].financial_model['dict_results']['Debt metrics']['Effective gearing'],  # Gearing as percentage
		
		}
		sidebar_data = financial_models['sponsor_base_case'].financial_model['dict_sidebar']
		
		displayed_metrics.update(sidebar_data)
		
		return displayed_metrics


	def _extract_financial_statements(self, selected_fm) -> Dict[str, Any]:
		"""Extract and package all financial statements data"""
		return {
			'financing_plan': selected_fm.extract_fs_financing_plan_data(),
			'financial_statements': selected_fm.extract_fs_financial_statements_data(),
			'balance_sheet': selected_fm.extract_fs_balance_sheet_data(),
			'debt_schedule': selected_fm.extract_fs_debt_schedule_data()

		}



	def _prepare_json_response(
		self, 
		selected_fm, 
		financial_models: Dict,
		displayed_metrics: Dict, 
		dashboard_data: Dict, 
		charts_data: Dict, 
		financial_statements:Dict,

	) -> JsonResponse:
		"""Prepare JSON response with all financial model data"""
		try:
			return JsonResponse({
				"df": selected_fm.financial_model,
				"dashboard_cards": dashboard_data['tables'],
				"table_sensi_diff": dashboard_data['sensi_diff'],
				"table_sensi_diff_IRR": dashboard_data['sensi_diff_irr'], 
				"charts_data_constr": charts_data['construction'],
				"df_annual": charts_data['sum_year'],
				"df_eoy": charts_data['end_of_year'],
				"fs_financing_plan": financial_statements['financing_plan'],
				"fs_balance_sheet": financial_statements['balance_sheet'],
				"fs_financial_statements": financial_statements['financial_statements'],
				"fs_debt_schedule": financial_statements['debt_schedule'],
			
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


	def _generate_dashboard_data(self, selected_fm, financial_models):
		"""
		Generate all dashboard tables and their difference calculations.

		Returns:
		dict: Contains dashboard tables and computed differences
		"""
		dashboard_data = self._build_dashboard(selected_fm, financial_models)

		return {
			'tables': dashboard_data,
			'sensi_diff': self._compute_differences(dashboard_data['Sensi']),
			'sensi_diff_irr': self._compute_differences(dashboard_data['Sensi_IRR'])
		}


	def _build_dashboard(
		self, 
		selected_fm, 
		financial_models: Dict[str, Any]
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
		
		data = selected_fm.financial_model

		return self._build_dashboard_data(
			data['dict_uses_sources'],
			data['dict_results'],
			table_sensi, 
			table_sensi_IRR,
		)

	"""@timer_decorator"""
	def _compute_differences(self, table_sensi):
		# Check if the table has a header row (key '')
		headers = table_sensi.get('', None)
		
		# Remove the header row if it exists and create the table data
		table_data = {k: v for k, v in table_sensi.items() if k != ''} if headers else table_sensi.copy()

		# Create a DataFrame from the remaining dictionary
		df = pd.DataFrame.from_dict(table_data, orient='index')
		
		# Check if the DataFrame is empty or has no valid columns
		if df.empty:
			logger.error("Warning: DataFrame is empty.")
			return table_sensi
		
		# Set column names if the header row exists and if it matches the number of columns
		if headers:
			if isinstance(headers, list) and len(headers) == len(df.columns):
				df.columns = headers
			else:
				logger.error("Warning: Header length mismatch or invalid header format.")
		
		# Check that we have enough columns (at least one numeric column and the Audit column)
		if df.shape[1] < 2:
			logger.error("Warning: Input dictionary has insufficient columns.")
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

		return replace_nan(result)

	def _build_dashboard_data(
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
			"Senior _create_fm": "{:.2%}",
			"Equity IRR": "{:.2%}",
			"Share capital IRR": "{:.2%}",
			"Shareholder loan IRR": "{:.2%}",
			"Project IRR (pre-tax)": "{:.2%}",
			"Project IRR (post-tax)": "{:.2%}"
		}
		
		# Add formatting for all Valuation metrics
		for key in dict_results.get('Valuation', {}).keys():
			if key.startswith("Discount factor"):
				output_formats[key] = "{:,.1f}"

		sorted_uses = dict(sorted(dict_uses_sources['Uses'].items(), key=lambda item: item[1], reverse=True))
		
		return {
			'Uses': build_dashboard_cards(sorted_uses, output_formats),
			'Sources': build_dashboard_cards(dict_uses_sources['Sources'], output_formats),
			'Project IRR': build_dashboard_cards(dict_results['Project IRR'], output_formats),
			'Equity metrics': build_dashboard_cards(dict_results['Equity metrics'], output_formats),
			'Debt metrics': build_dashboard_cards(dict_results['Debt metrics'], output_formats),
			'Audit': build_dashboard_cards(dict_results['Audit'], output_formats),
			'Valuation': build_dashboard_cards(dict_results['Valuation'], output_formats),
			'Sensi': build_dashboard_cards_sensi(table_sensi),
			'Sensi_IRR': build_dashboard_cards_sensi_sponsor(table_sensi_IRR),
		}

	def _project_form_changed(self, project_form):
		"""
		Return true if the user changed any assumptions of the project form, except for sensitivities assumptions.
		This is used to determine if all models need to be regenerated.
		"""
		# Get the project instance to check technology
		project = project_form.instance
		
		# Define fields that are considered sensitivity parameters
		excluded_fields = {
			'sensi_production', 'sensi_inflation', 'sensi_opex', 
			'sensi_production_sponsor', 'sensi_inflation_sponsor', 'sensi_opex_sponsor', 
			'sponsor_irr', 'valuation',
		}
		
		# Add technology-specific fields that should be excluded based on current technology
		if project.technology and "Solar" in project.technology:
			# Exclude wind-specific fields for solar projects
			excluded_fields.update({
				'wind_turbine_installed', 'capacity_per_turbine', 'dev_tax_taxable_base_wind'
			})
		elif project.technology == "Wind":
			# Exclude solar-specific fields for wind projects
			excluded_fields.update({
				'panels_capacity', 'annual_degradation', 'panels_surface',
				'dev_tax_taxable_base_solar', 'archeological_tax_base_solar', 'archeological_tax'
			})
		
		# Get all changed fields excluding sensitivity parameters and irrelevant technology fields
		changed_fields = set(project_form.changed_data) - excluded_fields
				
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
		result = sensitivity_type in changed_fields
		
		return result

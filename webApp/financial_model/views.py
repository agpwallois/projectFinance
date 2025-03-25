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

	SCENARIO_MAP = {
		'Lender_base_case': "Lender Base Case",
		'Lender_sensi_prod': "sensi_production",
		'Lender_sensi_inf': "sensi_inflation", 
		'Lender_sensi_opex': "sensi_opex",
		'Sponsor_base_case': "sponsor",
		'Sponsor_sensi_prod': "sensi_production_sponsor",
		'Sponsor_sensi_inf': "sensi_inflation_sponsor",
		'Sponsor_sensi_opex': "sensi_opex_sponsor",

	}

	""" GET METHOD """

	def get(self, request, id: int):
		"""Handle GET requests for financial model data"""    
		project = get_object_or_404(Project, id=id)
		context = {'project_form': ProjectForm(instance=project), 'project': project}
	
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return self._handle_ajax_request(request, project)
			
		return render(request, "financial_model/project_view.html", context)

	def _handle_ajax_request(self, request, project: Project) -> JsonResponse:
		"""Process AJAX requests for financial model data"""
		"""scenario = request.GET.get('scenario')"""
		scenario = "Lender_base_case"
		financial_models = self._get_financial_models(project)
		selected_model = financial_models.get(scenario)
		
		if not selected_model:
			return JsonResponse({'error': 'Invalid scenario'}, status=400)
			
		dashboard_data = self._build_dashboard(selected_model, financial_models)
		table_sensi_diff = self._compute_differences(dashboard_data['Sensi'])
		table_sensi_diff_IRR = self._compute_differences(dashboard_data['Sensi_IRR'])

		charts_data_constr, charts_data_eoy, charts_data_sum_year = selected_model.extract_values_for_charts()
		
		return self._prepare_json_response(selected_model, dashboard_data, table_sensi_diff, table_sensi_diff_IRR, charts_data_constr, charts_data_eoy, charts_data_sum_year)

	def _get_financial_models(self, project: Project) -> Dict[str, SolarFinancialModel]:
		"""Retrieve all financial models for a project"""
		financial_models = {}
		
		for scenario_id, model_type in self.SCENARIO_MAP.items():
			try:
				model = SolarFinancialModel.objects.get(
					project=project, 
					identifier=model_type
				)
				financial_models[scenario_id] = model
			except SolarFinancialModel.DoesNotExist:
				# Create missing models on demand
				model = self._create_model(project, model_type)
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
		scenario = "Lender_base_case"
		return self._create_financial_models(request, project, project_form, scenario)

	def _create_financial_models(self, request, project, project_form, scenario):
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
		return self._prepare_json_response(selected_model, dashboard_tables, table_sensi_diff, table_sensi_diff_IRR, charts_data_constr, charts_data_eoy, charts_data_sum_year)
		
	def _create_model(self, project: Project, model_type: str) -> SolarFinancialModel:
		"""Create or update a financial model of the specified type"""
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
		
		return model

	""" COMMON GET POST METHODS """

	def _prepare_json_response(
		self, 
		model: SolarFinancialModel, 
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
				"sidebar_data": model.financial_model['dict_sidebar']
			}, safe=False)
		except Exception as e:
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
			if key.startswith("Lender")
		}


		table_sensi_IRR = {
			key: model.financial_model['dict_results']['Sensi_IRR']
			for key, model in financial_models.items()
			if key.startswith("Sponsor")
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
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


from .views_helpers import (
	build_dashboard_table,
	build_dashboard_table_sensi,

)

import json

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

	def get(self, request, id):
		project = get_object_or_404(Project, id=id)
		project_form = ProjectForm(instance=project)

		context = {
			'project_form': project_form,
			'project': project,
		}

		scenario_identifier_selected = request.GET.get('scenario')
		
		# Check for AJAX request
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':

			# Retrieve financial models using a loop
			identifiers = {
				'RadioScenario1': "Lender Base Case",
				'RadioScenario2': "sensi_production",
				'RadioScenario3': "sensi_inflation",
				'RadioScenario4': "sensi_opex",
				'RadioScenario5': "sponsor_production_choice",
			}


			financial_models = {
				key: SolarFinancialModel.objects.get(project=project, identifier=value)
				for key, value in identifiers.items()
			}

			fm_selected = financial_models.get(scenario_identifier_selected)

			# Build dashboard tables and charts data
			dashboard_tables = self.build_dashboard(
				fm_selected, 
				financial_models
			)
			
			charts_data_constr, charts_data_eoy, charts_data_sum_year = fm_selected.extract_values_for_charts()
			
			# Return JSON response for AJAX
			return self.prepare_json_response(fm_selected, dashboard_tables, charts_data_constr, charts_data_sum_year, charts_data_eoy)

		# Render HTML template for initial page load
		return render(request, "financial_model/project_view.html", context)

	def post(self, request, id):
		project = get_object_or_404(Project, id=id)
		project_form = ProjectForm(request.POST, instance=project)

		# Capture the selected scenario from POST data
		scenario_identifier_selected = request.POST.get('scenario')

		if not project_form.is_valid():
			return JsonResponse({'error': project_form.errors.as_json()}, status=400)

		# Pass the selected scenario to the method handling the financial models
		return self.get_or_create_financial_models(request, project, project_form, scenario_identifier_selected)

	"""def create_lender_case(request):
		if request.POST['technology'].startswith('Solar'):
			return SolarFinancialModel(request)
		return WindFinancialModel(request)"""

	def project_form_changed(self, project_form):
		# Return true if the user changed any assumptions of the project form, except for sensitivities assumptions
		excluded_fields = {'sensi_production', 'sensi_inflation', 'sensi_opex'}
		changed_fields = set(project_form.changed_data) - excluded_fields
		return bool(changed_fields)

	def project_form_sensi_changed(self, project_form, sensitivity_type):
		# Convert the changed data to a set
		changed_fields = set(project_form.changed_data)

		# Check if sensitivity_type is in the set of changed fields
		if sensitivity_type in changed_fields:
			
			return True
		return False

	def get_or_create_financial_models(self, request, project, project_form, scenario_identifier_selected):
		# Step 1: Get or create the lender base case financial model
		fm_lender_case, created = self.get_or_create_lender_case(project)
		

		
		# Step 2: Update the lender base case if there are changes of assumptions and save new assumptions
		if self.project_form_changed(project_form):
			fm_lender_case.create_or_update_lender_financial_model()
			project_form.save()

		# Step 3: Get and update or create sensitivity financial models
		sensitivity_models  = self.get_or_create_sensitivities(project, project_form, fm_lender_case, created)


		# Retrieve financial models using a loop
		identifiers = {
			'RadioScenario1': "Lender Base Case",
			'RadioScenario2': "sensi_production",
			'RadioScenario3': "sensi_inflation",
			'RadioScenario4': "sensi_opex",
			'RadioScenario5': "sponsor_production_choice",
		}

		financial_models = {
			key: SolarFinancialModel.objects.get(project=project, identifier=value)
			for key, value in identifiers.items()
		}

		fm_selected = financial_models.get(scenario_identifier_selected)

		# Step 5: Generate the dashboard tables
		dashboard_tables = self.build_dashboard(fm_selected, financial_models)

		# Step 6: Format data for charts
		charts_data_constr, charts_data_eoy, charts_data_sum_year = fm_selected.extract_values_for_charts()


		# Step 7: Prepare and return the JSON response
		return self.prepare_json_response(fm_selected, dashboard_tables, charts_data_constr, charts_data_sum_year, charts_data_eoy)

	def get_or_create_lender_case(self, project):
		return SolarFinancialModel.objects.get_or_create(
			project=project,
			identifier="Lender Base Case",
			defaults={'financial_model': {}}
		)

	def get_or_create_sensitivities(self, project, project_form, fm_lender_case, created):
		# Create or retrieve sensitivity models and store them in a dictionary
		sensitivity_identifiers = [
			"sensi_production",
			"sensi_inflation",			
			"sensi_opex",
			"sponsor_production_choice",
		]

		financial_models = {
			sensitivity: self.copy_lender_case_and_apply_sensitivity(fm_lender_case, project, created, project_form, sensitivity)
			for sensitivity in sensitivity_identifiers
			}
		
		return financial_models

	def copy_lender_case_and_apply_sensitivity(self, fm_lender_case, project, created, project_form, sensitivity_type):
		
		# Copy an instance of SolarFinancialModel and modify its identifier.
		if created :
			financial_model_sensi = copy.deepcopy(fm_lender_case)
			financial_model_sensi.apply_sensitivity_and_rerun_financial_model(sensitivity_type)

			# Set a new identifier for the copied instance
			financial_model_sensi.identifier = sensitivity_type

			# Set primary key and ID to None to create a new database entry
			financial_model_sensi.pk = None
			financial_model_sensi.id = None
			financial_model_sensi._state.adding = True

			# Save the new instance to the database
			financial_model_sensi.save()

		# Update the sensitivity if it already exists and an assumption has changed
		elif self.project_form_changed(project_form) or self.project_form_sensi_changed(project_form, sensitivity_type): 
			
			financial_model_sensi = SolarFinancialModel.objects.get(
							project=project,
							identifier=sensitivity_type,
							)

			financial_model_sensi.apply_sensitivity_and_rerun_financial_model(sensitivity_type)
			financial_model_sensi.save()

		else:

			financial_model_sensi = SolarFinancialModel.objects.get(
							project=project,
							identifier=sensitivity_type,
							)

		return financial_model_sensi

	def build_dashboard(self, fm_selected, financial_models):
		# Use dictionary comprehension to extract the Sensi values
		table_sensi = {
			key: model.financial_model['dict_results']['Sensi']
			for key, model in financial_models.items()
		}

		# Retrieve the necessary data from the selected financial model
		data = fm_selected.financial_model

		return self.build_dashboard_tables(
			data['dict_uses_sources'],
			data['dict_results'],
			table_sensi, 
		)

	def build_dashboard_tables(self, dict_uses_sources, dict_results, table_sensi):

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

		dashboard_tables = {
			'Uses': build_dashboard_table(dict_uses_sources['Uses'], output_table_formats),
			'Sources': build_dashboard_table(dict_uses_sources['Sources'], output_table_formats),
			'Project IRR': build_dashboard_table(dict_results['Project IRR'], output_table_formats),
			'Equity metrics': build_dashboard_table(dict_results['Equity metrics'], output_table_formats),
			'Debt metrics': build_dashboard_table(dict_results['Debt metrics'], output_table_formats),
			'Audit': build_dashboard_table(dict_results['Audit'], output_table_formats),
			'Valuation': build_dashboard_table(dict_results['Valuation'], output_table_formats),
			'Sensi': build_dashboard_table_sensi(table_sensi),
		}
			
		return dashboard_tables

	def prepare_json_response(self, fm_selected, dashboard_tables, charts_data_constr, charts_data_sum_year, charts_data_eoy):
		try:
			return JsonResponse({
				"df": fm_selected.financial_model,
				"tables": dashboard_tables,
				"charts_data_constr": charts_data_constr,
				"df_annual": charts_data_sum_year,
				"df_eoy": charts_data_eoy,
				"sidebar_data": fm_selected.financial_model['dict_sidebar'],



			}, safe=False, status=200)
		except Exception as e:
			return self.handle_exception(e)

	def handle_exception(self, e):
		traceback_info = traceback.extract_tb(e.__traceback__)
		last_trace = traceback_info[-1]
		error_data = {
			'error_type': e.__class__.__name__,
			'message': str(e),
			'line_number': last_trace.lineno
		}
		return JsonResponse(error_data, safe=False, status=400)




"""to display in consolelog the attributes of the objects

		attributes_lender_case = {
			key: value
			for key, value in fm_lender_case.__dict__.items()
			if not key.startswith('_') and not isinstance(value, (np.ndarray, pd.Series, np.bool_))
		}

		attributes_sensi_production = {
			key: value
			for key, value in fm_sensi_production.__dict__.items()
			if not key.startswith('_') and not isinstance(value, (np.ndarray, pd.Series, np.bool_))
		}



		attributes_sensi_opex = fm_sensi_opex.__dict__
		attributes_sensi_inflation = fm_sensi_inflation.__dict__
		attributes_sensi_sponsor_case = fm_sponsor_case.__dict__	"""
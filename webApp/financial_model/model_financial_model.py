# Standard Library Imports
import datetime
import calendar
from decimal import Decimal
import copy
from collections import defaultdict
import json

# Third-Party Imports
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta

# Django Imports
from django.db import models

# Project Imports (Internal)
from .model_project import Project
from .financial_model_sections import * 
from .model_financial_model_helpers_charts import (
	extract_construction_values_for_charts,
	extract_EoY_values_for_charts,
	calc_annual_sum_for_charts,   
)
from .model_financial_model_helpers_dashboard import (
	create_dashboard_results,
)
import logging
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

logger = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
	def default(self, obj):

		if isinstance(obj, pd.Series):
			return obj.tolist()
		elif isinstance(obj, pd.Timestamp):
			return obj.strftime('%d/%m/%Y')
		elif isinstance(obj, Decimal):
			return float(obj)
		elif isinstance(obj, np.ndarray):
			return obj.tolist()
		elif isinstance(obj, np.integer):
			return int(obj)
		elif isinstance(obj, np.floating):
			return float(obj)
		elif isinstance(obj, np.bool_):
			return bool(obj)

		return super().default(obj)






from dataclasses import dataclass
from typing import List, Optional, Type
import numpy as np
from django.db import models

@dataclass
class FinancialModelParameters:
	"""Container for financial model initialization parameters."""
	model_type: str = 'lender'
	debt_sizing_sculpting: bool = True
	sensi_production: float = 0
	sensi_opex: float = 0
	sensi_inflation: float = 0
	sensi_production_sponsor: float = 0
	sensi_opex_sponsor: float = 0
	sensi_inflation_sponsor: float = 0

class FinancialModel(models.Model):
	"""
	Django model representing a financial model for solar projects with debt structuring capabilities.
	"""
	project = models.ForeignKey('Project', null=False, on_delete=models.CASCADE)
	financial_model = models.JSONField(default=dict, encoder=CustomJSONEncoder)
	model_type = models.CharField(max_length=255, default='default-identifier')
	sensitivity = models.CharField(max_length=255, default='default-identifier')
	senior_debt_amount = models.FloatField(default=1000.0)
	IRR = models.FloatField(default=10.0)
	identifier = models.CharField(max_length=255, default='default-identifier')
	valuation = models.FloatField(default=1000.0)
	depends_on = models.ForeignKey(
		'self', 
		null=True, 
		blank=True, 
		on_delete=models.SET_NULL, 
		related_name='dependent_models'
	)

	# Component initialization order
	STATIC_COMPONENTS = [
		FinancialModelAssumptions,
		FinancialModelDates,
		FinancialModelFlags,
		FinancialModelDays,
		FinancialModelTimes,
		FinancialModelProduction,
		FinancialModelConstructionCosts,
		FinancialModelIndexation,
		FinancialModelPrices,
		FinancialModelRevenues,
		FinancialModelOpex,
		FinancialModelEBITDA,
		FinancialModelWorkingCapital,
	]

	CALCULATIONS_BEFORE_DEBT = [
		FinancialModelFinancingPlan,
		FinancialModelSeniorDebt,
		FinancialModelUses,
		FinancialModelDepreciation,
		FinancialModelIncomeStatement,
		FinancialModelCashFlowStatement,
	]

	CALCULATIONS_AFTER_DEBT = [
		FinancialModelDSRA,
		FinancialModelAccounts,
		FinancialModelBalanceSheet,
		FinancialModelRatios,
		FinancialModelIRR,
		FinancialModelAudit,
	]


	def create_financial_model(self, **kwargs):
		"""Orchestrates the financial model building process."""

		params = FinancialModelParameters(**kwargs)
		self._initialize_components(params)
		
		FinancialModelDeclareVariables(self).declare_variables()
		
		if params.debt_sizing_sculpting:
			self._execute_debt_sizing_sculpting()
		else:
			self._apply_debt_from_dependency()
			
		self._finalize_model()

	def _initialize_components(self, params: FinancialModelParameters):
		"""Initialize all static components of the financial model."""
		for component_class in self.STATIC_COMPONENTS:
			component = component_class(self)
			
			if component_class == FinancialModelProduction:
				# Use the proper sensitivity parameter based on model type
				if params.model_type == 'sponsor':
					component.initialize(
						params.model_type, 
						sensi_production=params.sensi_production_sponsor/100
					)
				else:
					component.initialize(
						params.model_type, 
						sensi_production=params.sensi_production/100
					)
					
			elif component_class == FinancialModelIndexation:
				# Use the proper inflation sensitivity based on model type
				if params.model_type == 'sponsor':
					component.initialize(sensi_inflation=params.sensi_inflation_sponsor)
				else:
					component.initialize(sensi_inflation=params.sensi_inflation)
					
			elif component_class == FinancialModelPrices:
				component.initialize(params.model_type)
				
			elif component_class == FinancialModelOpex:
				# Use the proper opex sensitivity based on model type
				if params.model_type == 'sponsor':
					component.initialize(sensi_opex=params.sensi_opex_sponsor/100)
				else:
					component.initialize(sensi_opex=params.sensi_opex/100)
					
			else:
				component.initialize()

	def _execute_debt_sizing_sculpting(self):
		
		for _ in range(self.iteration):
			"""Update debt amount and repayment values from calculated targets."""
			self.senior_debt_amount = self.financial_model['debt_sizing']['target_debt_amount']
			self.financial_model['senior_debt']['repayments'] = self.financial_model['senior_debt']['target_repayments']

			"""Execute iterative debt sizing and sculpting process."""
			self._run_calculations(debt_sizing_sculpting=True)
			
			if self._has_converged():
				break
				
		self._persist_debt_data()

	def _apply_debt_from_dependency(self):
		"""
		Apply and copy debt values from the dependent model, then run calculations.
		"""
		if not self.depends_on:
			raise ValueError("No dependent model found for debt values")
		
		if not self.depends_on.recorded_results:
			raise ValueError("No recorded results found in dependent model")
		
		# Copy debt values from the dependent model
		self.senior_debt_amount = self.depends_on.recorded_results.debt_amount
		self.financial_model['senior_debt']['repayments'] = (
			self.depends_on.recorded_results.debt_schedule
		)
		
		# Run the necessary calculations
		for _ in range(self.iteration):
			self._run_calculations(debt_sizing_sculpting=False)

	def _run_calculations(self, debt_sizing_sculpting: bool):
		"""Execute all calculation components in order."""
		self._run_component_list(self.CALCULATIONS_BEFORE_DEBT)
		
		if debt_sizing_sculpting:
			self._calculate_senior_debt()
			
		self._run_component_list(self.CALCULATIONS_AFTER_DEBT)

	def _run_component_list(self, component_list: List[Type]):
		"""Initialize a list of components."""
		for component_class in component_list:
			component_class(self).initialize()

	def _calculate_senior_debt(self):
		"""Calculate senior debt size and repayments."""
		senior_debt_sizing = FinancialModelSeniorDebtSizing(self)
		senior_debt_sizing.calculate_senior_debt_amount()
		senior_debt_sizing.calculate_senior_debt_repayments()

	def _has_converged(self) -> bool:
		"""Check if debt calculations have converged."""
		debt_amount_delta = abs(
			self.senior_debt_amount - 
			self.financial_model['debt_sizing']['target_debt_amount']
		)

		if debt_amount_delta > 0.1:
			return False

		current = np.array(self.financial_model['senior_debt']['repayments'])
		target = np.array(self.financial_model['senior_debt']['target_repayments'])
		return np.allclose(current, target, atol=0.001)

	def _finalize_model(self):
		"""Prepare final outputs and save the model."""
		self._create_model_outputs()
		self._create_charts_data()
		self.save()

	def _create_model_outputs(self):
		"""Create all final model outputs."""
		self._create_dashboard_results()
		self._create_dynamic_sidebar_data()
		self._create_charts_data()

	def _create_charts_data(self):
		"""Format and store chart data."""
		self.financial_model['charts'] = {
			'senior_debt_draw_neg': -self.financial_model['injections']['senior_debt'],
			'share_capital_inj_neg': -self.financial_model['injections']['share_capital'],
			'shl_draw_neg': -self.financial_model['injections']['SHL'],
			'share_capital_inj_and_repay': (
				-self.financial_model['injections']['share_capital'] + 
				self.financial_model['share_capital']['repayments']
			),
			'shl_inj_and_repay': (
				-self.financial_model['injections']['SHL'] + 
				self.financial_model['SHL']['repayments']
			)
		}

	def _create_dashboard_results(self):
		"""Create dashboard results using the provided utility function."""
		create_dashboard_results(
			financial_model=self.financial_model,
			senior_debt_amount=self.senior_debt_amount,
			gearing_eff=self.gearing_eff
		)

	def _create_dynamic_sidebar_data(self):
		"""Create sidebar display data."""
		self.financial_model['dict_sidebar'] = {
			'COD': date_converter(self.COD),
			'installed_capacity': self.installed_capacity,
			'end_of_operations': date_converter(self.end_of_operations),
			'sum_seasonality': f"{round((sum(self.seasonality_inp) * 100), 2)}%",
			'sum_construction_costs': sum(self.construction_costs_assumptions),
			'liquidation': date_converter(self.liquidation_date),
			'date_debt_maturity': date_converter(self.debt_maturity),
			'price_elec_dict': self.price_elec_dict,
		}

	def extract_values_for_charts(self):
		"""Extract all required chart values."""
		return (
			extract_construction_values_for_charts(self.financial_model),
			extract_EoY_values_for_charts(self.financial_model),
			calc_annual_sum_for_charts(self.financial_model)
		)


	def _persist_debt_data(self):
		"""Save the final debt values to the database."""
		debt_data, created = DebtData.objects.get_or_create(financial_model=self)
		debt_data.debt_amount = self.senior_debt_amount
		debt_data.debt_schedule = convert_to_list(
			self.financial_model['senior_debt']['repayments']
		)
		debt_data.save()


	def save(self, *args, **kwargs):
		"""Override save to ensure proper JSON conversion."""
		self.financial_model = convert_to_list(self.financial_model)
		super().save(*args, **kwargs)



class DebtData(models.Model):
	"""
	DebtData model to store debt amount and schedule.
	"""
	financial_model = models.OneToOneField(FinancialModel, null=True, blank=True, on_delete=models.CASCADE, related_name='recorded_results')
	debt_amount = models.FloatField(null=True, blank=True)
	debt_schedule = models.JSONField(null=True, blank=True)  # Store schedule as a JSON list




def date_converter(date_str):
	return date_str.strftime("%d/%m/%Y")



def convert_to_list(data):
	if isinstance(data, pd.Series):
		return data.tolist()
	elif isinstance(data, pd.Timestamp):
		return data.strftime('%d/%m/%Y')
	elif isinstance(data, Decimal):
		return float(data)
	elif isinstance(data, np.ndarray):
		return data.tolist()
	elif isinstance(data, np.integer):
		return int(data)
	elif isinstance(data, np.floating):
		return float(data)
	elif isinstance(data, np.bool_):
		return bool(data)
	elif isinstance(data, dict):
		return {key: convert_to_list(value) for key, value in data.items()}
	elif isinstance(data, list):
		return [convert_to_list(item) for item in data]
	else:
		return data



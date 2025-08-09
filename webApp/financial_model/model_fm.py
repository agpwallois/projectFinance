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
from .model_fm_helpers_charts import (
	extract_construction_values_for_charts,
	extract_EoY_values_for_charts,
	calc_annual_sum_for_charts,  
)
from .model_fm_helpers_dashboard import (
	create_dashboard_results,
)

from .model_fm_helpers_fs_financing_plan import (
	extract_fs_financing_plan_data, 
)

from .model_fm_helpers_fs_balance_sheet import (
	extract_fs_balance_sheet_data, 
)

from .model_fm_helpers_fs_financial_statements import (
	extract_fs_financial_statements_data, 
)

from .model_fm_helpers_fs_debt_schedule import (
	extract_fs_debt_schedule_data, 
)





import logging
from concurrent.futures import ProcessPoolExecutor
import multiprocessing


from functools import wraps
import time


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


class CustomJSONEncoder(json.JSONEncoder):
	def encode(self, o):
		"""Override encode to handle NaN/Infinity at the top level."""
		if isinstance(o, float):
			if np.isnan(o) or np.isinf(o):
				return json.dumps(None)
		return super().encode(o)
	
	def default(self, obj):

		if isinstance(obj, pd.Series):
			return self._convert_to_serializable(obj.tolist())
		elif isinstance(obj, pd.Timestamp):
			return obj.strftime('%d/%m/%Y')
		elif isinstance(obj, Decimal):
			return float(obj)
		elif isinstance(obj, np.ndarray):
			return self._convert_to_serializable(obj.tolist())
		elif isinstance(obj, np.integer):
			return int(obj)
		elif isinstance(obj, np.floating):
			return self._convert_float(float(obj))
		elif isinstance(obj, np.bool_):
			return bool(obj)
		elif isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
			return None

		return super().default(obj)
	
	def _convert_float(self, value):
		"""Convert float values, handling NaN and Infinity."""
		if np.isnan(value):
			return None
		elif np.isinf(value):
			return None
		else:
			return value
	
	def _convert_to_serializable(self, lst):
		"""Recursively convert list elements to serializable format."""
		result = []
		for item in lst:
			if isinstance(item, float):
				result.append(self._convert_float(item))
			elif isinstance(item, list):
				result.append(self._convert_to_serializable(item))
			else:
				result.append(item)
		return result






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
		Assumptions,
		Dates,
		Flags,
		Days,
		Times,
		Production,
		ConstructionCosts,
		Indexation,
		Prices,
		Revenues,
		Opex,
		WorkingCapital,
	]

	CALCULATIONS_BEFORE_DEBT = [
		FinancingPlan,
		SeniorDebt,
		Uses,
		Depreciation,
	]

	CALCULATIONS_SENSI = [
		FinancialModelCalculator,
	]

	CALCULATIONS_FM_OUTPUTS = [
		BalanceSheet,
		Ratios,
		FinancialModelIRR,
		Audit,
	]

	def create_financial_model(self, **kwargs):
		"""Orchestrates the financial model building process."""

		params = FinancialModelParameters(**kwargs)
		self._initialize_components(params)
		
		DeclareVariables(self).declare_variables()
		
		if params.debt_sizing_sculpting:
			self._execute_debt_sizing_sculpting()
		else:
			self._apply_debt_from_dependency()
			
		self._finalize_model()

	"""@timer_decorator"""
	def _initialize_components(self, params: FinancialModelParameters):
		"""Initialize all static components of the financial model."""
		for component_class in self.STATIC_COMPONENTS:
			component = component_class(self)
			
			if component_class == Production:
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
					
			elif component_class == Indexation:
				# Use the proper inflation sensitivity based on model type
				if params.model_type == 'sponsor':
					component.initialize(sensi_inflation=params.sensi_inflation_sponsor)
				else:
					component.initialize(sensi_inflation=params.sensi_inflation)
					
			elif component_class == Prices:
				component.initialize(params.model_type)
				
			elif component_class == Opex:
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
	
			self._run_component_list(self.CALCULATIONS_BEFORE_DEBT)
			
			self._run_component_list(self.CALCULATIONS_SENSI)
			self._calculate_senior_debt()
			self._run_component_list(self.CALCULATIONS_FM_OUTPUTS)


			"""self._run_calculations(debt_sizing_sculpting=True)"""
			
			if self._structuring_case_has_converged():
				break
				
		"""self._persist_debt_data()"""

	def _apply_debt_from_dependency(self):
		"""
		Apply and copy debt values from the dependent model, then run calculations.
		"""
		if not self.depends_on:
			raise ValueError("No dependent model found for debt values")
		
		# Copy debt values directly from the dependent model
		self.senior_debt_amount = self.depends_on.senior_debt_amount
		self.financial_model['senior_debt']['repayments'] = (
			self.depends_on.financial_model['senior_debt']['repayments'].copy()
		)
		
		# Copy debt sizing information from dependent model if it exists
		if 'debt_sizing' in self.depends_on.financial_model:
			if 'debt_sizing' not in self.financial_model:
				self.financial_model['debt_sizing'] = {}
			# Copy the constraint value from the base case
			if 'constraint' in self.depends_on.financial_model['debt_sizing']:
				self.financial_model['debt_sizing']['constraint'] = (
					self.depends_on.financial_model['debt_sizing']['constraint']
				)


		self._copy_base_case_data_for_sensitivity()
		
		# Run only the components that need to be recalculated for sensitivity
		# Skip Uses since we copied it, but run the rest
		calculations_before_debt = [comp for comp in self.CALCULATIONS_BEFORE_DEBT
								if comp.__name__ not in ['Uses']]
		self._run_component_list(calculations_before_debt)
		self._run_component_list(self.CALCULATIONS_SENSI)
		self._run_component_list(self.CALCULATIONS_FM_OUTPUTS)		
		
		


	def _copy_base_case_data_for_sensitivity(self):
		"""Copy all necessary data from base case to ensure consistency in sensitivity models."""
		if not self.depends_on:
			return
		
		import pandas as pd
		import copy
		
		# Copy the entire uses data structure
		self._copy_uses_data_from_dependency()
		
		# Also copy any other data that should remain consistent with base case
		# This might include certain senior debt calculations that Uses depends on
		if 'senior_debt' in self.depends_on.financial_model:
			if 'senior_debt' not in self.financial_model:
				self.financial_model['senior_debt'] = {}
				
			# Copy specific senior debt items that should match base case
			base_senior_debt = self.depends_on.financial_model['senior_debt']
			for key in ['interests_construction', 'fees_construction', 'total_interests_fees']:
				if key in base_senior_debt:
					value = base_senior_debt[key]
					if isinstance(value, list):
						# Convert lists back to pandas Series
						self.financial_model['senior_debt'][key] = pd.Series(value)
					elif hasattr(value, 'copy'):
						self.financial_model['senior_debt'][key] = value.copy()
					else:
						self.financial_model['senior_debt'][key] = value
		
		logger.info("Copied base case data for sensitivity analysis")

	def _copy_senior_debt_data_for_uses(self):
		"""Copy senior debt data needed by Uses component from dependency."""
		# This method is no longer needed, functionality moved to _copy_base_case_data_for_sensitivity
		pass

	def _copy_uses_data_from_dependency(self):
		"""Copy all uses data from dependent model to ensure consistent project costs."""
		if not self.depends_on:
			return
		
		import pandas as pd
		import numpy as np
		import copy
		
		# Copy the entire uses dictionary to maintain complete consistency
		self.financial_model['uses'] = {}
		for key, value in self.depends_on.financial_model['uses'].items():
			if isinstance(value, list):
				# Convert lists back to pandas Series to preserve methods like .cumsum()
				self.financial_model['uses'][key] = pd.Series(value)
			elif hasattr(value, 'copy'):
				# For pandas Series, numpy arrays with copy method
				self.financial_model['uses'][key] = value.copy()
			elif isinstance(value, dict):
				# For dictionaries, use deepcopy to ensure independence
				self.financial_model['uses'][key] = copy.deepcopy(value)
			else:
				# For scalar values or immutable types
				self.financial_model['uses'][key] = value
		
		"""logger.info(f"Copied all uses data from dependent model. Total project costs: {pd.Series(self.financial_model['uses']['total']).sum():,.0f}")
		logger.debug(f"Copied uses keys: {list(self.financial_model['uses'].keys())}")"""

	def _run_component_list(self, component_list: List[Type]):
		"""Initialize a list of components."""
		for component_class in component_list:
			component_class(self).initialize()

	def _calculate_senior_debt(self):
		"""Calculate senior debt size and repayments."""
		senior_debt_sizing = SeniorDebtSizing(self)
		senior_debt_sizing.calculate_senior_debt_amount()
		senior_debt_sizing.calculate_senior_debt_repayments()

	def _structuring_case_has_converged(self) -> bool:
		"""Check if debt calculations have converged."""
		debt_amount_delta = abs(
			self.senior_debt_amount - 
			self.financial_model['debt_sizing']['target_debt_amount']
		)

		"""logger.error(debt_amount_delta)"""

		if debt_amount_delta > 0.01:
			return False

		current = np.array(self.financial_model['senior_debt']['repayments'])
		target = np.array(self.financial_model['senior_debt']['target_repayments'])

		return np.allclose(current, target, rtol=1e-5, atol=0.001)

	def _sensitivity_case_has_converged(self) -> bool:
		"""Check if debt calculations have converged."""

		
		return True
	
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
			'senior_debt_draw_neg': -self.financial_model['sources']['senior_debt'],
			'share_capital_inj_neg': -self.financial_model['sources']['share_capital'],
			'shl_draw_neg': -self.financial_model['sources']['SHL'],
			'share_capital_inj_and_repay': (
				-self.financial_model['sources']['share_capital'] + 
				self.financial_model['share_capital']['repayments']
			),
			'shl_inj_and_repay': (
				-self.financial_model['sources']['SHL'] + 
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
			'installed_capacity': f"{self.installed_capacity:,.1f}",
			'end_of_operations': date_converter(self.end_of_operations),
			'sum_seasonality': f"{round((sum(self.seasonality_inp) * 100), 2)}%",
			'sum_construction_costs': sum(self.construction_costs_assumptions),
			'liquidation': date_converter(self.liquidation_date),
			'date_debt_maturity': date_converter(self.debt_maturity),
			'price_elec_dict': self.price_elec_dict,
			'lender_prod_choice': self.lender_production_text,
			'sponsor_prod_choice': self.sponsor_production_text,
			'lender_mkt_price_choice': self.lender_mkt_price_choice_text,
			'sponsor_mkt_price_choice': self.sponsor_mkt_price_choice_text,
		}
		

	def extract_values_for_charts(self):
		"""Extract all required chart values."""
		return (
			extract_construction_values_for_charts(self.financial_model),
			extract_EoY_values_for_charts(self.financial_model),
			calc_annual_sum_for_charts(self.financial_model)
		)

	def extract_fs_financing_plan_data(self):
		"""Extract all required table values."""
		return extract_fs_financing_plan_data(self.financial_model)

	def extract_fs_balance_sheet_data(self):
		"""Extract all required table values."""
		return extract_fs_balance_sheet_data(self.financial_model)

	def extract_fs_financial_statements_data(self):
		"""Extract all required table values."""
		return extract_fs_financial_statements_data(self.financial_model)

	def extract_fs_debt_schedule_data(self):
		"""Extract all required table values."""
		return extract_fs_debt_schedule_data(self.financial_model)

	def save(self, *args, **kwargs):
		"""Override save to ensure proper JSON conversion."""
		import logging
		logger = logging.getLogger(__name__)
		
		# Log distribution account values before conversion
		if 'distr_account' in self.financial_model:
			distr = self.financial_model['distr_account']
			if 'balance_bop' in distr and 'balance_eop' in distr:
				logger.info("=== Distribution Account Values Before Save ===")
				# Check if it's already a list or still an array
				bop_data = distr['balance_bop']
				eop_data = distr['balance_eop']
				
				if isinstance(bop_data, (list, np.ndarray)) and isinstance(eop_data, (list, np.ndarray)):
					for i in range(min(10, len(bop_data))):
						bop = bop_data[i] if i < len(bop_data) else 0
						eop = eop_data[i] if i < len(eop_data) else 0
						prev_eop = eop_data[i-1] if i > 0 and i-1 < len(eop_data) else 0
						continuity = "✓" if i == 0 or abs(bop - prev_eop) < 0.01 else "✗"
						logger.info(f"Period {i}: BOP={bop:.2f}, EOP={eop:.2f}, Prev_EOP={prev_eop:.2f} {continuity}")
				else:
					logger.warning(f"Distribution account data types: BOP={type(bop_data)}, EOP={type(eop_data)}")
		
		self.financial_model = convert_to_list(self.financial_model)
		super().save(*args, **kwargs)





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



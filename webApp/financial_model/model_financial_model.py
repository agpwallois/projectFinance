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

class DebtData(models.Model):
	"""
	DebtData model to store debt amount and schedule.
	"""
	debt_amount = models.FloatField(null=True, blank=True)
	debt_schedule = models.JSONField(null=True, blank=True)  # Store schedule as a JSON list

	def record_debt_data(self, debt_amount, debt_schedule):
		"""
		Record the debt amount and schedule.
		:param debt_amount: Total debt amount.
		:param debt_schedule: Debt repayment schedule (e.g., list of payments).
		"""
		self.debt_amount = debt_amount
		self.debt_schedule = debt_schedule
		self.save()  # Persist changes to the database




class FinancialModel(models.Model):
	project = models.ForeignKey('Project', null=False, on_delete=models.CASCADE)
	financial_model = models.JSONField(default=dict, encoder=CustomJSONEncoder)
	senior_debt_amount = models.FloatField(default=1000.0)
	IRR = models.FloatField(default=10.0)
	identifier = models.CharField(max_length=255, default='default-identifier')
	valuation = models.FloatField(default=1000.0) 

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		
	def create_or_update_lender_financial_model(self):
		FinancialModelAssumptions(self).initialize()
		self._initialize_fm_static_series()
		self._initialize_and_save_fm(debt_sizing_sculpting=True)

	def apply_sensitivity_and_rerun_financial_model(self, sensitivity_type):
		FinancialModelAssumptions(self).initialize()
		# Apply the sensitivity to the copy of the Base Case financial model
		if sensitivity_type == 'sensi_production':
			FinancialModelProduction(self).initialize(sensi_production = self.sensi_production/100)
			"""FinancialModelIndexation(self).initialize(sensi_inflation = self.project.sensi_inflation/100)"""
			logger.error(self.project.sensi_production)
		
		elif sensitivity_type == 'sensi_inflation':
			FinancialModelIndexation(self).initialize(sensi_inflation = self.project.sensi_inflation/100)
		
		elif sensitivity_type == 'sensi_opex':
			FinancialModelOpex(self).initialize(sensi_opex = self.project.sensi_opex/100)
		
		elif sensitivity_type == 'sponsor_production_choice':
			self.financial_model['production']['total'] = self.project.p90_10y/1000 * pd.Series(self.financial_model['seasonality']) * self.financial_model['capacity']['after_degradation']
		
		else:
			pass	
		self._initialize_and_save_fm(debt_sizing_sculpting=False)

	def extract_values_for_charts(self):
		construction_values = extract_construction_values_for_charts(self.financial_model)
		eoy_values = extract_EoY_values_for_charts(self.financial_model)
		annual_sums = calc_annual_sum_for_charts(self.financial_model)
		return construction_values, eoy_values, annual_sums

	def _initialize_and_save_fm(self, debt_sizing_sculpting):
		self._init_fm_dynamic_series()
		if debt_sizing_sculpting:
			self._calculate_fm(debt_sizing_sculpting)
		else: 
			self._perform_calculations(debt_sizing_sculpting)
		self._create_financial_model_outputs()
		self._save()

	def _calculate_fm(self, debt_sizing_sculpting):
		FinancialModelDeclareVariables(self).declare_variables()
		# Loop until convergence between the target debt amount / debt amount; target debt repayment schedule / debt repayment schedule
		for _ in range(self.iteration):
			self._update_senior_debt_amount_and_repayment()
			self._perform_calculations(debt_sizing_sculpting)
			self._calc_convergence_tests()

	def _perform_calculations(self, debt_sizing_sculpting):
		self._perform_calculations_before_debt()
		if debt_sizing_sculpting:
			self._calc_senior_debt_size()
		self._perform_calculations_after_debt()
		
	def _create_financial_model_outputs(self):
		self._create_dashboard_results()
		self._create_dynamic_sidebar_data()
		self._format_charts_data()

	def _initialize_fm_static_series(self):
		"""
		Initializes all the static (ie not affected by sensitivities) series of the financial model. 
		These will not be recomputed if the instance initialized is a sensitivity financial model.
		"""
		static_series_initializers = [
			FinancialModelDates,
			FinancialModelFlags,
			FinancialModelDays,
			FinancialModelTimes,
			FinancialModelProduction,
			FinancialModelConstructionCosts,
		]
		for initializer in static_series_initializers:
			initializer(self).initialize()
		
	def _init_fm_dynamic_series(self):
		"""
		Initializes all the dynamic (ie affected by sensitivities) series of the financial model. 
		These need to be recomputed after a sensitivity is applied.		
		"""
		dynamic_series_initializers = [
			FinancialModelIndexation,
			FinancialModelPrices,
			FinancialModelRevenues,
			FinancialModelOpex,
			FinancialModelEBITDA,
			FinancialModelWorkingCapital,
		]
		for initializer in dynamic_series_initializers:
			initializer(self).initialize()

	def _update_senior_debt_amount_and_repayment(self):
		self.senior_debt_amount = self.financial_model['debt_sizing']['target_debt_amount']
		self.financial_model['senior_debt']['repayments'] = self.financial_model['senior_debt']['target_repayments']

	def _perform_calculations_before_debt(self):
		
		dynamic_initializers = [
			FinancialModelFinancingPlan,
			FinancialModelSeniorDebt,
			FinancialModelUses,
			FinancialModelDepreciation,
			FinancialModelIncomeStatement,
			FinancialModelCashFlowStatement,
		]
		for initializer in dynamic_initializers:
			initializer(self).initialize()

	def _calc_senior_debt_size(self):
		senior_debt_sizing = FinancialModelSeniorDebtSizing(self)
		senior_debt_sizing.calculate_senior_debt_amount()
		senior_debt_sizing.calculate_senior_debt_repayments()

	def _perform_calculations_after_debt(self):
				
		dynamic_initializers = [
			FinancialModelDSRA,
			FinancialModelAccounts,
			FinancialModelBalanceSheet,
			FinancialModelRatios,
			FinancialModelIRR,
			FinancialModelAudit,
		]
		for initializer in dynamic_initializers:
			initializer(self).initialize()

	def _calc_convergence_tests(self):
		debt_amount_not_converged = abs(self.senior_debt_amount - self.financial_model['debt_sizing']['target_debt_amount']) > 0.1
		difference = np.array(self.financial_model['senior_debt']['target_repayments']) - np.array(self.financial_model['senior_debt']['repayments'])
		debt_sculpting_not_converged = np.where(difference == 0, True, False)
		self.debt_sculpting_not_converged = np.any(np.logical_not(debt_sculpting_not_converged))
		 
	def _format_charts_data(self):

		self.financial_model['charts'] = {}

		self.financial_model['charts']['senior_debt_draw_neg'] = - self.financial_model['injections']['senior_debt']
		self.financial_model['charts']['share_capital_inj_neg'] = - self.financial_model['injections']['share_capital']
		self.financial_model['charts']['shl_draw_neg'] = - self.financial_model['injections']['SHL']
		self.financial_model['charts']['share_capital_inj_and_repay'] = - self.financial_model['injections']['share_capital'] + self.financial_model['share_capital']['repayments']
		self.financial_model['charts']['shl_inj_and_repay'] = - self.financial_model['injections']['SHL'] + self.financial_model['SHL']['repayments']


	def _save(self, *args, **kwargs):
		# Automatically convert types to lists in financial_model
		super().save(*args, **kwargs)


	def __deepcopy__(self, memo):
		# Create a new instance of this class
		new_instance = self.__class__.__new__(self.__class__)

		# Copy all attributes from self to copied_instance
		memo[id(self)] = new_instance

		# Iterate over all attributes in self.__dict__
		for key, value in self.__dict__.items():
			# Deep copy each attribute
			setattr(new_instance, key, copy.deepcopy(value, memo))

		return new_instance


	def _create_dashboard_results(self):

		create_dashboard_results(
			financial_model=self.financial_model,
			senior_debt_amount=self.senior_debt_amount,
			gearing_eff=self.gearing_eff
		)

	def _create_dynamic_sidebar_data(self):

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

	


def date_converter(date_str):
	return date_str.strftime("%d/%m/%Y")


"""self.financial_model = convert_to_list(self.financial_model)

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
		return data"""



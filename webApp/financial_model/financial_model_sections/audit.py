import pandas as pd
import numpy as np
from pyxirr import xirr
from dateutil.parser import ParserError
from dateutil import parser
import datetime


class FinancialModelAudit:
	def __init__(self, instance):
		self.instance = instance

	def initialize(self):
		self.instance.financial_model['audit'] = {}

		# Calculate financing plan and balance sheet checks
		self.instance.financial_model['audit']['financing_plan'] = self.instance.financial_model['uses']['total'] - self.instance.financial_model['injections']['total']
		self.instance.financial_model['audit']['balance_sheet'] = self.instance.financial_model['BS']['total_assets'] - self.instance.financial_model['BS']['total_liabilities']

		self.instance.financial_model['audit']['check_financing_plan'] = abs(self.instance.financial_model['audit']['financing_plan'].sum()) < 0.01
		self.instance.financial_model['audit']['check_balance_sheet'] = abs(self.instance.financial_model['audit']['balance_sheet'].sum()) < 0.01

		# Determine final repayment date of debt
		final_repayment_date_debt = find_last_payment_date(
			self.instance.financial_model['dates']['model']['end'],
			self.instance.financial_model['senior_debt']['balance_bop']
		)
		final_repayment_date_debt = pd.to_datetime(final_repayment_date_debt, dayfirst=True).strftime("%Y-%m-%d %H:%M:%S")
		final_repayment_date_debt = parser.parse(final_repayment_date_debt).date()

		# Calculate tenor of debt
		self.instance.financial_model['audit']['tenor_debt'] = calculate_tenor(final_repayment_date_debt, self.instance.project.start_construction)

		# Check debt maturity
		self.instance.financial_model['audit']['debt_maturity'] = (final_repayment_date_debt == self.instance.debt_maturity)

		self.instance.financial_model['audit']['check_all'] = (
			self.instance.financial_model['audit']['check_financing_plan'].all() and
			self.instance.financial_model['audit']['check_balance_sheet'].all() and
			self.instance.financial_model['audit']['debt_maturity']
		)


def calculate_tenor(final_repayment_date, construction_start):
	time_difference = final_repayment_date-construction_start
	tenor = round(time_difference.days / 365.25, 1)
	return tenor



def find_last_payment_date(series_end_period, boolean_array):
	boolean_array = boolean_array > 0.1
	new_array = [date if boolean else 0 for boolean, date in zip(boolean_array, series_end_period)]
	non_zero_dates = [date for date in new_array if date != 0]
	max_date = max(non_zero_dates)
	return max_date

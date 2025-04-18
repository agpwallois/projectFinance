from dataclasses import dataclass
from typing import Dict, List, Union, Optional
import pandas as pd
import numpy as np
from datetime import date, datetime
from dateutil import parser
from dataclasses import dataclass

@dataclass
class AuditResults:
	"""Contains the results of financial model audits."""
	financing_plan_diff: np.ndarray
	balance_sheet_diff: np.ndarray
	financing_plan_check: bool
	balance_sheet_check: bool
	debt_maturity_check: bool
	tenor_debt: float
	check_all: bool

class FinancialModelAudit:
	"""
	Performs audits and validations on financial models.
	
	This class checks for various financial conditions including:
	- Financing plan balance
	- Balance sheet equality
	- Debt maturity dates
	- Overall model consistency
	"""
	
	def __init__(self, instance):
		self.instance = instance
		self.model = instance.financial_model
		self.MATERIALITY_THRESHOLD = 0.01  # Threshold for numerical differences
		
	def initialize(self) -> None:
		"""
		Initialize audit calculations and store results.
		"""
		audit_results = self._perform_audit()
		self._store_audit_results(audit_results)
		
	def _perform_audit(self) -> AuditResults:
		"""
		Perform all audit checks and return results.
		
		Returns:
			AuditResults: Container with all audit check results
		"""
		# Calculate differences
		financing_plan_diff = self._calculate_financing_plan_difference()
		balance_sheet_diff = self._calculate_balance_sheet_difference()
		
		# Perform checks
		financing_plan_check = self._check_materiality(financing_plan_diff)
		balance_sheet_check = self._check_materiality(balance_sheet_diff)
		
		# Calculate debt related metrics
		final_repayment_date = self._determine_final_debt_repayment_date()
		tenor_debt = self._calculate_debt_tenor(final_repayment_date)
		debt_maturity_check = self._check_debt_maturity(final_repayment_date)
		
		# Combine all checks
		check_all = all([
			financing_plan_check,
			balance_sheet_check,
			debt_maturity_check
		])
		
		return AuditResults(
			financing_plan_diff=financing_plan_diff,
			balance_sheet_diff=balance_sheet_diff,
			financing_plan_check=financing_plan_check,
			balance_sheet_check=balance_sheet_check,
			debt_maturity_check=debt_maturity_check,
			tenor_debt=tenor_debt,
			check_all=check_all
		)
	
	def _calculate_financing_plan_difference(self) -> np.ndarray:
		"""
		Calculate difference between uses and sources in financing plan.
		
		Returns:
			np.ndarray: Differences in financing plan
		"""
		return (
			self.model['uses']['total'] -
			self.model['injections']['total']
		)
	
	def _calculate_balance_sheet_difference(self) -> np.ndarray:
		"""
		Calculate difference between assets and liabilities.
		
		Returns:
			np.ndarray: Differences in balance sheet
		"""
		return (
			self.model['BS']['total_assets'] -
			self.model['BS']['total_liabilities']
		)
	
	def _check_materiality(self, differences: np.ndarray) -> bool:
		"""
		Check if differences are within materiality threshold.
		
		Args:
			differences: Array of differences to check
			
		Returns:
			bool: True if all differences are within threshold
		"""
		return abs(differences.sum()) < self.MATERIALITY_THRESHOLD
	
	def _determine_final_debt_repayment_date(self) -> date:
		"""
		Find the last date where debt balance is positive.
		
		Returns:
			date: Final repayment date
		"""
		end_dates = self.model['dates']['model']['end']
		debt_balance = self.model['senior_debt']['balance_bop']
		
		# Find last date with positive balance
		mask = debt_balance > 0.1
		valid_dates = [date for date, is_valid in zip(end_dates, mask) if is_valid]
		
		if not valid_dates:
			raise ValueError("No valid debt repayment dates found")
			
		final_date = max(valid_dates)
		return self._parse_date(final_date)
	
	def _parse_date(self, date_str: str) -> date:
		"""
		Parse date string to date object.
		
		Args:
			date_str: Date string to parse
			
		Returns:
			date: Parsed date object
		"""
		try:
			parsed_date = pd.to_datetime(date_str, dayfirst=True)
			return parser.parse(parsed_date.strftime("%Y-%m-%d %H:%M:%S")).date()
		except ParserError as e:
			raise ValueError(f"Invalid date format: {date_str}") from e
	
	def _calculate_debt_tenor(self, final_repayment_date: date) -> float:
		"""
		Calculate debt tenor in years.
		
		Args:
			final_repayment_date: Final debt repayment date
			
		Returns:
			float: Debt tenor in years
		"""
		days_difference = (final_repayment_date - self.instance.project.start_construction).days
		return round(days_difference / 365.25, 1)
	
	def _check_debt_maturity(self, final_repayment_date: date) -> bool:
		"""
		Check if final repayment date matches expected debt maturity.
		
		Args:
			final_repayment_date: Actual final repayment date
			
		Returns:
			bool: True if dates match
		"""
		return final_repayment_date == self.instance.debt_maturity
	
	def _store_audit_results(self, results: AuditResults) -> None:
		"""
		Store audit results in the financial model.
		
		Args:
			results: Audit results to store
		"""
		self.model['audit'] = {
			'financing_plan': results.financing_plan_diff,
			'balance_sheet': results.balance_sheet_diff,
			'check_financing_plan': results.financing_plan_check,
			'check_balance_sheet': results.balance_sheet_check,
			'tenor_debt': results.tenor_debt,
			'debt_maturity': results.debt_maturity_check,
			'check_all': results.check_all
		}
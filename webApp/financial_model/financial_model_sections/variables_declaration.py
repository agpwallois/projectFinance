import logging
import numpy as np
import pandas as pd
from typing import Any

logger = logging.getLogger(__name__)


class DeclareVariables:
	"""
	A class that initializes and declares essential variables within the financial model,
	ensuring that all necessary structures (e.g., dictionaries and placeholder arrays)
	are set up before calculations are performed.
	"""

	def __init__(self, instance: Any) -> None:
		"""
		Initialize with an instance that includes:
			- financial_model: A dictionary containing sub-dictionaries like 'dates',
							   'construction_costs', etc.
			- project: An object with project-level attributes (e.g. debt_gearing_max).
		"""
		self.instance = instance

	def declare_variables(self) -> None:
		"""
		Declares and initializes a variety of variables used throughout the financial model,
		including arrays (of zeros/ones) for future computations and derived values
		such as target_debt_amount.
		"""
		fm = self.instance.financial_model
		project = self.instance.project

		# Determine the number of periods based on the model's end dates
		data_length = len(fm["dates"]["model"]["end"])

		# Basic instance-level initialization
		self.instance.optimised_devfee = 0
		self.instance.development_fee = np.full(data_length, 0)

		# Income Statement (IS)
		fm["IS"] = {}
		fm["IS"]["distributable_profit"] = np.full(data_length, 1)

		# Initialize sub-dictionaries in the financial_model
		fm["op_account"] = {}
		fm["senior_debt"] = {}
		fm["discount_factor"] = {}
		fm["assets"] = {}
		fm["liabilities"] = {}

		fm["distr_account"] = {}
		
		fm["share_capital"] = {}
		fm["audit"] = {}

		# Uses and their cumulative total
		fm["uses"] = {}
		fm["uses"]["total"] = fm["construction_costs"]["total"]
		fm["uses"]["total_cumul"] = fm["uses"]["total"].cumsum()

		# Shareholder Loan (SHL)
		fm["SHL"] = {
			"balance_bop": np.full(data_length, 1),
			"interests_construction": np.full(data_length, 0),
			"interests_operations": np.full(data_length, 0),
		}

		# Operating Account
		fm["op_account"]["balance_eop"] = np.full(data_length, 0)

		# Debt Service Reserve Account (DSRA)
		fm["DSRA"] = {
			"dsra_bop": np.full(data_length, 0),
			"dsra_eop": np.full(data_length, 0),

			"initial_funding": np.full(data_length, 0),
			"dsra_mov": np.full(data_length, 0),
			"dsra_additions": np.full(data_length, 0),
			"dsra_release": np.full(data_length, 0),

		}



		# Track maximum initial funding requirement
		self.instance.initial_funding_max = 0

		# Debt Sizing - target debt amount determined by gearing
		fm["debt_sizing"]["target_debt_amount"] = (
			fm["uses"]["total"].sum() * float(project.debt_gearing_max) / 100
		)

		# Senior Debt Repayments placeholder
		fm["senior_debt"]["target_repayments"] = np.full(data_length, 0)

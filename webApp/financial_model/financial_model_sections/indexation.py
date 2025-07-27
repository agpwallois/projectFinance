from decimal import Decimal
import pandas as pd


class Indexation:
	def __init__(self, instance):
		self.instance = instance
		self.financial_model = instance.financial_model

	def initialize(self, sensi_inflation=0):
		"""Initialize the indexation vectors with optional inflation sensitivity adjustment."""
		index_columns = self._get_index_columns()
		self._initialize_indexation_section()
		self._create_indexation_vectors(index_columns, sensi_inflation)

	def _get_index_columns(self):
		"""Return a mapping of index names to their corresponding columns."""
		return {
			'merchant': 'merchant_indexation',
			'contract': 'contract_indexation',
			'opex': 'opex_indexation',
			'lease': 'lease_indexation'
		}

	def _initialize_indexation_section(self):
		"""Ensure the 'indexation' section exists in the financial model."""
		if 'indexation' not in self.financial_model:
			self.financial_model['indexation'] = {}

	def _create_indexation_vectors(self, index_columns, sensi_inflation):
		"""Create indexation vectors for each index based on inflation sensitivity."""
		for indice_name, column_name in index_columns.items():
			indexation_rate = self._calculate_indexation_rate(indice_name, sensi_inflation)
			indexation_year = self._get_indexation_years(column_name)
			self.financial_model['indexation'][indice_name] = self._compute_indexation_vector(
				indexation_rate, indexation_year
			)

	def _calculate_indexation_rate(self, indice_name, sensi_inflation):
		"""Calculate the indexation rate with inflation sensitivity."""
		base_rate = getattr(self.instance.project, f'index_rate_{indice_name}')
		adjusted_rate = Decimal(base_rate) + Decimal(sensi_inflation)
		return float(adjusted_rate) / 100

	def _get_indexation_years(self, column_name):
		"""Retrieve the years from base dates for the given index."""
		return pd.Series(self.financial_model['time_series']['years_from_base_dates'][column_name])

	def _compute_indexation_vector(self, indexation_rate, indexation_year):
		"""Compute the indexation vector based on the rate and years."""
		return pd.Series((1 + indexation_rate) ** indexation_year).astype(float)

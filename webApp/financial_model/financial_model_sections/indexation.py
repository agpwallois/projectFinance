

import pandas as pd

class FinancialModelIndexation:
    def __init__(self, instance):
        self.instance = instance

    def initialize(self, sensi_inflation=0):
        # Create a dictionary to store the mapping between the index names and their corresponding columns
        index_columns = {
            'merchant': 'merchant_indexation',
            'contract': 'contract_indexation',
            'opex': 'opex_indexation',
            'lease': 'lease_indexation'
        }

        # Initialize the indexation dictionary
        self.instance.financial_model['indexation'] = {}

        # Iterate over the dictionary to create the indexation vectors
        for indice_name, column_name in index_columns.items():
            # Calculate the indexation rate with inflation sensitivity adjustment
            indexation_rate = getattr(self.instance.project, f'index_rate_{indice_name}') + sensi_inflation
            indexation_rate = float(indexation_rate) / 100

            # Create the indexation vector based on the years
            indexation_year = pd.Series(self.instance.financial_model['time_series']['years_from_base_dates'][column_name])
            self.instance.financial_model['indexation'][indice_name] = pd.Series((1 + indexation_rate) ** indexation_year).astype(float)

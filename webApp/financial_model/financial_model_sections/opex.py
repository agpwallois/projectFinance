
import numpy as np


class FinancialModelOpex:
    def __init__(self, instance):
        self.instance = instance

    def initialize(self, sensi_opex=0):
        # Initialize the operating expenses (opex) in the financial model
        self.instance.financial_model['opex'] = {}

        # Calculate operating costs with indexation and sensitivity adjustment
        self.instance.financial_model['opex']['operating_costs'] = self.instance.project.opex * \
            np.array(self.instance.financial_model['indexation']['opex']) * \
            np.array(self.instance.financial_model['time_series']['years_during_operations']) * \
            (1 + float(sensi_opex))

        # Calculate lease costs with indexation and sensitivity adjustment
        self.instance.financial_model['opex']['lease_costs'] = self.instance.project.lease * \
            np.array(self.instance.financial_model['indexation']['lease']) * \
            np.array(self.instance.financial_model['time_series']['years_during_operations']) * \
            (1 + float(sensi_opex))

        # Total operating expenses is the sum of operating and lease costs
        self.instance.financial_model['opex']['total'] = self.instance.financial_model['opex']['operating_costs'] + \
            self.instance.financial_model['opex']['lease_costs']

import pandas as pd
import numpy as np


class FinancialModelCashFlowStatement:
    def __init__(self, instance):
        self.instance = instance
        self.financial_model = instance.financial_model

    def initialize(self):
        # Ensure the 'CFS' section exists in the financial model
        if 'CFS' not in self.financial_model:
            self.financial_model['CFS'] = {}

        self._compute_cash_flows_operating()
        self._compute_cash_flows_investing()
        self._compute_cash_flows_financing()
        self._compute_cfads()

    def _compute_cash_flows_operating(self):
        ebitda = self.financial_model['EBITDA']['EBITDA']
        working_cap_movement = self.financial_model['working_cap']['working_cap_movement']
        corporate_tax = self.financial_model['IS']['corporate_income_tax']

        self.financial_model['CFS']['cash_flows_operating'] = (
            ebitda + working_cap_movement - corporate_tax
        )

    def _compute_cash_flows_investing(self):
        construction_costs = np.array(self.financial_model['uses']['construction'])
        development_fee = np.array(self.financial_model['uses']['development_fee'])

        self.financial_model['CFS']['cash_flows_investing'] = -(construction_costs + development_fee)

    def _compute_cash_flows_financing(self):
        senior_debt = self.financial_model['senior_debt']
        injections = self.financial_model['injections']

        self.financial_model['CFS']['cash_flows_financing'] = -(
            senior_debt['upfront_fee'] +
            senior_debt['interests_construction'] +
            senior_debt['commitment_fees'] -
            injections['senior_debt'] -
            injections['equity']
        )

    def _compute_cfads(self):
        cfs = self.financial_model['CFS']
        flags = self.financial_model['flags']

        cfs['CFADS'] = (
            cfs['cash_flows_operating'] +
            cfs['cash_flows_investing'] +
            cfs['cash_flows_financing']
        )
        cfs['CFADS_amo'] = cfs['CFADS'] * flags['debt_amo']
        cfs['CFADS_operations'] = cfs['CFADS'] * flags['operations']

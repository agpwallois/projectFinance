import numpy as np


class FinancialModelBalanceSheet:
    def __init__(self, instance):
        self.instance = instance
        self.financial_model = instance.financial_model

    def initialize(self):
        self._compute_ppe()
        self._compute_total_assets()
        self._compute_total_liabilities()

    def _compute_ppe(self):
        construction_costs = np.array(self.financial_model['construction_costs']['total']).cumsum()
        senior_debt_idc_and_fees = self.financial_model['uses']['senior_debt_idc_and_fees'].cumsum()
        interests_construction = self.financial_model['SHL']['interests_construction'].cumsum()
        depreciation = self.financial_model['IS']['depreciation'].cumsum()

        self.financial_model['BS']['PPE'] = (
            construction_costs + senior_debt_idc_and_fees + interests_construction - depreciation
        )

    def _compute_total_assets(self):
        bs = self.financial_model['BS']
        working_cap = self.financial_model['working_cap']
        dsra = self.financial_model['DSRA']
        distr_account = self.financial_model['distr_account']
        op_account = self.financial_model['op_account']

        bs['total_assets'] = (
            bs['PPE'] +
            working_cap['accounts_receivable_eop'] +
            dsra['dsra_eop'] +
            distr_account['balance_eop'] +
            op_account['balance_eop']
        )

    def _compute_total_liabilities(self):
        bs = self.financial_model['BS']
        shl = self.financial_model['SHL']
        share_capital = self.financial_model['share_capital']
        income_statement = self.financial_model['IS']
        senior_debt = self.financial_model['senior_debt']
        working_cap = self.financial_model['working_cap']

        bs['total_liabilities'] = (
            shl['balance_eop'] +
            share_capital['balance_eop'] +
            income_statement['retained_earnings_eop'] +
            senior_debt['balance_eop'] +
            working_cap['accounts_payable_eop']
        )

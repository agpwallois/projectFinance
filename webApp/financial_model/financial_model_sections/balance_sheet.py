import numpy as np


class BalanceSheet:
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

        self.financial_model['assets']['PPE'] = (
            construction_costs + senior_debt_idc_and_fees + interests_construction - depreciation
        )

    def _compute_total_assets(self):
        bs_assets = self.financial_model['assets']

        bs_assets['accounts_receivable'] = self.financial_model['working_cap']['accounts_receivable_eop']
        bs_assets['operating_account'] = self.financial_model['op_account']['balance_eop']
        bs_assets['DSRA'] = self.financial_model['DSRA']['dsra_eop']
        bs_assets['distribution_account'] = self.financial_model['distr_account']['balance_eop']

        bs_assets['total_assets'] = (
            bs_assets['PPE'] +
            bs_assets['accounts_receivable'] +
            bs_assets['DSRA'] +
            bs_assets['distribution_account'] +
            bs_assets['operating_account']
        )

    def _compute_total_liabilities(self):
        bs_liabilities = self.financial_model['liabilities']

        bs_liabilities['share_capital'] = self.financial_model['share_capital']['balance_eop']
        bs_liabilities['shareholder_loan'] = self.financial_model['SHL']['balance_eop']

        bs_liabilities['retained_earnings'] = self.financial_model['IS']['retained_earnings_eop']


        bs_liabilities['senior_debt'] = self.financial_model['senior_debt']['balance_eop']
        bs_liabilities['accounts_payable'] = self.financial_model['working_cap']['accounts_payable_eop']


        bs_liabilities['total_liabilities'] = (
            bs_liabilities['accounts_payable'] +
            bs_liabilities['senior_debt'] +
            bs_liabilities['shareholder_loan'] +
            bs_liabilities['share_capital'] +
            bs_liabilities['retained_earnings'] 



        )



import numpy as np


class FinancialModelBalanceSheet:
    def __init__(self, instance):
        self.instance = instance

    def initialize(self):
        self.instance.financial_model['BS']['PPE'] = ( 
            np.array(self.instance.financial_model['construction_costs']['total']).cumsum() + 
            self.instance.financial_model['uses']['senior_debt_idc_and_fees'].cumsum() + 
            self.instance.financial_model['SHL']['interests_construction'].cumsum() -
            self.instance.financial_model['IS']['depreciation'].cumsum()
        )

        self.instance.financial_model['BS']['total_assets'] = (
            self.instance.financial_model['BS']['PPE'] + 
            self.instance.financial_model['working_cap']['accounts_receivable_eop'] + 
            self.instance.financial_model['DSRA']['dsra_eop'] + 
            self.instance.financial_model['distr_account']['balance_eop'] + 
            self.instance.financial_model['op_account']['balance_eop']
        )

        self.instance.financial_model['BS']['total_liabilities'] = (
            self.instance.financial_model['SHL']['balance_eop'] + 
            self.instance.financial_model['share_capital']['balance_eop'] + 
            self.instance.financial_model['IS']['retained_earnings_eop'] + 
            self.instance.financial_model['senior_debt']['balance_eop'] + 
            self.instance.financial_model['working_cap']['accounts_payable_eop']
        )

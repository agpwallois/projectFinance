from collections import OrderedDict
import pandas as pd

# Ordering lists
INCOME_STATEMENT_ORDER = [
    'contracted_revenues', 'merchant_revenues', 'total_revenues',
    'operating_costs', 'lease_costs', 'total_opex',
    'EBITDA', 'depreciation', 'EBIT',
    'senior_debt_interests', 'shareholder_loan_interests', 'EBT',
    'corporate_income_tax', 'net_income',
    'retained_earnings_bop', 'retained_earnings_eop', 'distributable_profit'
]

OPERATING_ACCOUNT_ORDER = [
    'balance_bop', 'cash_flows_operating', 'construction_costs',
    'development_fee', 'cash_flows_investing', 'cash_flows_financing',
    'CFADS', 'senior_debt_interests_paid', 'senior_debt_repayments',
    'cash_available_for_distribution', 'transfers_distribution_account', 'balance_eop'
]

DISTRIBUTION_ACCOUNT_ORDER = [
    'balance_bop', 'transfers_distribution_account', 'cash_available_for_distribution',
    'shl_interests_paid', 'cash_available_for_shl_repayments', 'shl_repayments',
    'cash_available_for_dividends', 'dividends_paid',
    'cash_available_for_redemption', 'share_capital_repayments', 'balance_eop'
]

# Mapping for reordering
REORDER_MAPPING = {
    'annual_IS': INCOME_STATEMENT_ORDER,
    'annual_op_account': OPERATING_ACCOUNT_ORDER,
    'annual_distr_account': DISTRIBUTION_ACCOUNT_ORDER
}

def extract_fs_financial_statements_data(financial_model):
    """
    Calculates and reorders annual financial statements from a financial model dictionary.
    """
    def process_series(series, end_dates):
        """Helper function to sum values by year."""
        values = {}
        for i, end_date in enumerate(end_dates):
            if i < len(series):
                val = series[i]
                val = float(val) if isinstance(val, (int, float)) else 0.0
                year = end_date.year
                values[year] = values.get(year, 0.0) + val
        return values

    financial_statements = {
        'annual_IS': {},
        'annual_op_account': {},
        'annual_distr_account': {}
    }

    period_end_series = pd.to_datetime(
        financial_model['dates']['model']['end'],
        format='%d/%m/%Y',
        dayfirst=True
    )

    section_mapping = {
        'IS': 'annual_IS',
        'op_account': 'annual_op_account',
        'distr_account': 'annual_distr_account'
    }

    for source_section, output_key in section_mapping.items():
        if source_section in financial_model:
            section_data = financial_model[source_section]
            for sub_key, series in section_data.items():
                if isinstance(series, (list, tuple)):
                    result = process_series(series, period_end_series)
                    financial_statements[output_key][sub_key] = result

    # Reordering logic applied to all relevant sections
    for section_key, order_list in REORDER_MAPPING.items():
        original_section = financial_statements[section_key]
        reordered_section = OrderedDict()

        for key in order_list:
            if key in original_section:
                reordered_section[key] = original_section[key]
            else:
                # Optional: include empty dict if key missing
                reordered_section[key] = {}

        financial_statements[section_key] = reordered_section

    return financial_statements

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
    'balance_bop', 'EBITDA', 'working_cap_movement', 'corporate_tax', 'cash_flows_operating', 'construction_costs',
    'development_fee', 'senior_debt_interests_construction', 'senior_debt_upfront_fee', 'senior_debt_commitment_fees', 'reserves', 'local_taxes', 'cash_flows_investing', 
    'senior_debt', 'share_capital', 'shareholder_loan', 'cash_flows_financing',
    'CFADS', 'senior_debt_interests_paid', 'senior_debt_repayments', 'dsra_initial_funding', 'dsra_additions', 'dsra_releases',
    'transfers_distribution_account', 'balance_eop'
]

DISTRIBUTION_ACCOUNT_ORDER = [
    'balance_bop', 'transfers_distribution_account',
    'SHL_interests_paid', 'dividends_paid',
    'SHL_repayments',
    'share_capital_repayments', 'balance_eop'
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
    def process_series_sum(series, end_dates):
        """Helper function to sum values by year."""
        values = {}
        for i, end_date in enumerate(end_dates):
            if i < len(series):
                val = series[i]
                val = float(val) if isinstance(val, (int, float)) else 0.0
                year = end_date.year
                values[year] = values.get(year, 0.0) + val
        return values
    
    def process_series_eoy(series, end_dates):
        """Helper function to get year-end values (for balance_eop items)."""
        values = {}
        for i, end_date in enumerate(end_dates):
            if i < len(series):
                val = series[i]
                val = float(val) if isinstance(val, (int, float)) else 0.0
                year = end_date.year
                # Only keep the value if this is a year-end date (31st December)
                if end_date.month == 12 and end_date.day == 31:
                    values[year] = val
        return values
    
    def process_series_boy(series, start_dates):
        """Helper function to get beginning-of-year values (for balance_bop items).
        This takes the value as at 01/01 of each year."""
        values = {}
        for i, start_date in enumerate(start_dates):
            if i < len(series):
                val = series[i]
                val = float(val) if isinstance(val, (int, float)) else 0.0
                year = start_date.year
                # Only keep the value if this is a year start date (1st January)
                if start_date.month == 1 and start_date.day == 1:
                    values[year] = val
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
    
    period_start_series = pd.to_datetime(
        financial_model['dates']['model']['start'],
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
                    # Use appropriate processing based on the key type
                    if 'balance_bop' in sub_key.lower():
                        # Beginning of period balance - value as at 01/01 of current year
                        result = process_series_boy(series, period_start_series)
                    elif 'balance_eop' in sub_key.lower():
                        # End of period balance - value as at 31/12 of current year
                        result = process_series_eoy(series, period_end_series)
                    else:
                        # All other items - sum throughout the year
                        result = process_series_sum(series, period_end_series)
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

from collections import OrderedDict
import pandas as pd

# Ordering lists
ASSETS_ORDER = [
    'PPE', 'accounts_receivable', 'operating_account', 'DSRA',
    'distribution_account','total', 
]

LIABILITIES_ORDER = [
    'share_capital', 'shareholder_loan', 'retained_earnings',
    'senior_debt', 'accounts_payable','total', 
]

# Mapping for reordering
REORDER_MAPPING = {
    'annual_assets': ASSETS_ORDER,
    'annual_liabilities': LIABILITIES_ORDER,
}

def extract_fs_balance_sheet_data(financial_model):
    """
    Extracts year-end balance sheet values from a financial model dictionary.
    Returns values as at 31/12/N for each year.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("=== Extracting Balance Sheet Data ===")
    
    def process_series(series, end_dates):
        """Helper function to get year-end values."""
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

    financial_statements = {
        'annual_assets': {},
        'annual_liabilities': {},
    }

    period_end_series = pd.to_datetime(
        financial_model['dates']['model']['end'],
        format='%d/%m/%Y',
        dayfirst=True
    )


    section_mapping = {
        'assets': 'annual_assets',
        'liabilities': 'annual_liabilities'
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
        if section_key in financial_statements:
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
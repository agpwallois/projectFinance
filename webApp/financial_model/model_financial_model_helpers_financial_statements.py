from collections import defaultdict, OrderedDict
import pandas as pd

# Income Statement display order configuration
INCOME_STATEMENT_ORDER = [
    'contracted_revenues',
    'merchant_revenues', 
    'total',
    'EBITDA',
    'depreciation',
    'EBIT',
    'EBT',
    'corporate_income_tax',
    'net_income',
    'retained_earnings_bop',
    'retained_earnings_eop',
    'distributable_profit'
]



def calc_annual_financial_statements(financial_model):
    """
    Calculates the annual sum for IS, op_account, and distr_account
    from the financial_model dict.
    Returns a dictionary with keys: annual_IS, annual_op_account, annual_distr_account
    Each containing a nested dict: sub_key -> year -> sum
    
    Now automatically reorders annual_IS according to INCOME_STATEMENT_ORDER
    """
    print("Starting calc_annual_financial_statements")
    print(f"Input financial_model keys: {list(financial_model.keys())}")
    
    def process_series(series, end_dates):
        """Helper function to sum values by year"""
        values = {}
        for i, end_date in enumerate(end_dates):
            if i < len(series):
                val = series[i]
                val = float(val) if isinstance(val, (int, float)) else 0.0
                year = end_date.year
                if year not in values:
                    values[year] = 0.0
                values[year] += val
        return values

    # Initialize result dictionary with the desired structure
    financial_statements = {
        'annual_IS': {},
        'annual_op_account': {},
        'annual_distr_account': {}
    }

    # Convert period end series to datetime
    period_end_series = pd.to_datetime(
        financial_model['dates']['model']['end'],
        format='%d/%m/%Y',
        dayfirst=True
    )

    # Map source sections to output keys
    section_mapping = {
        'IS': 'annual_IS',
        'op_account': 'annual_op_account',
        'distr_account': 'annual_distr_account'
    }

    # Process each section
    for source_section, output_key in section_mapping.items():
        print(f"Processing section: {source_section}")
        if source_section in financial_model:
            section_data = financial_model[source_section]
            print(f"Section {source_section} keys: {list(section_data.keys())}")
            
            # Process all sub-keys in the section
            for sub_key, series in section_data.items():
                print(f"Processing {source_section}.{sub_key}")
                if isinstance(series, (list, tuple)):
                    result = process_series(series, period_end_series)
                    financial_statements[output_key][sub_key] = result
                    print(f"Added {sub_key}: {result}")
                else:
                    print(f"Skipped {sub_key} - not a list/tuple")
        else:
            print(f"Section {source_section} not found")

    print(f"Final annual_IS keys before reordering: {list(financial_statements['annual_IS'].keys())}")
    
    # REORDER annual_IS according to INCOME_STATEMENT_ORDER
    print("Reordering annual_IS according to INCOME_STATEMENT_ORDER")
    original_annual_IS = financial_statements['annual_IS'].copy()
    reordered_annual_IS = OrderedDict()
    
    for item in INCOME_STATEMENT_ORDER:
        if item in original_annual_IS:
            reordered_annual_IS[item] = original_annual_IS[item]
            print(f"Reordered: Added {item}")
        else:
            print(f"Reordered: Missing {item} - will be empty")
    
    # Replace the unordered dict with the ordered one
    financial_statements['annual_IS'] = reordered_annual_IS
    print(f"Final annual_IS keys after reordering: {list(financial_statements['annual_IS'].keys())}")
    
    return financial_statements






# Example usage and testing:
if __name__ == "__main__":
    # Example of how to use the functions
    pass
import pandas as pd
from collections import defaultdict

def extract_fs_financing_plan_data(financial_model):
    """
    Extracts construction-related values from a financial_model dict
    and returns them in a filtered format with summary values prepended.
    """
    # Get the list of flags from the data
    flags = financial_model['flags']['construction']
    
    # Helper function to filter data based on construction flags
    def filter_by_flags(data, apply_filter=True):
        if not apply_filter or not isinstance(data, list):
            return data
        return [data[i] for i, flag in enumerate(flags) if flag == 1]
    
    # Helper function to format dates to month/year
    def format_dates_to_month_year(dates):
        if not isinstance(dates, list):
            return dates
        
        formatted_dates = []
        for date in dates:
            if isinstance(date, str) and date:
                try:
                    # Parse the date and format to MM/YYYY
                    parsed_date = pd.to_datetime(date, dayfirst=True)
                    formatted_dates.append(parsed_date.strftime('%m/%Y'))
                except:
                    # If parsing fails, keep original
                    formatted_dates.append(date)
            else:
                formatted_dates.append(date)
        
        return formatted_dates
    
    # Helper function to add summary value as first element
    def add_summary_value(data, key, section):
        if not isinstance(data, list) or len(data) == 0:
            return data
        
        # Special cases for different keys/sections
        if section == 'fs_dates' or 'date' in key.lower():
            # For dates, add empty string as first value
            return ['Total'] + data
        elif key == 'gearing' or key == 'cumulative_project_costs':
            # For gearing_during_finplan, add last value as first value
            return [data[-1]] + data
        else:
            # For all other arrays, add sum as first value
            try:
                total = sum(data)
                return [total] + data
            except (TypeError, ValueError):
                # If sum fails (e.g., non-numeric data), just add empty string
                return [''] + data
    
    # Define all data paths in a single structure organized by sections
    data_structure = {
        'fs_dates': {
            '': financial_model['dates']['model']['end'],
        },
        'fs_uses': {
			'construction_costs': financial_model['uses']['construction'],
			'development fee (optimised)': financial_model['uses']['development_fee'],
			'senior_debt_interests_construction': financial_model['uses']['interests_construction'],
			'senior_debt_upfront_fee': financial_model['uses']['upfront_fee'],
			'senior_debt_commitment_fees': financial_model['uses']['commitment_fees'],
			'DSRA_initial_funding': financial_model['DSRA']['initial_funding'],
			'Total': financial_model['uses']['total'],
        },
        'fs_sources': {
            'share_capital': financial_model['sources']['share_capital'],
            'shareholder_loan': financial_model['sources']['SHL'],
            'senior_debt': financial_model['sources']['senior_debt'],
            'total': financial_model['sources']['total'],

        },
        'fs_gearing': {
            'cumulative_project_costs': financial_model['uses']['total_cumul'],
            'gearing': financial_model['gearing_during_finplan'],
        }
    }
    

    # Process all data with filtering and summary values
    extracted_values = {}
    for section, section_data in data_structure.items():
        extracted_values[section] = {}
        for key, data in section_data.items():
            # Apply filtering to all sections
            filtered_data = filter_by_flags(data, apply_filter=True)
            
            # Special handling for fs_dates section - format to month/year
            if section == 'fs_dates':
                filtered_data = format_dates_to_month_year(filtered_data)
            
            # Add summary value as first element
            extracted_values[section][key] = add_summary_value(filtered_data, key, section)
    
    return extracted_values
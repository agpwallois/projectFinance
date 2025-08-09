import pandas as pd
from collections import defaultdict


def extract_fs_debt_schedule_data(financial_model):
    """
    Extracts debt schedule data during operations periods only.
    Returns a table with model start dates, model end dates, senior debt repayments,
    senior debt interests, and the sum of repayments and interests.
    """
    # Get the operations flags to filter data
    debt_amo = financial_model['flags']['debt_amo']
    
    # Get date arrays
    model_start_dates = pd.Series(financial_model['dates']['model']['start'])
    model_end_dates = pd.Series(financial_model['dates']['model']['end'])
    
    # Get senior debt data
    senior_debt_repayments = pd.Series(financial_model['senior_debt']['repayments'])
    senior_debt_interests = pd.Series(financial_model['senior_debt']['interests'])
    
    # Filter data to operations periods only (where flags['operations'] == 1)
    operations_indices = [i for i, flag in enumerate(debt_amo) if flag == 1]
    
    if not operations_indices:
        # Return empty structure if no operations periods
        return {
            'model_start_dates': [],
            'model_end_dates': [],
            'senior_debt_repayments': [],
            'senior_debt_interests': [],
            'debt_service_total': []
        }
    
    # Filter all data to operations periods only
    filtered_start_dates = model_start_dates.iloc[operations_indices]
    filtered_end_dates = model_end_dates.iloc[operations_indices]
    filtered_repayments = senior_debt_repayments.iloc[operations_indices]
    filtered_interests = senior_debt_interests.iloc[operations_indices]
    
    # Calculate the sum of repayments and interests
    debt_service_total = filtered_repayments + filtered_interests
    
    # Convert to lists and format dates for display
    start_dates_formatted = []
    end_dates_formatted = []
    
    for date in filtered_start_dates:
        if isinstance(date, str):
            start_dates_formatted.append(date)
        else:
            start_dates_formatted.append(date.strftime('%d/%m/%Y'))
    
    for date in filtered_end_dates:
        if isinstance(date, str):
            end_dates_formatted.append(date)
        else:
            end_dates_formatted.append(date.strftime('%d/%m/%Y'))
    
    # Calculate totals for summary row
    total_repayments = filtered_repayments.sum()
    total_interests = filtered_interests.sum()
    total_debt_service = debt_service_total.sum()
    
    # Add summary row at the top (empty strings for dates, totals for financial data)
    start_dates_with_total = ['Total'] + start_dates_formatted
    end_dates_with_total = [''] + end_dates_formatted
    repayments_with_total = [total_repayments] + filtered_repayments.tolist()
    interests_with_total = [total_interests] + filtered_interests.tolist()
    debt_service_with_total = [total_debt_service] + debt_service_total.tolist()
    
    # Return the structured data
    return {
        'model_start_dates': start_dates_with_total,
        'model_end_dates': end_dates_with_total,
        'senior_debt_repayments': repayments_with_total,
        'senior_debt_interests': interests_with_total,
        'debt_service_total': debt_service_with_total
    }
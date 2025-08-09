import pandas as pd
from collections import defaultdict


def extract_construction_values_for_charts(financial_model):
	"""
	Extracts construction-related values from a financial_model dict
	and returns them in a filtered format.
	"""
	# Get the list of flags from the data
	flags = financial_model['flags']['construction']

	# List of paths to extract values from
	data_paths = {
		'dates_model_end': financial_model['dates']['model']['end'],
		'construction_costs_total': financial_model['construction_costs']['total'],
		'uses_total_cumul': financial_model['uses']['total_cumul'],
		'uses_senior_debt_idc_and_fees': financial_model['uses']['senior_debt_idc_and_fees'],
		'DSRA_initial_funding': financial_model['DSRA']['initial_funding'],
		'charts_share_capital_inj_neg': financial_model['charts']['share_capital_inj_neg'],
		'charts_shl_draw_neg': financial_model['charts']['shl_draw_neg'],
		'charts_senior_debt_draw_neg': financial_model['charts']['senior_debt_draw_neg'],
		'uses_total': financial_model['uses']['total'],
		'gearing_during_finplan': financial_model['gearing_during_finplan'],
	}

	extracted_values = {}

	for path_key, data in data_paths.items():
		# Ensure data is a list and filter it based on flags
		filtered_data = [data[i] for i in range(len(flags)) if flags[i] == 1]
		extracted_values[path_key] = filtered_data

	return extracted_values






def extract_EoY_values_for_charts(financial_model):
	"""
	Extracts end-of-year (EoY) values from the financial_model dict
	and returns them in a filtered format.
	"""
	import logging
	logger = logging.getLogger(__name__)
	logger.info("=== Extracting EoY Values for Charts ===")
	
	# Define the keys that need processing
	required_keys = {
		'senior_debt': ['balance_eop', 'DS_effective'],
		'distr_account': ['balance_eop'],
		'IRR': ['irr_curve'],
		'ratios': ['DSCR_effective', 'LLCR', 'PLCR'],
		'IS': ['retained_earnings_bop'],
		'DSRA': ['dsra_bop'],
		'capacity': ['degradation_factor'],

	}

	def process_series(series, end_dates):
		values = defaultdict(float)
		for i, end_date in enumerate(end_dates):
			if i < len(series):
				# Check if the date is December 31st
				if end_date.day == 31 and end_date.month == 12:
					val = series[i]
					val = float(val) if isinstance(val, (int, float)) else 0.0
					values[end_date.year] = val
		return values

	value_eoy = defaultdict(lambda: defaultdict(float))

	# Convert period end series to datetime
	period_end_series = pd.to_datetime(
		financial_model['dates']['model']['end'],
		format='%d/%m/%Y',
		dayfirst=True
	)

	# Iterate over required keys and their sub-keys
	for key, sub_keys in required_keys.items():
		for sub_key in sub_keys:
			# Check if key and sub_key exist
			if key in financial_model and sub_key in financial_model[key]:
				series = financial_model[key][sub_key]
				value_eoy[key][sub_key] = process_series(series, period_end_series)
				
				# Log distribution account values
				if key == 'distr_account' and sub_key == 'balance_eop':
					logger.info(f"Distribution Account EoY values: {value_eoy[key][sub_key]}")
					# Also log the raw series for first few periods
					logger.info(f"Distribution Account raw series (first 10): {series[:10] if isinstance(series, list) else 'Not a list'}")

	# Convert defaultdict to a regular dictionary for output
	return dict(value_eoy)



def calc_annual_sum_for_charts(financial_model):
    """
    Calculates the annual sum for chart series from the financial_model dict.
    Returns a nested dictionary keyed by (section -> sub_key -> year -> sum).
    """
    # Define the keys that need processing
    required_keys = {
        'opex': ['total', 'lease_costs'],
        'revenues': ['contract', 'merchant'],
        'senior_debt': ['DS_effective', 'interests_operations', 'repayments'],
        'charts': ['share_capital_inj_and_repay', 'shl_inj_and_repay'],
        'distr_account': ['dividends_paid'],
        'IRR': ['irr_curve'],
        'ratios': ['DSCR_effective', 'LLCR', 'PLCR'],
        'sources': ['senior_debt'],
        'share_capital': ['repayments'],
        'production': ['total'],

    }

    def process_series(series, end_dates):
        values = defaultdict(float)
        for i, end_date in enumerate(end_dates):
            if i < len(series):
                val = series[i]
                val = float(val) if isinstance(val, (int, float)) else 0.0
                values[end_date.year] += val
        return values

    # Start processing from the top level
    year_sum = defaultdict(lambda: defaultdict(float))

    # Convert period end series to datetime
    period_end_series = pd.to_datetime(
        financial_model['dates']['model']['end'],
        format='%d/%m/%Y',
        dayfirst=True
    )

    # Iterate over required keys and their sub-keys
    for key, sub_keys in required_keys.items():
        for sub_key in sub_keys:
            # Check if the key and sub_key exist
            if key in financial_model and sub_key in financial_model[key]:
                series = financial_model[key][sub_key]
                year_sum[key][sub_key] = process_series(series, period_end_series)

    return dict(year_sum)

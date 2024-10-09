from collections import defaultdict




def calc_sum_nested_dict(computation_displayed):
	all_sums = {}

	# Iterate through keys in the outer dictionary
	for dictkey, subkey_data in computation_displayed.items():
		sums = {}

		# Iterate through subkeys within each key
		for subkey, series in subkey_data.items():
			sum_val = sum([x for x in series if isinstance(x, (int, float))])
			sums[subkey] = sum_val

		# Store sums for the current key in the all_sums dictionary
		all_sums[dictkey] = sums

	return all_sums

def build_dashboard_table(results, specific_formats=None):
	table = {}

	# Default format to be applied if no specific format is provided
	default_format = "{:.1f}"

	for metric, data in results.items():
		# Determine the format to use for this metric
		fmt = specific_formats.get(metric, default_format) if specific_formats else default_format

		# Check if the format is None
		if fmt is None:
			formatted_val = data  # Keep the data as is
		elif isinstance(data, str):
			try:
				# Convert string to float and format it, if possible
				formatted_val = fmt.format(float(data))
			except (ValueError, TypeError):
				# If conversion fails, or format code is incompatible, keep the data as is
				formatted_val = data
		else:
			try:
			# Apply the formatting to non-string data
				formatted_val = fmt.format(data)
			except (ValueError, TypeError):
				formatted_val = data


		table[metric] = {0: formatted_val}

	return table

def build_dashboard_table_sensi(results):
	metrics = [("Min DSCR", "{:.2f}x"), ("Avg. DSCR", "{:.2f}x"), 
	("Min LLCR", "{:.2f}x"), ("Equity IRR", "{:.2%}"), 
	("Audit", None)]  # Specific format only for "Audit"

	dashboard_sensitivity_tables  = {"": [metric[0] for metric in metrics]}

	# Initialize an empty list to hold all rows including the blank one
	all_rows = []

	for scenario, data in results.items():
		scenario_data = []
		for j, value in enumerate(data.values()):
			format_string = metrics[j][1]
			if format_string:  # Apply formatting if specified
				formatted_value = format_string.format(value)
			else:
				formatted_value = value  # No formatting
			scenario_data.append(formatted_value)

		all_rows.append((scenario, scenario_data))

		# After the first scenario, append a blank row
		if len(all_rows) == 1:
			all_rows.append(('Blank Row', [''] * len(metrics)))

	# Add the processed rows to the dashboard_sensitivity_tables  dictionary
	for scenario, data in all_rows:
		dashboard_sensitivity_tables [scenario] = data

	return dashboard_sensitivity_tables 

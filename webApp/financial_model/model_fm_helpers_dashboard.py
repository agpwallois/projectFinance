
def create_dashboard_results(financial_model, senior_debt_amount, gearing_eff):
	"""
	Populates the financial_model dict with high-level 'Uses & Sources' 
	and 'Results' data for the dashboard.
	"""

	# Dictionary for uses and sources
	financial_model['dict_uses_sources'] = {
		"Uses": {
			"Construction costs": sum(financial_model['construction_costs']['total']),
			"Development fee": 0,
			"Debt interests & fees": sum(financial_model['uses']['senior_debt_idc_and_fees']),
			"Upfront fee": sum(financial_model['senior_debt']['upfront_fee']),
			"Commitment fees": sum(financial_model['senior_debt']['commitment_fees']),
			"IDC": sum(financial_model['senior_debt']['interests_construction']),
			"Local taxes": sum(financial_model['local_taxes']['total']),
			"Development tax": sum(financial_model['local_taxes']['development_tax']),
			"Archeological tax": sum(financial_model['local_taxes']['archeological_tax']),
			"Initial DSRA funding": sum(financial_model['DSRA']['initial_funding']),
			"Total": sum(financial_model['uses']['total']),
		},
		"Sources": {
			"Equity": sum(financial_model['sources']['equity']),
			"Share capital": sum(financial_model['sources']['share_capital']),
			"Shareholder loan": sum(financial_model['sources']['SHL']),
			"Senior debt": sum(financial_model['sources']['senior_debt']),
			"Total": sum(financial_model['sources']['total']),
		},
	}

	# Dictionary for results
	financial_model['dict_results'] = {
		"Equity metrics": {
			"Equity IRR": financial_model['IRR']['equity'],
			"Share capital IRR": financial_model['IRR']['share_capital'],
			"Shareholder loan IRR": financial_model['IRR']['SHL'],
			"Payback date": financial_model['IRR']['payback_date'],
			"Payback time": financial_model['IRR']['payback_time'],
		},
		"Sensi": {
			"Min DSCR": financial_model['ratios']['DSCR_min'],
			"Avg. DSCR": financial_model['ratios']['DSCR_avg'],
			"Min LLCR": financial_model['ratios']['LLCR_min'],
			"Audit": financial_model['audit']['check_all'],
		},
		"Sensi_IRR": {
			"Equity IRR": financial_model['IRR']['equity'],
			"Audit": financial_model['audit']['check_all'],
		},
		"Project IRR": {
			"Project IRR (pre-tax)": financial_model['IRR']['project_pre_tax'],
			"Project IRR (post-tax)": financial_model['IRR']['project_post_tax'],
		},
		"Debt metrics": {
			"Debt amount": f"{senior_debt_amount:,.1f}",
			"Effective gearing": f"{gearing_eff * 100:.1f}%",
			"Tenor (door-to-door)": financial_model['audit']['tenor_debt'],
			"Average DSCR": f"{financial_model['ratios']['DSCR_avg']:,.2f}x",
			"Minimum DSCR": f"{financial_model['ratios']['DSCR_min']:,.2f}x",
			"Minimum LLCR": f"{financial_model['ratios']['LLCR_min']:,.2f}x",
			"Senior Debt IRR": f"{financial_model['IRR']['senior_debt'] * 100:.2f}%",
		},
		"Audit": {
			"Financing plan": "true" if financial_model['audit']['check_financing_plan'] else "false",
			"Balance sheet": "true" if financial_model['audit']['check_balance_sheet'] else "false",
			"Debt maturity": "true" if financial_model['audit']['debt_maturity'] else "false",
		},
		"Valuation": {
			f"{financial_model['IRR']['eqt_discount_factor_less_1'] * 100:.2f}%":
				financial_model['IRR']['valuation_less_1'],

			f"{financial_model['IRR']['eqt_discount_factor'] * 100:.2f}%":
				financial_model['IRR']['valuation'],

			f"{financial_model['IRR']['eqt_discount_factor_plus_1'] * 100:.2f}%":
				financial_model['IRR']['valuation_plus_1'],
		},
	}


	"""			,
			"Audit": financial_model['audit']['check_all'],"""

	"""Constraint": financial_model['senior_debt']['debt_constraint'],"""


	# Return the financial_model if you want to do something with it
	return financial_model

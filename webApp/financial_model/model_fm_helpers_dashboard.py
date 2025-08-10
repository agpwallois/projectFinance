
def create_dashboard_results(financial_model, senior_debt_amount, gearing_eff):
	"""
	Populates the financial_model dict with high-level 'Uses & Sources' 
	and 'Results' data for the dashboard.
	"""

	# Dictionary for uses and sources
	financial_model['dict_uses_sources'] = {
		"Uses": {
			"Construction costs": sum(financial_model['construction_costs']['total']),
			"Development fee (if optimised)": sum(financial_model['uses']['development_fee']),
			"Debt upfront fee": sum(financial_model['senior_debt']['upfront_fee']),
			"Debt commitment fees": sum(financial_model['senior_debt']['commitment_fees']),
			"Debt interests": sum(financial_model['senior_debt']['interests_construction']),
			"Development tax": sum(financial_model['local_taxes']['development_tax']),
			"Archeological tax": sum(financial_model['local_taxes']['archeological_tax']),
			"Debt service reserve account initial funding": sum(financial_model['DSRA']['initial_funding']),
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
			"Debt amount constraint": financial_model['debt_sizing']['constraint'],
			"Effective gearing": f"{gearing_eff * 100:.1f}%",
			"Tenor (door-to-door)": financial_model['audit']['tenor_debt'],
			"Average DSCR": f"{financial_model['ratios']['DSCR_avg']:,.2f}x",
			"Minimum DSCR": f"{financial_model['ratios']['DSCR_min']:,.2f}x",
			"Minimum LLCR": f"{financial_model['ratios']['LLCR_min']:,.2f}x",
			"Debt IRR": f"{financial_model['IRR']['senior_debt'] * 100:.2f}%",
		},
		"Audit": {
			"Balance sheet balanced": "true" if financial_model['audit']['check_balance_sheet'] else "false",
			"Financing sources equals uses": "true" if financial_model['audit']['check_financing_plan'] else "false",
			"Debt repaid at maturity": "true" if financial_model['audit']['debt_maturity'] else "false",
			"Operating account balance ≥ 0": "true" if financial_model['audit']['check_operating_account'] else "false",
			"Distribution account balance ≥ 0": "true" if financial_model['audit']['check_distribution_account'] else "false",
			"DSRA is unused": "true" if financial_model['audit']['check_dsra_usage'] else "false",
		},
		"Valuation": {
			f"Discount factor @{financial_model['IRR']['eqt_discount_factor_less_1'] * 100:.2f}%":
				financial_model['IRR']['valuation_less_1'],

			f"Discount factor @{financial_model['IRR']['eqt_discount_factor'] * 100:.2f}%":
				financial_model['IRR']['valuation'],

			f"Discount factor @{financial_model['IRR']['eqt_discount_factor_plus_1'] * 100:.2f}%":
				financial_model['IRR']['valuation_plus_1'],
		},
	}


	"""			,
			"Audit": financial_model['audit']['check_all'],"""

	"""Constraint": financial_model['senior_debt']['debt_constraint'],"""


	# Return the financial_model if you want to do something with it
	return financial_model

# Standard library imports
import calendar
import datetime
import time

# Third-party imports
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
from dateutil import parser
from dateutil.parser import ParserError
from pyxirr import xirr

# Django imports
from django.http import JsonResponse
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

# Application-specific imports
from .forms import ProjectForm
from .models import Project
from .property_taxes import property_tax, tfpb_standard_reduction
import requests
from django.urls import reverse
from api_integration.views import get_data
import json
from .taxes import data


def testsimple(request):
    # Call the get_data function to get the response
    response = json.loads(get_data(request, "VERMENTON").content)
    taux_value = response['data']['results'][0]['taux']

    # Pass the 'response' data as a context variable to the template
    context = {
	'response_content': taux_value,

    }



    return render(request, 'testsimple.html', context)

def test(request, id):
	if request.method == "POST":
		return function_test(request, id)
	else:
		return handle_get_request(request, id)

def function_test(request,id):
	project = get_object_or_404(Project, id=id)
	project_form = ProjectForm(request.POST, instance=project)

	if not project_form.is_valid():
		return JsonResponse({'error': project_form.errors.as_json()}, status=400)
		
	try: 
		inputs = get_inputs(request)
		date_series = create_series(inputs)
		"""'Date Period start': format_date(date_series,'start_period').tolist(),"""
		"""'Date Period end': format_date(date_series,'end_period').tolist(),"""

		data_detailed = {
			'Date Period start': format_date(date_series,'start_period').tolist(),
			'Date Period end': format_date(date_series,'end_period').tolist(),

		}

		df = pd.DataFrame(data_detailed)
		
		test = datetime.datetime(2023,11,30) + relativedelta(months=+3) + pd.tseries.offsets.QuarterEnd()

		project_form.save()

		return JsonResponse({
			"df":data_detailed,
			"test":test,

			},safe=False, status=200)

	except Exception as e:
		
		error_data = {
			'error_type': e.__class__.__name__,
			'message': str(e)
		}

		return JsonResponse(error_data,safe=False, status=400)


################################################################

def project_list(request):
	projects = Project.objects.all()
	context = {'projects': projects}
	return render(request, 'projects_list.html', context)



def project_view(request, id):
	if request.method == "POST":
		return handle_post_request(request, id)
	else:
		return handle_get_request(request, id)

def handle_post_request(request,id):
	project = get_object_or_404(Project, id=id)
	project_form = ProjectForm(request.POST, instance=project)

	if not project_form.is_valid():
		return JsonResponse({'error': project_form.errors.as_json()}, status=400)
		
	try: 
		calculation_type = project_form.cleaned_data.get('calculation_type')
		inputs = get_inputs(request)
		date_series = create_series(inputs)
		params = create_params(inputs, date_series)
		flags = FlagCreator().create_flags(params)
		days_series = DaysCalculator(flags).calculate_days_series(params)
		time_series = create_time_series(date_series, days_series, flags)
		years_from_base_dates = calc_years_from_base_dates(days_series, time_series['days_in_year'])


		seasonality = create_seasonality_vector(request,date_series['start_period'],date_series['end_period'])
		
		# Creating constuction cost vector
		construction_costs,construction_costs_cumul,sum_construction_costs  = calc_construction_costs(request,inputs,flags)


		dev_tax_commune = import_dev_tax_commune(request, inputs['commune'])

		development_tax,archeological_tax,local_taxes = calc_local_taxes(request,inputs,flags,dev_tax_commune)
		development_tax_sum = sum(development_tax)
		archeological_tax_sum = sum(archeological_tax)
		sum_local_taxes = sum(local_taxes)

		gross_property_value = sum_construction_costs*property_tax[inputs['technology']]["Tax base"]*property_tax[inputs['technology']]["Annual property rental value"]*flags['operations']
		gross_land_value = inputs['lease']/property_tax[inputs['technology']]["Land discount rate"]*property_tax[inputs['technology']]["Annual land value"]*flags['operations']
		
		total_taxable_value = (gross_property_value+gross_land_value)*tfpb_standard_reduction
		tfpb = inputs['tfpb_rate']*total_taxable_value*flags['start_calendar_year']

		cfe_std_deduction = gross_property_value*inputs['cfe_discount_tax_base']
		cfe_tax_base = gross_property_value-cfe_std_deduction
		cfe_due = cfe_tax_base*inputs['cfe_rate']*flags['start_calendar_year']
		cfe_mgt_fee = cfe_tax_base*inputs['cfe_discount_tax_base']*flags['start_calendar_year']
		cfe_total_due = cfe_due+cfe_mgt_fee



		df_test = pd.DataFrame(data)
		if inputs['commune'] not in df_test["Commune"].values:
			tfpb_commune = 0
			tfpb_intercommunal = 0
			tfpb_specific_eqpt = 0		
		else: 
			index_of_abergement = data["Commune"].index(inputs['commune'])
			tfpb_commune = data["tfpb_commune"][index_of_abergement]
			tfpb_intercommunal = data["tfpb_intercommunal"][index_of_abergement]
			tfpb_specific_eqpt = data["tfpb_specific_eqpt"][index_of_abergement]

		capacity = calc_capacity(inputs, flags, time_series)
		installed_capacity = inputs['wind_turbine_installed']*1000*inputs['capacity_per_turbine']

		dict_scenario = create_scenario_dict(inputs)

		dfs = {}
		results_sensi = {}
		results_equity = {}
		results_projectIRR = {}
		results_debt = {}
		results_audit= {}

		for key in dict_scenario:
			
			production = calc_production(request,seasonality,capacity['after_degradation'], dict_scenario, key)*(1+dict_scenario[key]["sensi_prod"]) 
		
			index = calc_index(inputs, years_from_base_dates, dict_scenario, key)

			prices, dic_price_elec_keys = calc_prices(request, time_series, inputs, flags, index, dict_scenario, key)

			revenues = calc_revenues(production, prices, time_series)
			opex = inputs['opex']*index['opex']*time_series['years_during_operations']*(1+dict_scenario[key]["sensi_opex"])
			lease = inputs['lease']*index['lease']*time_series['years_during_operations']*(1+dict_scenario[key]["sensi_opex"])

			EBITDA = revenues['total']-opex-lease-tfpb
			EBITDA_margin =np.divide(EBITDA,revenues['total'],out=np.zeros_like(EBITDA), where=revenues['total']>0)
			working_cap = calc_wc(inputs, days_series,revenues,opex,lease)

			data_length = date_series['end_period'].size

			# Debt amount and repayment schedule is only computed in the Lender Case
			if key.startswith('Sensi'):
				target_debt_amount = target_debt_amount
				senior_debt_repayments_target = senior_debt_repayments_target
			else: 
				target_debt_amount = sum_construction_costs*inputs['debt_gearing_max']
				senior_debt_repayments_target = np.full(data_length, 0)
						
			optimised_devfee = 0

			development_fee = np.full(data_length, 0)
			total_costs=sum_construction_costs
			total_uses=construction_costs
			total_uses_cumul = total_uses.cumsum()

			distributable_profit = np.full(data_length, 1)

			SHL_balance_bop = np.full(data_length, 1)
			SHL_interests_construction= np.full(data_length, 0)
			SHL_interests_operations= np.full(data_length, 0)
			
			operating_account_eop= np.full(data_length, 0)
			dsra_bop= np.full(data_length, 0)
			DSRA_initial_funding= np.full(data_length, 0)
			DSRA_initial_funding_max=0
			DSRA = {}
			DSRA['dsra_mov']= np.full(data_length, 0)
	
			# DEBT LOOP #
			"""debt_amount_not_converged = True
			debt_sculpting_not_converged = True
			while debt_amount_not_converged or debt_sculpting_not_converged:"""

			for i in range(30):
				debt_amount = target_debt_amount
				senior_debt_repayments = senior_debt_repayments_target
					
				injections = calc_injections(inputs, total_uses_cumul, total_costs, total_uses, debt_amount)
				senior_debt = calc_senior_debt(injections['debt'], senior_debt_repayments, inputs, days_series, flags, debt_amount)
				senior_debt_fees_constr = calc_debt_fees_construction(senior_debt)
				capitalised_fees_cumul = calc_capitalised_fees(senior_debt,SHL_interests_construction)			
				total_uses=construction_costs+development_fee+senior_debt['senior_debt_idc']+senior_debt['upfront_fee']+senior_debt['commitment_fees']+DSRA_initial_funding+local_taxes
				total_uses_cumul = total_uses.cumsum()
				depreciation = calc_depreciation(sum_construction_costs, capitalised_fees_cumul, optimised_devfee, time_series, inputs,local_taxes)
				income_statement = calc_income_statement(depreciation, EBITDA, senior_debt['interests_operations'], SHL_interests_operations, inputs)				
				cf_statement = calc_cf_statement(EBITDA,working_cap,income_statement,construction_costs,senior_debt['senior_debt_idc'],development_fee,senior_debt['upfront_fee'],senior_debt['commitment_fees'],injections,local_taxes)

				CFADS=cf_statement['cash_flows_operating']
				CFADS_amo = CFADS*flags['debt_amo']

				discount_factor = calc_discount_factor(senior_debt, days_series, flags)
				debt_amount_DSCR = calc_debt_amount_DSCR(CFADS_amo, inputs, flags, discount_factor)

				optimised_devfee = optimise_devfee(request,debt_amount_DSCR['debt_amount'],sum_construction_costs,senior_debt_fees_constr,DSRA_initial_funding_max,local_taxes)
				development_fee = inputs['devfee_paid_FC'] * optimised_devfee * flags['construction_start'] + inputs['devfee_paid_COD'] * optimised_devfee * flags['construction_end']
				
				total_costs = sum_construction_costs+optimised_devfee+DSRA_initial_funding_max+sum(senior_debt_fees_constr.values())+sum_local_taxes

				debt_amount_gearing = total_costs*inputs['debt_gearing_max']	

				if key.startswith('Sensi'):
					target_debt_amount = target_debt_amount
					senior_debt_repayments_target = senior_debt_repayments_target
				else:
					target_debt_amount = min(debt_amount_DSCR['debt_amount'],debt_amount_gearing)
					senior_debt_repayments_target = calc_senior_debt_repayments_target(injections,CFADS_amo,discount_factor,senior_debt)


				DS_effective=senior_debt_repayments+senior_debt['interests_operations']
				DSCR_effective = np.divide(CFADS_amo,DS_effective,out=np.zeros_like(CFADS_amo), where=DS_effective!=0)

				# Calculate DSRA
				DSRA, DSRA_initial_funding, DSRA_initial_funding_max, dsra_bop = calc_dsra(CFADS, DS_effective, inputs, flags, dsra_bop)
				

				cash_available_for_distribution = (CFADS - senior_debt['interests_operations'] - senior_debt_repayments - DSRA['dsra_mov'] - inputs['cash_min']*flags['operations'])
				transfers_distribution_account = cash_available_for_distribution.clip(lower=0)

				operating_account_eop=cash_available_for_distribution+DSRA_initial_funding-transfers_distribution_account
				operating_account_bop=np.roll(operating_account_eop, 1)

				start_time = time.time()

	
				distribution_account = calc_distr_account(SHL_balance_bop, days_series, inputs, flags,
						  transfers_distribution_account, distributable_profit, injections, income_statement)

				SHL_interests_operations = distribution_account['SHL_interests_operations']
				SHL_interests_construction = distribution_account['SHL_interests_construction']

				
				end_time = time.time()
				execution_time_distribution_account = end_time - start_time

				""" Convergence tests """

				debt_amount_not_converged = abs(debt_amount-target_debt_amount)>0.1
				difference = senior_debt_repayments_target-senior_debt_repayments
				debt_sculpting_not_converged = np.where(difference == 0, True, False)
				debt_sculpting_not_converged = np.any(np.logical_not(debt_sculpting_not_converged))

			share_capital_repayment=distribution_account['distribution_account_bop']*flags['liquidation_end']
			distribution_account_eop=distribution_account['distribution_account_eop']-share_capital_repayment

			share_capital_eop = (injections['share_capital'] - share_capital_repayment).cumsum()
			share_capital_bop = share_capital_eop - (injections['share_capital']-share_capital_repayment)

			total_cash = operating_account_eop+DSRA['dsra_eop']+distribution_account_eop

			""" Balance sheet """		

			PPE = construction_costs_cumul+capitalised_fees_cumul+development_fee.cumsum()-depreciation.cumsum()+local_taxes.cumsum()
			total_assets = PPE+working_cap['acc_receivables_eop']+operating_account_eop+distribution_account_eop+DSRA['dsra_eop']

			total_liabilities = share_capital_eop+distribution_account['SHL_balance_eop']+senior_debt['balance_eop']+distribution_account['retained_earnings_eop']+working_cap['acc_payables_eop']
			total_sources = injections['debt']+injections['equity']

	
			""" Debt ratios """
			LLCR, PLCR = calculate_ratios(discount_factor['avg_interest_rate'], CFADS_amo, CFADS, senior_debt['balance_eop'], date_series['end_period'])
			
			""" Output tables """
			share_capital_cash_flows=-injections['equity']+distribution_account['dividends_paid']+share_capital_repayment
			SHL_cash_flows= -injections['SHL']+SHL_interests_operations+distribution_account['SHL_repayments']
			equity_cash_flows = share_capital_cash_flows+SHL_cash_flows
			equity_cash_flows_cumul = equity_cash_flows.cumsum()

			DSCR_avg = DSCR_effective[flags['debt_amo'] == 1].mean()
			DSCR_min = DSCR_effective[flags['debt_amo'] == 1].min()


			mask = (flags['debt_amo'] == 1)
			indices = np.where(mask)[0]
			indices_without_last = indices[:-1]

			LLCR_min = LLCR[indices_without_last].min()
			equity_irr = xirr(pd.to_datetime(date_series['end_period']).dt.date,equity_cash_flows)



			share_capital_irr = xirr(pd.to_datetime(date_series['end_period']).dt.date,share_capital_cash_flows)
			SHL_irr = xirr(pd.to_datetime(date_series['end_period']).dt.date,SHL_cash_flows)
			


			payback_date = find_payback_date(date_series['end_period'],equity_cash_flows_cumul)

			try:
				payback_date = parser.parse(str(payback_date)).date()
				time_difference = payback_date-inputs['construction_start']
				payback_time = round(time_difference.days / 365.25, 1)
				payback_date=payback_date.strftime("%d/%m/%Y")
			except ParserError:
				payback_date="error"
				payback_time="error"

			project_cash_flows_pre_tax = -total_uses+EBITDA
			project_cash_flows_post_tax = project_cash_flows_pre_tax+income_statement['corporate_income_tax']

			project_irr_pre_tax = xirr(pd.to_datetime(date_series['end_period']).dt.date,project_cash_flows_pre_tax)
			project_irr_post_tax = xirr(pd.to_datetime(date_series['end_period']).dt.date,project_cash_flows_post_tax)



			debt_constraint = determine_debt_constraint(debt_amount_DSCR['debt_amount'],debt_amount_gearing)

			gearing_eff = (debt_amount/total_costs)
			debt_cash_flows = -injections['debt']+senior_debt_repayments+senior_debt['interests']+senior_debt['upfront_fee']+senior_debt['commitment_fees']
			debt_irr = xirr(pd.to_datetime(date_series['end_period']).dt.date,debt_cash_flows)
			

			if debt_amount>0:
				average_debt_life = sum(x * y for x, y in zip(time_series['years_in_period'], senior_debt['balance_bop']))/debt_amount
				average_debt_life = round(average_debt_life,1)
			else:
				average_debt_life=""	


			final_repayment_date_debt=find_last_payment_date(date_series['end_period'], senior_debt['balance_bop'])
			final_repayment_date_debt = final_repayment_date_debt.strftime("%Y-%m-%d %H:%M:%S")
			final_repayment_date_debt = parser.parse(final_repayment_date_debt).date()
			
			tenor_debt = calculate_tenor(final_repayment_date_debt,inputs['construction_start'])


			# Audit and checks 
			audit, check, check_all = calc_audit(total_uses, total_sources, total_assets, total_liabilities, final_repayment_date_debt, inputs)


			""" Output graphs """
			irr_values = create_IRR_curve(equity_cash_flows,date_series['end_period'])



			gearing_during_finplan = injections['debt'].cumsum()/(injections['equity'].cumsum()+injections['debt'].cumsum())


			""" Output sidebar """


			COD_formatted = format_single_date(inputs['COD'])
			end_of_operations_formatted = format_single_date(inputs['end_of_operations'])
			liquidation_formatted = format_single_date(inputs['liquidation_date'])
			debt_maturity_formatted = format_single_date(inputs['debt_maturity'])

	

			sum_seasonality = np.sum(seasonality)/ np.sum(seasonality)* 100
			


			data_detailed = {
				'test': DSRA['dsra_mov'],

				'Date Period start': format_date(date_series,'start_period'),
				'Date Period end': format_date(date_series,'end_period'),

				'FlagCons Construction': flags['construction'],
				'FlagCons Construction start': flags['construction_start'],
				'FlagCons Construction end': flags['construction_end'],
				
				'FlagMod Year': time_series['series_end_period_year'],
				'FlagMod Days in period': days_series['period'],
				'FlagMod Days in year': time_series['days_in_year'],
				'FlagMod Years in period': time_series['years_in_period'],
				'FlagMod Quarter': time_series['quarters'],
				'FlagMod Start of calendar year': flags['start_calendar_year'],

				'FlagOftk_t Contract period': flags['contract'],
				'FlagOftk_t Contract start date': format_date(date_series,'start_contract'),
				'FlagOftk_t Contract end date': format_date(date_series,'end_contract'),
				'FlagOftk_t Days in contract period': days_series['contracted'],
				'FlagOftk_t Percentage in contract period': time_series['pct_in_contract_period'],

				'FlagOftk_i Indexation period': flags['contract_index_period'],
				'FlagOftk_i Indexation start date': format_date(date_series,'start_contract_index'),
				'FlagOftk_i Indexation end date': format_date(date_series,'end_contract_index'),
				'FlagOftk_i Indexation (days)': days_series['contracted_index'] ,
				'FlagOftk_i Indexation': index['contracted'],

				'FlagOp Operations': flags['operations'],
				'FlagOp Years from COD (BoP)': time_series['years_from_COD_bop'],
				'FlagOp Years from COD (EoP)': time_series['years_from_COD_eop'],
				'FlagOp Years from COD (avg.)': time_series['years_from_COD_avg'],
				'FlagOp Years during operations': time_series['years_during_operations'],
				'FlagOp Liquidation': flags['liquidation'] ,
				'FlagOp Liquidation end': flags['liquidation_end'],
				'FlagOp Seasonality':seasonality,

				'FlagOp Days in operations':days_series['days_operations'],
				'FlagOp Percentage in operations period': time_series['pct_in_operations_period'],

				

				'FlagFin Amortisation period': flags['debt_amo'],
				'FlagFin Days during construction': days_series['debt_interest_construction'],
				'FlagFin Days during operations': days_series['debt_interest_operations'],
		
				'IS Contracted revenues': revenues['contracted'],
				'IS Uncontracted electricity revenues': revenues['merchant'],
				'IS Total revenues': revenues['total'],
				'IS Operating expenses': -opex,
				'IS Lease': -lease,

				'IS Property tax': -tfpb,


				'IS EBITDA':EBITDA,
				'IS Depreciation':-depreciation,
				'IS EBIT':income_statement['EBIT'],
				'IS Senior debt interests':-senior_debt['interests_operations'],
				'IS Shareholder loan interests':-SHL_interests_operations,
				'IS EBT':income_statement['EBT'], 
				'IS Corporate income tax':-income_statement['corporate_income_tax'],
				'IS Net income':income_statement['net_income'],
			
				'Mkt_i Indexation': index['merchant'],
				'Mkt_i Indexation (days)': days_series['merchant_index'],
				'Mkt_i Indexation end date': format_date(date_series,'end_elec_index'),
				'Mkt_i Indexation period': flags['merchant_index_period'],
				'Mkt_i Indexation start date': format_date(date_series,'start_elec_index'),
				
				'Opex Indexation': index['opex'],
				'Opex Indexation (days)': days_series['opex_index'],
				'Opex Indexation end date': format_date(date_series,'end_opex_index'),
				'Opex Indexation period': flags['opex_index_period'],
				'Opex Indexation start date': format_date(date_series,'start_opex_index'),
				'Opex Years from indexation start date': years_from_base_dates['opex_index'],


				'Lease Indexation': index['lease'],
				'Lease Indexation (days)': days_series['lease_index'],
				'Lease Indexation end date': format_date(date_series,'end_lease_index'),
				'Lease Indexation period': flags['lease_index_period'],
				'Lease Indexation start date': format_date(date_series,'start_lease_index'),
				'Lease Years from indexation start date': years_from_base_dates['lease_index'],




				'Price Contract price (unindexed)': prices['contracted_real'],
				'Price Contract price (indexed)': prices['contracted_nom'],
				'Price Electricity market price (unindexed)': prices['merchant_real'],
				'Price Electricity market price (indexed)': prices['merchant_nom'],
				
				'Prod Capacity after degradation': capacity['after_degradation'],
				'Prod Capacity before degradation': capacity['before_degradation'],
				'Prod Capacity degradation factor': capacity['degradation_factor'],
				'Prod Production': production,
				
				'EBITDA margin': EBITDA_margin,
				'arr_construction_costs_cumul': construction_costs_cumul,							

				'WCRec Accounts receivables (BoP)':working_cap['acc_receivables_bop'],
				'WCRec Revenue accrued in period':revenues['total'],
				'WCRec Payment received in period':-working_cap['revenues_paid']-working_cap['acc_receivables_bop'],
				'WCRec Accounts receivables (EoP)':working_cap['acc_receivables_eop'],

				'WCPay Accounts payables (BoP)':working_cap['acc_payables_bop'],
				'WCPay Costs accrued in period':(opex+lease),
				'WCPay Payment made in period':-working_cap['costs_paid']-working_cap['acc_payables_bop'],
				'WCPay Accounts payables (EoP)':working_cap['acc_payables_eop'],

				'WCMov Cash flow from (to) creditors':-working_cap['cashflows_from_creditors'],
				'WCMov Cash flow from (to) debtors':working_cap['cashflows_from_debtors'],
				'WCMov Net movement in working capital':working_cap['wc_variation'],
				
				'CF_op EBITDA':EBITDA,
				'CF_op Net movement in working capital':working_cap['wc_variation'],
				'CF_op Corporate income tax':-income_statement['corporate_income_tax'],
				'CF_op Cash flows from operating activities':cf_statement['cash_flows_operating'],
				
				'CF_in Construction costs':-construction_costs,
				'CF_in Development tax':-development_tax,
				'CF_in Archeological tax':-archeological_tax,

				'CF_in Development fee':-development_fee,
				'CF_in Capitalised IDC':-senior_debt['senior_debt_idc'],
				'CF_in Cash flows from investing activities':cf_statement['cash_flows_investing'],
			
				'CF_fi Arrangement fee (upfront)':-senior_debt['upfront_fee'],
				'CF_fi Commitment fees':-senior_debt['commitment_fees'],				
				'CF_fi Senior debt drawdowns':injections['debt'],
				'CF_fi Equity injections':injections['equity'],
				'CF_fi Cash flows from financing activities':cf_statement['cash_flows_financing'],
				
				'CFADS CFADS':CFADS,
				'CFADS Senior debt interests':-senior_debt['interests_operations'],
				'CFADS Senior debt principal':-senior_debt_repayments,

				'CFDSRA Additions to DSRA':-DSRA['dsra_additions'],
				'CFDSRA Release of excess funds':-DSRA['dsra_release'],

				'CFDistr Cash available for distribution':cash_available_for_distribution,
				'CFDistr Transfers to distribution account':-transfers_distribution_account,

				'OpAccB Operating account balance (BoP)':operating_account_bop,

				'OpAccE Operating account balance (EoP)':operating_account_eop,

				'FP_u Construction costs': construction_costs,
				'FP_u Development fee': development_fee,	
				'FP_u Development tax': development_tax,	
				'FP_u Archeological tax': archeological_tax,	



				'FP_u Interests during construction':senior_debt['senior_debt_idc'],
				'FP_u Arrangement fee (upfront)':senior_debt['upfront_fee'],
				'FP_u Commitment fees':senior_debt['commitment_fees'],
				'FP_u Initial DSRA funding':DSRA_initial_funding,

				'FP_u Total uses':total_uses,

				'FP_s Senior debt drawdowns': injections['debt'],
				'FP_s Share capital injections': injections['share_capital'],
				'FP_s Shareholder loan injections': injections['SHL'],
				'FP_s Total sources': total_sources,

				'Debt_a Amount available (BoP)':senior_debt['senior_debt_available_bop'],
				'Debt_a Drawdowns':-injections['debt'],
				'Debt_a Amount available (EoP)':senior_debt['senior_debt_available_eop'],
			
				'Debt_b Opening balance':senior_debt['balance_bop'],
				'Debt_b Drawdowns':injections['debt'],
				'Debt_b Scheduled repayments':-senior_debt_repayments,
				'Debt_b Closing balance':senior_debt['balance_eop'],
			
				'Debt_i Arrangement fee (upfront)':senior_debt['upfront_fee'],
				'Debt_i Commitment fees':senior_debt['commitment_fees'],
				'Debt_i Debt interests':senior_debt['interests'],
				
				'Sizing CFADS':CFADS_amo,
				'Sizing Target DSCR':debt_amount_DSCR['target_DSCR'],
				'Sizing Target DS':debt_amount_DSCR['target_DS'],
				'Sizing Average interest rate':discount_factor['avg_interest_rate'],
				'Sizing Discount factor':discount_factor['discount_factor'],
				'Sizing Cumulative discount factor':discount_factor['discount_factor_cumul'],
				'Sizing Interests during operations':senior_debt['interests_operations'],
				'Sizing Debt repayment target':senior_debt_repayments_target,

				'DSRA Cash available for DSRA':DSRA['cash_available_for_dsra'],
				'DSRA DSRA target liquidity':DSRA['dsra_target'],
				'DSRA DSRA target additions':DSRA['dsra_additions_required'],
				
				'DSRA DSRA (BoP)':DSRA['dsra_bop'],
				'DSRA Additions to DSRA':DSRA['dsra_additions'],
				'DSRA Release of excess funds':DSRA['dsra_release'],
				'DSRA DSRA (EoP)':DSRA['dsra_eop'],
							
				'DistrBOP Balance brought forward':distribution_account['distribution_account_bop'],
				'DistrBOP Transfers to distribution account':transfers_distribution_account,

				'DistrSHLi Cash available for interests':distribution_account['cash_available_for_SHL_interests'],
				'DistrSHLi Shareholder loan interests paid':-distribution_account['SHL_interests_paid'],

				'DistrDiv Cash available for dividends':distribution_account['cash_available_for_dividends'],
				'DistrDiv Dividends paid':-distribution_account['dividends_paid'],

				'DistrSHLp Cash available for repayment':distribution_account['cash_available_for_SHL_repayments'],
				'DistrSHLp Shareholder loan repayment':-distribution_account['SHL_repayments'],

				'DistrSC Cash available for reductions':distribution_account['cash_available_for_redemption'],
				'DistrSC Share capital reductions':-share_capital_repayment,

				'DistrEOP Distribution account balance':distribution_account_eop,


				'DevTax Development tax':development_tax,
				
				'ArchTax Archeological tax':archeological_tax,


				'PropTax Property value':gross_property_value,
				'PropTax Land value':gross_land_value,
				
				'PropTax Property tax':tfpb,


				'CFETaxBase Property value before deductions':gross_property_value,
				'CFETaxBase Standard deduction':-cfe_std_deduction,
				'CFETaxBase Tax base':cfe_tax_base,
				'CFETaxDue Notional CFE due in period':cfe_due,
				'CFETaxDue Local tax management fee due':cfe_mgt_fee,
				'CFETaxDue Gross CFE due':cfe_total_due,



				'SHL Opening balance':distribution_account['SHL_balance_bop'],
				'SHL Drawdowns':injections['SHL'],
				'SHL Capitalised interest':SHL_interests_construction,
				'SHL Repayment':-distribution_account['SHL_repayments'],
				'SHL Closing balance':distribution_account['SHL_balance_eop'],
			
				'iSHL Interests (construction)':SHL_interests_construction,
				'iSHL Interests (operations)':SHL_interests_operations,

				'RE_b Distributable profit':distribution_account['distributable_profit'],			
				'RE_b Balance brought forward':distribution_account['retained_earnings_bop'],
				'RE_b Net income': income_statement['net_income'],		
				'RE_b Dividends declared': -distribution_account['dividends_paid'],
				'RE_b Retained earnings':distribution_account['retained_earnings_eop'],

				'Eqt Opening balance':share_capital_bop,			
				'Eqt Contributions':injections['share_capital'],
				'Eqt Capital reductions':-share_capital_repayment,
				'Eqt Closing balance':share_capital_eop,

				'BS_a Property, Plant, and Equipment': PPE,
				'BS_a Accounts receivables': working_cap['acc_receivables_eop'],
				'BS_a Cash or cash equivalents': total_cash,
				'BS_a Operating account balance': operating_account_eop,
				'BS_a DSRA balance': DSRA['dsra_eop'],

				'BS_a Distribution account balance': distribution_account_eop,

				'BS_a Total assets': total_assets,
			
				'BS_l Share capital (EoP)': share_capital_eop,
				'BS_l Retained earnings': distribution_account['retained_earnings_eop'],
				'BS_l Shareholder loan (EoP)': distribution_account['SHL_balance_eop'],
				'BS_l Senior debt (EoP)': senior_debt['balance_eop'],
				'BS_l Accounts payables (EoP)': working_cap['acc_payables_eop'],
				'BS_l Total liabilities': total_liabilities,

				'Cumulative total uses':total_uses_cumul,
				'Senior debt drawdowns neg': -1 * injections['debt'],
				'Share capital injections neg': -1 * injections['share_capital'],
				'Shareholder loan injections neg': -1 * injections['SHL'],
				'Dividends paid pos':distribution_account['dividends_paid'],
			

				'Lease pos': lease,

				'Operating expenses pos':(opex+lease+tfpb),
				'Senior debt repayments':senior_debt_repayments,
				'Ratio DSCR':DSCR_effective,
				'Ratio LLCR':LLCR,
				'Ratio PLCR':PLCR,

				'Share capital injections and repayment':-injections['share_capital']+share_capital_repayment,
				'Shareholder loan injections and repayment':-injections['SHL']+distribution_account['SHL_repayments'],
				'Share capital repayment pos':share_capital_repayment,
				'Debt service':DS_effective,

				'IRR curve':irr_values,

				'Gearing during financing plan':gearing_during_finplan,
				'Audit Balance sheet balanced': audit['balance_sheet'],
				'Audit Financing plan balanced': audit['financing_plan'],
			}

			df = pd.DataFrame(data_detailed)

			df_annual = create_df_annual(data_detailed)
			
			dfs[key] = df
			df_sum = df.apply(pd.to_numeric, errors='coerce').sum()	
			

			results_equity[key] = [share_capital_irr,SHL_irr,equity_irr,payback_date,payback_time]
			results_sensi[key] = [DSCR_min,DSCR_avg,LLCR_min,equity_irr,check_all]
			results_projectIRR[key] = [project_irr_pre_tax,project_irr_post_tax]
			results_debt[key] = [debt_amount,debt_constraint,gearing_eff,tenor_debt,average_debt_life,DSCR_avg,debt_irr]
			results_audit[key] = [check['financing_plan'],check['balance_sheet'],check['debt_maturity']]



		calculation_type_mapping = {
			"sensi-p50": "Sponsor Case",
			"sensi-opex": "Sensi Opex",
			"sensi-inflation": "Sensi Inflation",
			"sensi-production": "Sensi Production",

		}

		if calculation_type in calculation_type_mapping:
			key = calculation_type_mapping[calculation_type]
		else:
			key = "Lender Case"

		results_projectIRR_displayed = results_projectIRR[key]
		results_equity_displayed = results_equity[key]
		results_debt_displayed = results_debt[key]
		results_audit_displayed = results_audit[key]
		df_displayed = dfs[key]

		table_sensi = create_table_sensi(results_sensi).to_dict()
		table_uses = create_table_uses(sum_construction_costs,optimised_devfee,senior_debt_fees_constr,total_costs,DSRA_initial_funding_max,development_tax_sum,archeological_tax_sum)
		table_sources = create_table_sources(injections,debt_amount)
		table_projectIRR = create_table_projectIRR(results_projectIRR_displayed)
		table_equity = create_table_equity(results_equity_displayed)
		table_debt = create_table_debt(results_debt_displayed)
		table_audit = create_table_audit(results_audit_displayed)
		

		api_results = np.array([
			dev_tax_commune,
			])

	
		tfpb_rates = {
		    "Taux communal": tfpb_commune,
		    "Taux intercommunal": tfpb_intercommunal,
		    "Taxe spéciale d’équipement": tfpb_specific_eqpt,
		}


		dev_tax_rates = {
		    "Taux communal": dev_tax_commune,
		}

		data_dump_sidebar = np.array([
			COD_formatted,
			installed_capacity,
			end_of_operations_formatted,
			
			sum_seasonality,
			sum_construction_costs,
			liquidation_formatted,
			debt_maturity_formatted,
			debt_amount_DSCR['debt_amount'],
			debt_amount_gearing,
			target_debt_amount,
			debt_amount,
			optimised_devfee,
			final_repayment_date_debt,
			])
		
		del project_form.cleaned_data['calculation_type']
		project_form.save()






		annual = calculate_annual(date_series['end_period'],production,capacity['degradation_factor'],revenues,opex,lease,EBITDA,senior_debt['interests_operations'],senior_debt_repayments,CFADS_amo,injections['debt'],senior_debt['balance_eop'],DSRA['dsra_bop'],distribution_account['dividends_paid'],irr_values,injections,share_capital_repayment,distribution_account['SHL_repayments'],distribution_account['retained_earnings_bop'], distribution_account['distribution_account_eop'])
		monthly = calculate_monthly(date_series['end_period'],construction_costs,total_uses_cumul,flags['construction'],injections,total_uses, gearing_during_finplan,development_fee,senior_debt['senior_debt_idc'],senior_debt['upfront_fee'],senior_debt['commitment_fees'],DSRA_initial_funding,local_taxes)
		end_year = calculate_end_year(date_series['end_period'],capacity['degradation_factor'],senior_debt['balance_eop'],DSRA['dsra_bop'],irr_values,distribution_account['retained_earnings_bop'], distribution_account['distribution_account_eop'], LLCR, PLCR)


		return JsonResponse({
			"df":df_displayed.to_dict(),
			"df_sum":df_sum.to_dict(),
			"df_annual":df_annual.to_dict(),


			"table_uses":table_uses.to_dict(),
			"table_sources":table_sources.to_dict(),
			"table_projectIRR":table_projectIRR,
			"table_equity":table_equity,
			"table_debt":table_debt,
			"table_sensi":table_sensi,
			"table_audit":table_audit,

			"calculation_detail":inputs['calculation_detail'],
			"dic_price_elec_keys":dic_price_elec_keys.tolist(),
			"data_dump_sidebar":data_dump_sidebar.tolist(),
			"tfpb_rates":tfpb_rates,
			"dev_tax_rates":dev_tax_rates,
			"annual":annual,
			"monthly":monthly,
			"end_year":end_year,

			},safe=False, status=200)

	except Exception as e:
		
		error_data = {
			'error_type': e.__class__.__name__,
			'message': str(e)
		}

		return JsonResponse(error_data,safe=False, status=400)










def handle_get_request(request, id):
	project = get_object_or_404(Project, id=id)
	project_form = ProjectForm(instance=project)
	context = {
		'project_form': project_form,
		'project': project,
	}
	return render(request, "project_view.html", context)


def get_inputs(request):
	post_data = request.POST

	inp_all_in_interest = np.array([
		float(post_data['debt_margin']),
		float(post_data['debt_swap_rate']),
		float(post_data['debt_swap_margin']),
		float(post_data['debt_reference_rate_buffer']),
	])

	debt_interest_rate = np.sum(inp_all_in_interest) / 100

	dsra = 6 if int(post_data['DSRA_choice']) == 1 else 12

	construction_start = datetime.datetime.strptime(post_data['start_construction'], "%Y-%m-%d").date()

	construction_end = datetime.datetime.strptime(post_data['end_construction'], "%Y-%m-%d").date()
	COD = construction_end + datetime.timedelta(days=1) 

	operating_life = int(post_data['operating_life'])
	end_of_operations = construction_end + relativedelta(years=operating_life)

	debt_tenor = float(post_data['debt_tenor'])

	debt_maturity = construction_start + relativedelta(months=+int(debt_tenor*12)-1)
	debt_maturity_date = debt_maturity
	debt_maturity = debt_maturity.replace(day = calendar.monthrange(debt_maturity.year, debt_maturity.month)[1])

	liquidation = int(post_data['liquidation'])

	liquidation_date = end_of_operations + relativedelta(months=liquidation)

	# Create a dictionary to store the results
	inputs = {

		'periodicity': int(post_data['periodicity']),
		'construction_start': construction_start,
		'construction_end': construction_end,
		'COD': COD,
		'debt_maturity_date': debt_maturity_date,

		'operating_life':operating_life,

		'end_of_operations':end_of_operations,

		'start_contract': post_data['start_contract'],
		'end_contract': post_data['end_contract'],

		'debt_tenor':debt_tenor,	
		'debt_maturity':debt_maturity,	


		'liquidation':liquidation,
		'liquidation_date':liquidation_date,

		'income_tax_rate': float(post_data['corporate_income_tax']) / 100,

		'debt_gearing_max': float(post_data['debt_gearing_max']) / 100,
		'debt_upfront_fee': float(post_data['debt_upfront_fee']) / 100,
		'debt_commitment_fee': float(post_data['debt_commitment_fee']) / 100,
		'subgearing': float(post_data['subgearing']) / 100,
		'debt_target_DSCR': float(post_data['debt_target_DSCR']),
		'debt_interest_rate': debt_interest_rate,

		'injection_choice': int(post_data['injection_choice']),

		'SHL_margin': float(post_data['SHL_margin']) / 100,

		'devfee_paid_FC': float(post_data['devfee_paid_FC']),
		'devfee_paid_COD': float(post_data['devfee_paid_COD']),

		'contract_price': float(post_data['contract_price']),
		'index_rate_merchant': float(post_data['price_elec_indexation']) / 100,
		'index_rate_contract': float(post_data['contract_indexation']) / 100,
		'index_rate_opex': float(post_data['opex_indexation']) / 100,
		'payment_delay_revenues': int(post_data['payment_delay_revenues']),
		'payment_delay_costs': int(post_data['payment_delay_costs']),

		'opex': float(post_data['opex']),
		'dsra': dsra,

		'cash_min': int(post_data['cash_min']),

		'panels_capacity': int(post_data['panels_capacity']),
		'degradation':  float(post_data['annual_degradation'])/100,		

		'sensi_production': float(post_data['sensi_production'])/100,
		'sensi_opex': float(post_data['sensi_opex'])/100,
		'sensi_inflation': float(post_data['sensi_inflation'])/100,

		'opex_index_start_date': post_data['opex_indexation_start_date'],
		'merchant_index_start_date': post_data['price_elec_indexation_start_date'],
		'contract_index_start_date': post_data['contract_indexation_start_date'],

		'calculation_detail': int(post_data['calculation_detail']),




		'lease': float(post_data['lease']),
		'index_rate_lease': float(post_data['lease_indexation']) / 100,		
		'lease_index_start_date': post_data['lease_indexation_start_date'],


		'lender_prod': int(post_data['production_choice']),
		'sponsor_prod': int(post_data['sponsor_production_choice']),

		'lender_mkt_prices': int(post_data['price_elec_choice']),
		'sponsor_mkt_prices': int(post_data['sponsor_price_elec_choice']),

		'wind_turbine_installed': int(post_data['wind_turbine_installed']),
		'capacity_per_turbine': float(post_data['capacity_per_turbine']),

		'technology': post_data['technology'],
		'timeline_quarters_ceiling': post_data['timeline_quarters_ceiling'],
		
		'commune': post_data['commune'],


		'panels_surface': float(post_data['panels_surface']),
		'dev_tax_taxable_base_solar': float(post_data['dev_tax_taxable_base_solar']),
		'dev_tax_taxable_base_wind': float(post_data['dev_tax_taxable_base_wind']),
		'dev_tax_commune_tax': float(post_data['dev_tax_commune_tax'])/100,
		'dev_tax_department_tax': float(post_data['dev_tax_department_tax'])/100,

		'archeological_tax_base_solar': float(post_data['archeological_tax_base_solar']),
		'archeological_tax': float(post_data['archeological_tax'])/100,


		'tfpb_rate': (float(post_data['tfpb_commune_tax'])+float(post_data['tfpb_department_tax'])+float(post_data['tfpb_region_tax'])+float(post_data['tfpb_additional_tax']))/100,
		'cfe_rate': (float(post_data['cfe_commune_tax'])+float(post_data['cfe_intercommunal_tax'])+float(post_data['cfe_specific_eqp_tax'])+float(post_data['cfe_localCCI_tax']))/100,
		'cfe_mgt_fee': float(post_data['cfe_mgt_fee'])/100,
		'cfe_discount_tax_base': float(post_data['cfe_discount_tax_base'])/100,

	}

	return inputs


def create_scenario_dict(inputs):

		dict_scenario = {
			"Lender Case": {
				"prod": inputs['lender_prod'],
				"elec_price": inputs['lender_mkt_prices'],
				"sensi_prod": 0,
				"sensi_inf": 0,
				"sensi_opex": 0,
			},

			"Sensi Production": {
				"prod": inputs['lender_prod'],
				"elec_price": inputs['lender_mkt_prices'],
				"sensi_prod": inputs['sensi_production'],
				"sensi_inf": 0,
				"sensi_opex": 0,
			},
			"Sensi Inflation": {
				"prod": inputs['lender_prod'],
				"elec_price": inputs['lender_mkt_prices'],
				"sensi_prod": 0,
				"sensi_inf": inputs['sensi_inflation'],
				"sensi_opex": 0,
			},
			"Sensi Opex": {
				"prod": inputs['lender_prod'],
				"elec_price": inputs['lender_mkt_prices'],
				"sensi_prod": 0,
				"sensi_inf": 0,
				"sensi_opex": inputs['sensi_opex'],
			},
			"Sponsor Case": {
				"prod": inputs['sponsor_prod'],
				"elec_price": inputs['sponsor_mkt_prices'],
				"sensi_prod": 0,
				"sensi_inf": 0,
				"sensi_opex": 0,
			},
		}


		return dict_scenario


class FlagCreator:
	def __init__(self):
		pass
	
	def create_flag_operations(self, COD, series_start_period, series_end_period, end_of_operations):
		self.flag_operations = ((series_end_period >= pd.to_datetime(COD)) * (series_start_period <= pd.to_datetime(end_of_operations))).astype(int)
		return self.flag_operations

	def create_flag_start_calendar_year(self, series_start_period):
		datetime_series = pd.to_datetime(series_start_period, format='%d/%m/%Y', errors='coerce')
		self.flag_start_calendar_year = (datetime_series.dt.month == 1)*1
		return self.flag_start_calendar_year

	def create_flag_construction(self, series_start_period, construction_end):
		self.flag_construction = (series_start_period <= pd.to_datetime(construction_end)).astype(int)
		return self.flag_construction

	def create_flag_construction_end(self, series_start_period, series_end_period, construction_end):
		self.flag_construction_end = ((series_start_period <= pd.to_datetime(construction_end))*(series_end_period >= pd.to_datetime(construction_end))).astype(int)
		return self.flag_construction_end

	def create_flag_construction_start(self, series_start_period, series_end_period, construction_start):
		self.flag_construction_start = ((series_start_period <= pd.to_datetime(construction_start))*(series_end_period >= pd.to_datetime(construction_start))).astype(int)
		return self.flag_construction_start

	def create_flag_liquidation(self, series_end_period, end_of_operations):
		self.flag_liquidation = (series_end_period > pd.to_datetime(end_of_operations + datetime.timedelta(days=1))).astype(int)
		return self.flag_liquidation

	def create_flag_liquidation_end(self, series_end_period, liquidation):
		self.flag_liquidation_end = (series_end_period == pd.to_datetime(liquidation)).astype(int)
		return self.flag_liquidation_end

	def create_flag_debt_amo(self, series_start_period, debt_maturity, flag_operations):
		return (series_start_period <= pd.to_datetime(debt_maturity)).astype(int) * flag_operations

	def create_flag_array(self, timeline_end,start,timeline_start,end):	
		flag_result = (timeline_end>=pd.to_datetime(start))*(timeline_start<=pd.to_datetime(end)).astype(int)*(timeline_end!=timeline_start)
		return flag_result

	def create_flag_contract(self, start_contract, series_start_period, series_end_period, end_contract):
		self.flag_contract = ((series_end_period >= pd.to_datetime(start_contract)) * (series_start_period <= pd.to_datetime(end_contract))).astype(int)
		return self.flag_contract


	def create_flags(self, params):
		# Create flags by calling the respective methods
		self.create_flag_operations(params['COD'], params['series_start_period'], 
									params['series_end_period'], params['end_of_operations'])

		self.create_flag_start_calendar_year(params['series_start_period'])

		self.create_flag_construction(params['series_start_period'], params['construction_end'])
		self.create_flag_construction_end(params['series_start_period'], params['series_end_period'], params['construction_end'])
		self.create_flag_construction_start(params['series_start_period'], params['series_end_period'], params['construction_start'])
		self.create_flag_liquidation(params['series_end_period'], params['end_of_operations'])
		self.create_flag_liquidation_end(params['series_end_period'], params['liquidation_date'])
		self.create_flag_contract(params['start_contract'], params['series_start_period'], params['series_end_period'], params['end_contract'])

		self.flag_debt_amo = self.create_flag_debt_amo(params['series_start_period'], params['debt_maturity'], self.flag_operations)
		self.flag_contract_index_period = self.create_flag_array(params['series_end_contract_index'], params['contract_index_start_date'], params['series_start_contract_index'], params['end_contract'])
		self.flag_merchant_index_period = self.create_flag_array(params['series_end_elec_index'], params['merchant_index_start_date'], params['series_start_elec_index'], params['end_of_operations'])
		self.flag_opex_index_period = self.create_flag_array(params['series_end_opex_index'], params['opex_index_start_date'], params['series_start_opex_index'], params['end_of_operations'])
		self.flag_lease_index_period = self.create_flag_array(params['series_end_lease_index'], params['lease_index_start_date'], params['series_start_lease_index'], params['end_of_operations'])


		# Return a dictionary containing all flags
		return {
			'operations': self.flag_operations,
			'construction': self.flag_construction,
			'construction_end': self.flag_construction_end,
			'construction_start': self.flag_construction_start,
			'liquidation': self.flag_liquidation,
			'liquidation_end': self.flag_liquidation_end,
			'debt_amo': self.flag_debt_amo,
			'contract': self.flag_contract,
			'contract_index_period': self.flag_contract_index_period,
			'merchant_index_period': self.flag_merchant_index_period,
			'opex_index_period': self.flag_opex_index_period,
			'lease_index_period': self.flag_lease_index_period,
			'start_calendar_year': self.flag_start_calendar_year,

		}

class DaysCalculator:
	def __init__(self, flags):
		self.flags = flags
	
	def create_days(self, arr_end_date, arr_start_date, flag_name):
		flag = self.flags[flag_name]
		number_days = ((arr_end_date - arr_start_date).dt.days + 1) * flag
		return number_days

	def calculate_days_series(self, params):
		period = ((params['series_end_period'] - params['series_start_period']).dt.days + 1) * 1
		
		


		contracted = self.create_days(params['series_end_contract'], 
										 params['series_start_contract'], 
										 'contract') 

		contracted_index = self.create_days(params['series_end_contract_index'], 
										 params['series_start_contract_index'], 
										 'contract_index_period') 

		merchant_index = self.create_days(params['series_end_elec_index'], 
										 params['series_start_elec_index'], 
										 'merchant_index_period') 

		opex_index = self.create_days(params['series_end_opex_index'], 
										 params['series_start_opex_index'], 
										 'opex_index_period') 

		lease_index = self.create_days(params['series_end_lease_index'], 
										 params['series_start_lease_index'], 
										 'lease_index_period') 


		debt_interest_construction = self.create_days(params['series_end_debt_interests_construction'], 
										 params['series_start_debt_interests_construction'], 
										 'construction') 

		debt_interest_operations = self.create_days(params['series_end_debt_interests_operations'], 
										 params['series_start_debt_interests_operations'], 
										 'debt_amo') 

		days_operations = self.create_days(params['series_end_operations'], 
										 params['series_start_operations'], 
										 'operations') 


		# ... similarly calculate other period days
		return {
			'period': period,
			'contracted': contracted,
			'contracted_index': contracted_index,
			'merchant_index': merchant_index,
			'opex_index': opex_index,
			'debt_interest_construction': debt_interest_construction,
			'debt_interest_operations': debt_interest_operations,

			'days_operations': days_operations,
			'lease_index': lease_index,



			# ... other period days
		}



def format_date(date_series, column_name):
	return pd.to_datetime(date_series[column_name]).dt.strftime('%d/%m/%Y')

def format_single_date(date_str):
	return date_str.strftime("%d/%m/%Y")


def create_timeline_series(inputs):

	freq_period_start = str(inputs['periodicity'])+"MS"
	freq_period_end = str(inputs['periodicity'])+"M"

	testi = inputs['periodicity']
	test = int(inputs['periodicity']/3)

	first_day_month_construction_start = first_day_month(inputs['construction_start'])
	last_day_construction_end = last_day_month(inputs['construction_end'])
	
	first_operations_date = last_day_construction_end + datetime.timedelta(days=1) 
	first_operations_date = pd.Timestamp(first_operations_date)
	first_operations_date = pd.Series(first_operations_date)

	first_operations_end_date = last_day_construction_end + datetime.timedelta(days=1) + relativedelta(months=+test) + pd.tseries.offsets.QuarterEnd()*test

	second_operations_date = first_operations_end_date + datetime.timedelta(days=1)

	last_day_liquidation_end = last_day_month(inputs['liquidation_date'])

	last_day_end_liquidation_plus_freq = first_day_next_month(inputs['liquidation_date'],inputs)
	
	start_period_construction = pd.Series(pd.date_range(first_day_month_construction_start,last_day_construction_end, freq='MS'))
	end_period_construction = pd.Series(pd.date_range(first_day_month_construction_start,last_day_construction_end, freq='M'))

	start_period_operations = pd.Series(pd.date_range(second_operations_date, last_day_liquidation_end,freq=freq_period_start))
	end_period_operations = pd.Series(pd.date_range(first_operations_end_date, last_day_end_liquidation_plus_freq,freq=freq_period_end))

	series_start_period = pd.concat([start_period_construction,first_operations_date,start_period_operations], ignore_index=True)
	series_end_period = pd.concat([end_period_construction,end_period_operations], ignore_index=True)
	
	return series_start_period, series_end_period


def create_time_series(date_series, days_series, flags):
	# Calculating days in year considering leap years
	days_in_year = date_series['end_period'].dt.is_leap_year * 366 + (1 - date_series['end_period'].dt.is_leap_year) * 365

	# Calculating years in period
	years_in_period = days_series['period'] / days_in_year

	# Calculating years during operations
	years_during_operations = years_in_period * flags['operations']


	quarters = get_quarters(date_series['end_period'])

	# Calculating years from COD to end of operations
	years_from_COD_eop = years_during_operations.cumsum()
	years_from_COD_bop = years_from_COD_eop - years_during_operations
	years_from_COD_avg = (years_from_COD_eop + years_from_COD_bop) / 2

	# Extracting the year part from the end period series
	series_end_period_year = date_series['end_period'].dt.year


	pct_in_operations_period = days_series['days_operations'] / days_series['period']
	# Calculating years from base dates (assuming calc_years_from_base_dates is defined elsewhere in your code)
	"""years_from_base_dates = calc_years_from_base_dates(days_series, days_in_year)"""


	# Calculating the percentage of time in the contracted period
	pct_in_contract_period = np.where(days_series['days_operations'] > 0, days_series['contracted'] / days_series['days_operations'],0)  # Default value when days_series['days_operations'] is zero

	# Constructing the result dictionary

	time_series_results = {
		'days_in_year': days_in_year,
		'years_in_period': years_in_period,
		'years_during_operations': years_during_operations,
		'years_from_COD_eop': years_from_COD_eop,
		'years_from_COD_bop': years_from_COD_bop,
		'years_from_COD_avg': years_from_COD_avg,
		'series_end_period_year': series_end_period_year,
		'pct_in_contract_period': pct_in_contract_period,
		'pct_in_operations_period': pct_in_operations_period,
		'quarters': quarters,

	}

	return time_series_results


def create_df_annual(data_detailed):

	data_detailed = pd.DataFrame(data_detailed)

	data_detailed['Year'] = pd.to_datetime(data_detailed['Date Period end']).dt.year
	is_columns = [col for col in data_detailed.columns if col.startswith('IS')]
	columns_to_sum = ['Year'] + is_columns
	annual_sums = data_detailed[columns_to_sum].groupby('Year').sum().reset_index()

	return annual_sums


def get_elec_prices(request, construction_end, liquidation_date, dict_scenario, key):
	dic_price_elec = create_price_elec_dict(request, construction_end, liquidation_date, dict_scenario, key)
	dic_price_elec_keys = np.array(list(dic_price_elec.keys()))
	return dic_price_elec, dic_price_elec_keys


def calculate_monthly(series_end_period,construction_costs,total_uses_cumul,flag_construction,injections,total_uses, gearing_during_finplan,development_fee,senior_debt_idc,senior_debt_upfront_fee,senior_debt_commitment_fees,DSRA_initial_funding,local_taxes):

	debt_fees = senior_debt_idc+senior_debt_upfront_fee+senior_debt_commitment_fees


	df = pd.DataFrame({
		'Date': series_end_period, 
		'construction_costs':construction_costs,
		'total_uses_cumul':total_uses_cumul,
		'flag_construction':flag_construction,
		'Share capital injections':-injections['share_capital'],
		'SHL injections':-injections['SHL'],
		'Debt injections':-injections['debt'],
		'Total uses':total_uses,
		'Gearing':gearing_during_finplan,
		'Development fee':development_fee,
		'Debt fees':debt_fees,
		'DSRA initial funding':DSRA_initial_funding,
		'Local taxes':local_taxes,

		})

	df_filtered = df[df['flag_construction'] == 1]
	formatted_dates = [date.strftime('%d/%m/%Y') for date in df_filtered['Date']]


	result_dict = {
	'Date': df_filtered['Date'].tolist(),
	'Construction costs': df_filtered['construction_costs'].tolist(),
	'Construction costs cumul': df_filtered['total_uses_cumul'].tolist(),
	'Share capital injections': df_filtered['Share capital injections'].tolist(),
	'SHL injections': df_filtered['SHL injections'].tolist(),
	'Debt injections': df_filtered['Debt injections'].tolist(),
	'Total uses': df_filtered['Total uses'].tolist(),
	'Gearing': df_filtered['Gearing'].tolist(),
	'Development fee': df_filtered['Development fee'].tolist(),
	'Debt fees': df_filtered['Debt fees'].tolist(),
	'DSRA initial funding': df_filtered['DSRA initial funding'].tolist(),
	'Local taxes': df_filtered['Local taxes'].tolist(),

	}

	result_dict['Date'] = [date.strftime('%m/%y') for date in df_filtered['Date']]

	return result_dict




def calculate_annual(series_end_period, production, degradation, revenues,opex,lease,EBITDA,senior_debt_interests_operations,senior_debt_repayments,CFADS, senior_debt_drawdowns,senior_debt_eop,DSRA_eop,dividends_paid,irr_values,injections,share_capital_repayment,SHL_repayment,retained_earnings_bop,distribution_account_eop):
	df = pd.DataFrame({
		'Date': series_end_period, 
		'Production': production, 
		'Degradation': degradation, 
		'Contracted revenues':revenues['contracted'], 
		'Merchant revenues': revenues['merchant'],
		'Opex': opex,
		'Lease': lease,
		'EBITDA':EBITDA,
		'Senior debt interests':senior_debt_interests_operations,
		'Senior debt repayments':senior_debt_repayments,
		'CFADS':CFADS,
		'Senior debt drawdowns':senior_debt_drawdowns,
		'Senior debt EOP':senior_debt_eop,
		'DSRA EOP':DSRA_eop,
		'Dividends':dividends_paid,
		'IRR curve':irr_values,
		'Share capital injections':-injections['share_capital'],
		'SHL injections':-injections['SHL'],
		'Share capital repayment':share_capital_repayment,
		'SHL repayment':SHL_repayment,
		'Retained earnings BOP':retained_earnings_bop,
		'Distribution account EOP':distribution_account_eop,
		})

	# Convert the 'Date' column to datetime objects
	df['Date'] = pd.to_datetime(df['Date'])
	df['Year'] = df['Date'].dt.year

	# Extract the year from the 'Date' column and group by year
	yearly_production_sum = df.groupby('Year')['Production'].sum().reset_index()
	yearly_contracted_revenues_sum = df.groupby('Year')['Contracted revenues'].sum().reset_index()
	yearly_merchant_revenues_sum = df.groupby('Year')['Merchant revenues'].sum().reset_index()
	opex_sum = df.groupby('Year')['Opex'].sum().reset_index()
	lease_sum = df.groupby('Year')['Lease'].sum().reset_index()
	EBITDA_sum = df.groupby('Year')['EBITDA'].sum().reset_index()
	senior_debt_interests_operations_sum = df.groupby('Year')['Senior debt interests'].sum().reset_index()
	senior_debt_repayments_sum = df.groupby('Year')['Senior debt repayments'].sum().reset_index()
	CFADS_sum = df.groupby('Year')['CFADS'].sum().reset_index()
	share_capital_injections_sum = df.groupby('Year')['Share capital injections'].sum().reset_index()
	SHL_injections_sum = df.groupby('Year')['SHL injections'].sum().reset_index()
	share_capital_repayment_sum = df.groupby('Year')['Share capital repayment'].sum().reset_index()
	SHL_repayment_sum = df.groupby('Year')['SHL repayment'].sum().reset_index()
	CFADS_sum = df.groupby('Year')['CFADS'].sum().reset_index()
	dividends_paid_sum = df.groupby('Year')['Dividends'].sum().reset_index()
	senior_debt_drawdowns_sum = df.groupby('Year')['Senior debt drawdowns'].sum().reset_index()


	share_capital_flows = share_capital_injections_sum['Share capital injections']+share_capital_repayment_sum['Share capital repayment']
	SHL_flows = SHL_injections_sum['SHL injections']+SHL_repayment_sum['SHL repayment']
	debt_service=senior_debt_interests_operations_sum['Senior debt interests']+senior_debt_repayments_sum['Senior debt repayments']
	total_revenues=yearly_contracted_revenues_sum['Contracted revenues']+yearly_merchant_revenues_sum['Merchant revenues']
	
	EBITDA_margin = np.divide(EBITDA_sum['EBITDA'], total_revenues, out=np.zeros_like(EBITDA_sum['EBITDA']), where=total_revenues > 0)


	DSCR = np.divide(CFADS_sum['CFADS'], debt_service, out=np.zeros_like(CFADS_sum['CFADS']), where=debt_service > 0)




	# Get the degradation value at 31/12/N of each year
	degradation_values = df.groupby('Year')['Degradation'].last().reset_index()
	senior_debt_eop = df.groupby('Year')['Senior debt EOP'].last().reset_index()
	DSRA_eop = df.groupby('Year')['DSRA EOP'].last().reset_index()
	IRR_curve = df.groupby('Year')['IRR curve'].last().reset_index()
	Retained_earnings_BOP = df.groupby('Year')['Retained earnings BOP'].last().reset_index()
	Distribution_account_EOP = df.groupby('Year')['Distribution account EOP'].last().reset_index()


	annual_sum = {
	'Year': degradation_values['Year'].tolist(),
	'Production': yearly_production_sum['Production'].tolist(),
	'Contracted revenues': yearly_contracted_revenues_sum['Contracted revenues'].tolist(),
	'Merchant revenues': yearly_merchant_revenues_sum['Merchant revenues'].tolist(),
	'Opex': opex_sum['Opex'].tolist(),
	'Lease': lease_sum['Lease'].tolist(),
	'EBITDA': EBITDA_sum['EBITDA'].tolist(),
	'EBITDA margin': EBITDA_margin.tolist(),
	'Senior debt interests': senior_debt_interests_operations_sum['Senior debt interests'].tolist(),
	'Senior debt repayments': senior_debt_repayments_sum['Senior debt repayments'].tolist(),
	'DSCR': DSCR.tolist(),
	'Debt service': debt_service.tolist(),
	'CFADS': CFADS_sum['CFADS'].tolist(),
	'Senior debt drawdowns': senior_debt_drawdowns_sum['Senior debt drawdowns'].tolist(),
	'Share capital flows': share_capital_flows.tolist(),
	'SHL flows': SHL_flows.tolist(),
	'Share capital repayment': share_capital_repayment_sum['Share capital repayment'].tolist(),
	'Dividends': dividends_paid_sum['Dividends'].tolist(),


	'Degradation': degradation_values['Degradation'].tolist(),
	'IRR curve': IRR_curve['IRR curve'].tolist(),
	'DSRA EOP': DSRA_eop['DSRA EOP'].tolist(),
	'Retained earnings BOP': Retained_earnings_BOP['Retained earnings BOP'].tolist(),
	'Distribution account EOP': Distribution_account_EOP['Distribution account EOP'].tolist(),
	'Senior debt EOP': senior_debt_eop['Senior debt EOP'].tolist(),
	}

	return annual_sum

def calculate_end_year(series_end_period, degradation, senior_debt_eop,DSRA_eop,irr_values,retained_earnings_bop,distribution_account_eop,LLCR,PLCR):
	df = pd.DataFrame({
		'Date': series_end_period, 
		'Degradation': degradation, 
		'Senior debt EOP':senior_debt_eop,
		'DSRA EOP':DSRA_eop,
		'IRR curve':irr_values,
		'Retained earnings BOP':retained_earnings_bop,
		'Distribution account EOP':distribution_account_eop,
		'LLCR': LLCR, 
		'PLCR': PLCR, 

		})

	df['Year'] = df['Date'].dt.year

	end_of_year = df.groupby('Year').agg({
		'Degradation': 'last',
		'IRR curve': 'last',
		'DSRA EOP': 'last',
		'Retained earnings BOP': 'last',
		'Distribution account EOP': 'last',
		'Senior debt EOP': 'last',
		'LLCR': 'last',
		'PLCR': 'last',

	}).to_dict(orient='list')

	return end_of_year




def calc_construction_costs(request, inputs, flags):
	
	inp_construction_costs = get_constr_costs(request, inputs)
	
	construction_costs = np.hstack([
		inp_construction_costs,
		np.zeros(flags['operations'].size - inp_construction_costs.size)
	]) * flags['construction']
	
	construction_costs_cumul = construction_costs.cumsum()
	sum_construction_costs = np.sum(inp_construction_costs)
	
	return construction_costs, construction_costs_cumul, sum_construction_costs


def calc_capacity(inputs, flags, time_series):

	if inputs['technology'].startswith('Solar'):

		capacity_before_degradation = inputs['panels_capacity']*flags['operations']
		degradation_factor = 1/(1+inputs['degradation'])**time_series['years_from_COD_avg']
		capacity_after_degradation = capacity_before_degradation * degradation_factor

	else: 

		capacity_before_degradation = inputs['wind_turbine_installed']*1000*inputs['capacity_per_turbine']*flags['operations']
		degradation_factor = 1
		capacity_after_degradation = capacity_before_degradation

	capacity = {
		'before_degradation': capacity_before_degradation,
		'degradation_factor': degradation_factor,
		'after_degradation': capacity_after_degradation,
	}

	return capacity


def calc_index(inputs, years_from_base_dates, dict_scenario, key):

	sentivity_inflation = dict_scenario[key]["sensi_inf"]
	
	elec_index_indice = array_index(inputs['index_rate_merchant']+sentivity_inflation,years_from_base_dates['merchant_index'])
	contract_index_indice = array_index(inputs['index_rate_contract']+sentivity_inflation,years_from_base_dates['contracted_index'])
	opex_index_indice = array_index(inputs['index_rate_opex']+sentivity_inflation,years_from_base_dates['opex_index'])
	lease_index_indice = array_index(inputs['index_rate_lease']+sentivity_inflation,years_from_base_dates['lease_index'])


	index = {

		'merchant': elec_index_indice,
		'contracted': contract_index_indice,
		'opex': opex_index_indice,
		'lease': lease_index_indice,

	}
	
	return index


def calc_prices(request, time_series, inputs, flags, index, dict_scenario, key):


	dic_price_elec, dic_price_elec_keys = get_elec_prices(request, inputs['construction_end'],inputs['liquidation_date'], dict_scenario, key)



	merchant_prices_real = array_elec_prices(time_series['series_end_period_year'], dic_price_elec)
	contracted_prices_real = inputs['contract_price'] * flags['contract']

	merchant_prices_indexed = merchant_prices_real * index['merchant']
	contracted_prices_indexed = contracted_prices_real * index['contracted']
	
	prices = {

		'merchant_real': merchant_prices_real,
		'merchant_nom': merchant_prices_indexed,
		'contracted_real': contracted_prices_real,
		'contracted_nom': contracted_prices_indexed,
	}
	
	return prices, dic_price_elec_keys



def calc_revenues(production, prices, time_series):
	contracted_revenues = (production * prices['contracted_nom'] / 1000 * time_series['pct_in_contract_period'] * time_series['pct_in_operations_period'])
	
	market_revenues = (production * prices['merchant_nom'] / 1000 * (1-time_series['pct_in_contract_period']) * time_series['pct_in_operations_period'])
	
	total_revenues = contracted_revenues + market_revenues
	
	revenues = {

		'contracted': contracted_revenues,
		'merchant': market_revenues,
		'total': total_revenues,
	}

	return revenues



def calc_wc(inputs, days_series, revenues, opex,lease):
	revenues_in_period_paid = (1 - inputs['payment_delay_revenues'] / days_series['period']) * revenues['total']
	accounts_receivables_eop = revenues['total'] - revenues_in_period_paid
	accounts_receivables_bop = np.roll(accounts_receivables_eop, 1)

	costs_in_period_paid = (1 - inputs['payment_delay_costs'] / days_series['period']) * (opex+lease)
	accounts_payables_eop = (opex+lease) - costs_in_period_paid
	accounts_payables_bop = np.roll(accounts_payables_eop, 1)

	cashflows_from_creditors = np.ediff1d(accounts_receivables_eop, to_begin=accounts_receivables_eop[0])
	cashflows_from_debtors = np.ediff1d(accounts_payables_eop, to_begin=accounts_payables_eop[0])
	working_cap_movement = cashflows_from_debtors - cashflows_from_creditors
	
	return {
		'revenues_paid': revenues_in_period_paid,
		'acc_receivables_eop': accounts_receivables_eop,
		'acc_receivables_bop': accounts_receivables_bop,
		'costs_paid': costs_in_period_paid,
		'acc_payables_eop': accounts_payables_eop,
		'acc_payables_bop': accounts_payables_bop,
		'cashflows_from_creditors': cashflows_from_creditors,
		'cashflows_from_debtors': cashflows_from_debtors,
		'wc_variation': working_cap_movement,
	}




def calc_distr_account(SHL_balance_bop, days_series, inputs, flags,
						  transfers_distribution_account, distributable_profit, injections, income_statement):
	
	
	SHL_balance_bop=np.array(SHL_balance_bop)
	period=np.array(days_series['period'])
	flag_operations=np.array(flags['operations'])
	flag_construction=np.array(flags['construction'])
	transfers_distribution_account=np.array(transfers_distribution_account)
	distributable_profit=np.array(distributable_profit)
	SHL_injections=np.array(injections['SHL'])
	net_income=np.array(income_statement['net_income'])




	for i in range(100):
	
		SHL_interests_operations = SHL_balance_bop * inputs['SHL_margin'] * period / 360 * flag_operations
		SHL_interests_construction = SHL_balance_bop * inputs['SHL_margin'] * period / 360 * flag_construction

		SHL_interests_paid = np.minimum(transfers_distribution_account, SHL_interests_operations)
		cash_available_for_dividends = transfers_distribution_account - SHL_interests_paid
		dividends_paid = np.minimum(cash_available_for_dividends, distributable_profit)
		cash_available_for_SHL_repayments = cash_available_for_dividends - dividends_paid
		SHL_repayments = np.minimum(SHL_balance_bop, cash_available_for_SHL_repayments)
		cash_available_for_redemption = cash_available_for_SHL_repayments - SHL_repayments
		
		distribution_account_eop = (transfers_distribution_account - SHL_interests_paid - dividends_paid - SHL_repayments).cumsum()
		distribution_account_bop = distribution_account_eop - (transfers_distribution_account - SHL_interests_paid - dividends_paid - SHL_repayments)

		SHL_balance_eop = (SHL_injections + SHL_interests_construction - SHL_repayments).cumsum()
		SHL_balance_bop = SHL_balance_eop - (SHL_injections + SHL_interests_construction - SHL_repayments)

		retained_earnings_eop = (net_income - dividends_paid).cumsum()
		retained_earnings_bop = retained_earnings_eop - (net_income - dividends_paid)
		
		distributable_profit = np.clip(retained_earnings_bop + net_income, 0, None)

	result = {
			'SHL_interests_operations': SHL_interests_operations,
			'SHL_interests_construction': SHL_interests_construction,
			'cash_available_for_SHL_interests': transfers_distribution_account,
			'SHL_interests_paid': SHL_interests_paid,
			'cash_available_for_dividends': cash_available_for_dividends,	
			'dividends_paid': dividends_paid,
			'cash_available_for_SHL_repayments': cash_available_for_SHL_repayments,
			'SHL_repayments': SHL_repayments,
			'cash_available_for_redemption':cash_available_for_redemption,
			'distribution_account_eop': distribution_account_eop,
			'distribution_account_bop': distribution_account_bop,
			'SHL_balance_eop': SHL_balance_eop,
			'SHL_balance_bop': SHL_balance_bop,
			'retained_earnings_eop': retained_earnings_eop,
			'retained_earnings_bop': retained_earnings_bop,
			'distributable_profit': distributable_profit,
		}

	return result



def calc_injections(inputs, total_uses_cumul, total_costs, total_uses, debt_amount):
	

	equity_amount= total_costs-debt_amount
	gearing_eff = (debt_amount/total_costs)

	if inputs['injection_choice'] == 1:
		equity_injections_cumul = np.clip(total_uses_cumul, None, equity_amount) 
		equity_injections = np.ediff1d(equity_injections_cumul, to_begin=equity_injections_cumul[0])
		share_capital_injections = equity_injections*(1-inputs['subgearing'])
		SHL_injections = equity_injections*inputs['subgearing']
		senior_debt_drawdowns = total_uses - equity_injections
		senior_debt_drawdowns_cumul = senior_debt_drawdowns.cumsum()
	elif inputs['injection_choice'] == 2:
		senior_debt_drawdowns_cumul = np.clip(total_uses_cumul * gearing_eff, None, debt_amount)
		senior_debt_drawdowns = np.ediff1d(senior_debt_drawdowns_cumul, to_begin=senior_debt_drawdowns_cumul[0])
		equity_injections = total_uses - senior_debt_drawdowns
		share_capital_injections = equity_injections*(1-inputs['subgearing'])
		SHL_injections = equity_injections*inputs['subgearing']


	injections = {
			'share_capital': share_capital_injections,
			'SHL': SHL_injections,
			'equity': equity_injections,
			'debt': senior_debt_drawdowns,

		}

	return injections



def calc_senior_debt(senior_debt_drawdowns, senior_debt_repayments, inputs, days_series, flags, debt_amount):
	
	balance_eop = (senior_debt_drawdowns - senior_debt_repayments).cumsum()
	balance_bop = balance_eop + senior_debt_repayments - senior_debt_drawdowns


	interests_construction = balance_bop * inputs['debt_interest_rate'] * days_series['debt_interest_construction'] / 360
	interests_operations = balance_bop * inputs['debt_interest_rate'] * days_series['debt_interest_operations'] / 360

	interests = interests_construction + interests_operations

	upfront_fee=flags['construction_start']*debt_amount*inputs['debt_upfront_fee']

	senior_debt_available_eop = (debt_amount - balance_bop) * flags['construction']
	senior_debt_available_bop = senior_debt_available_eop + senior_debt_drawdowns

	commitment_fees=senior_debt_available_bop*inputs['debt_commitment_fee']*days_series['period']/360


	senior_debt = {

			'balance_eop': balance_eop,
			'balance_bop': balance_bop,
			'interests': interests,
			'interests_operations': interests_operations,
			'senior_debt_idc': interests_construction,
			'upfront_fee': upfront_fee,
			'senior_debt_available_eop': senior_debt_available_eop,
			'senior_debt_available_bop': senior_debt_available_bop,
			'commitment_fees': commitment_fees,

	}


	return senior_debt





def calc_capitalised_fees(senior_debt,SHL_interests_construction):

	capitalised_fees_cumul = (senior_debt['senior_debt_idc']+senior_debt['upfront_fee']+senior_debt['commitment_fees']+SHL_interests_construction).cumsum()

	return capitalised_fees_cumul



def create_params(inputs, date_series):

	params = {

		'construction_start': inputs['construction_start'],
		'construction_end': inputs['construction_end'],
		'COD': inputs['COD'],
		'debt_maturity':inputs['debt_maturity'],
		'end_of_operations': inputs['end_of_operations'],
		'liquidation_date': inputs['liquidation_date'],

		'contract_index_start_date':inputs['contract_index_start_date'],
		'merchant_index_start_date':inputs['merchant_index_start_date'],
		'opex_index_start_date':inputs['opex_index_start_date'],

		'start_contract':inputs['start_contract'],
		'end_contract':inputs['end_contract'],

		'series_start_period': date_series['start_period'],
		'series_end_period': date_series['end_period'] ,
	
		'series_start_operations': date_series['start_operations'],
		'series_end_operations': date_series['end_operations'] ,



		'series_start_contract':date_series['start_contract'],
		'series_end_contract':date_series['end_contract'],
		'series_start_contract_index':date_series['start_contract_index'],
		'series_end_contract_index':date_series['end_contract_index'],
		'series_start_elec_index':date_series['start_elec_index'],
		'series_end_elec_index':date_series['end_elec_index'],
		'series_start_opex_index':date_series['start_opex_index'],
		'series_end_opex_index':date_series['end_opex_index'],


		'series_start_debt_interests_construction':date_series['start_debt_interests_construction'],
		'series_end_debt_interests_construction':date_series['end_debt_interests_construction'],

		'series_start_debt_interests_operations':date_series['start_debt_interests_operations'],
		'series_end_debt_interests_operations':date_series['end_debt_interests_operations'],



		'lease_index_start_date':inputs['lease_index_start_date'],
		'series_start_lease_index':date_series['start_lease_index'],
		'series_end_lease_index':date_series['end_lease_index'],

		}

	return params



def calc_depreciation(sum_construction_costs, capitalised_fees_cumul, optimised_devfee, time_series, inputs,local_taxes):

	total_uses_depreciable = sum_construction_costs+max(capitalised_fees_cumul)+optimised_devfee+local_taxes
	depreciation = 	total_uses_depreciable*time_series['years_during_operations']/inputs['operating_life']

	return depreciation	



def calc_income_statement(depreciation, EBITDA, senior_debt_interests_operations, SHL_interests_operations, inputs):
	EBIT = EBITDA - depreciation
	EBT = EBIT - senior_debt_interests_operations - SHL_interests_operations
	corporate_income_tax = np.clip(inputs['income_tax_rate'] * EBT, 0, None)
	net_income = EBT - corporate_income_tax

	income_statement = { 
		'EBIT':EBIT,
		'EBT':EBT,
		'corporate_income_tax':corporate_income_tax,
		'net_income':net_income,
	}

	return income_statement


def calc_cf_statement(EBITDA,working_cap,income_statement,construction_costs,senior_debt_idc,development_fee,upfront_fee,commitment_fees,injections,local_taxes):
	
	cash_flows_operating=EBITDA+working_cap['wc_variation']-income_statement['corporate_income_tax']
	cash_flows_investing=-(construction_costs+senior_debt_idc+development_fee+local_taxes)
	cash_flows_financing=upfront_fee+commitment_fees+injections['debt']+injections['equity']

	cf_statement = { 
		'cash_flows_operating':cash_flows_operating,
		'cash_flows_investing':cash_flows_investing,
		'cash_flows_financing':cash_flows_financing,

	}

	return cf_statement



def calc_discount_factor(senior_debt, days_series, flags):

	avg_interest_rate = np.where(days_series['debt_interest_operations'] != 0,np.divide(senior_debt['interests_operations'], senior_debt['balance_bop'], out=np.zeros_like(senior_debt['interests_operations']), where=senior_debt['balance_bop'] != 0) / days_series['debt_interest_operations'] * 360,0)	
	condition = flags['debt_amo'] == 1
	discount_factor = np.where(condition, (1 / (1 + (avg_interest_rate * days_series['debt_interest_operations'] / 360))), 1)

	discount_factor_cumul=discount_factor.cumprod()

	discount_factor = { 
		'avg_interest_rate':avg_interest_rate,
		'discount_factor':discount_factor,
		'discount_factor_cumul':discount_factor_cumul,

	}

	return discount_factor

def calc_debt_amount_DSCR(CFADS_amo, inputs, flags,discount_factor):

	target_DSCR = inputs['debt_target_DSCR']*flags['debt_amo']
	target_DS = CFADS_amo/inputs['debt_target_DSCR']

	debt_amount = npv(target_DS,discount_factor['discount_factor_cumul'])

	debt_amount_DSCR = { 
		'target_DSCR':target_DSCR,
		'target_DS':target_DS,
		'debt_amount':debt_amount,

	}


	return debt_amount_DSCR



def calc_senior_debt_repayments_target(injections,CFADS_amo,discount_factor,senior_debt):

	DSCR_sculpting = calc_DSCR_sculpting(injections,CFADS_amo,discount_factor)
	senior_debt_repayments_target = np.maximum(0, np.minimum(senior_debt['balance_bop'], CFADS_amo / DSCR_sculpting - senior_debt['interests_operations']))

	return senior_debt_repayments_target



def calc_DSCR_sculpting(injections,CFADS_amo,discount_factor):

	cumul_debt_drawn  = sum(injections['debt'])				
	npv_CFADS = npv(CFADS_amo,discount_factor['discount_factor_cumul'])
	DSCR_sculpting = npv_CFADS / cumul_debt_drawn if cumul_debt_drawn > 0 else 1


	return DSCR_sculpting



def calc_dsra(CFADS, DS_effective, inputs, flags, dsra_bop):
	cash_available_for_dsra = np.maximum(CFADS - DS_effective, 0)
	dsra_target = calc_dsra_target(inputs, DS_effective) * flags['debt_amo']
	DSRA_initial_funding = calc_dsra_funding(dsra_target) * flags['construction_end']
	dsra_additions_available = np.minimum(cash_available_for_dsra, dsra_target)
	dsra_additions_required = np.maximum(dsra_target - dsra_bop, 0)
	dsra_additions_required_available = np.minimum(dsra_additions_available, dsra_additions_required)
	dsra_target = dsra_target + DSRA_initial_funding
	dsra_eop = np.clip((DSRA_initial_funding + dsra_additions_required_available).cumsum(), 0, dsra_target)
	dsra_eop_mov = np.ediff1d(dsra_eop, to_begin=dsra_eop[0])
	dsra_additions = np.maximum(dsra_eop_mov, 0)
	dsra_release = np.minimum(dsra_eop_mov, 0)
	dsra_bop = np.roll(dsra_eop, 1)
	dsra_mov = (dsra_eop - dsra_bop)
	DSRA_initial_funding_max = max(DSRA_initial_funding)


	DSRA = { 
		'cash_available_for_dsra':cash_available_for_dsra,
		'dsra_target':dsra_target,
		'dsra_additions_required':dsra_additions_required,

		'DSRA_initial_funding':DSRA_initial_funding,
		'dsra_eop':dsra_eop,
		'dsra_additions':dsra_additions,
		'dsra_release':dsra_release,
		'dsra_bop':dsra_bop,
		'dsra_mov':dsra_mov,
		'DSRA_initial_funding_max':DSRA_initial_funding_max,

	}

	
	return DSRA, DSRA_initial_funding, DSRA_initial_funding_max, dsra_bop


def calc_audit(total_uses, total_sources, total_assets, total_liabilities, final_repayment_date_debt, inputs):
	audit_financing_plan = total_uses - total_sources
	audit_balance_sheet = total_assets - total_liabilities
	

	check_financing_plan_balanced = abs(sum(audit_financing_plan))<0.01
	check_balance_sheet_balanced = abs(sum(audit_balance_sheet))<0.01	


	check_debt_maturity = (final_repayment_date_debt == inputs['debt_maturity'])		

	audit = { 
		'balance_sheet':audit_balance_sheet,
		'financing_plan':audit_financing_plan,
	}

	check = { 
		'balance_sheet':check_balance_sheet_balanced,
		'financing_plan':check_financing_plan_balanced,
		'debt_maturity':check_debt_maturity,

	}

	check_all = all(check.values())

	return audit, check, check_all


def create_price_elec_dict(request, construction_end,liquidation, dict_scenario, key):
	
	choice = dict_scenario[key]["elec_price"]

	construction_end_year = construction_end.year
	liquidation_year = liquidation.year

	years = [str(year) for year in range(construction_end_year, liquidation_year+1)]

	if choice == 1:
		prefix = 'price_elec_low_y'
	elif choice == 2:
		prefix = 'price_elec_med_y'
	else:
		prefix = 'price_elec_high_y'

	dic_price_elec = {}

	for i, year in enumerate(years):
		key = f'{prefix}{i+1}'
		value = float(request.POST[key])
		dic_price_elec[year] = value

	return dic_price_elec


def calc_dsra_target(inputs,DS_effective):

	look_forward=int(inputs['dsra']/inputs['periodicity'])	

	looking_forward_debt_service = []
	for i in range(len(DS_effective)):
		forward_debt_service = sum(DS_effective[i+1:min(i+1+look_forward, len(DS_effective))])
		looking_forward_debt_service.append(forward_debt_service)

	return looking_forward_debt_service

def calc_dsra_funding(dsra_target):
	
	positive_sum = 0
	count = 0

	for num in dsra_target:
		if num > 0:
			positive_sum += num
			count += 1

		if count == 1:
			break

	return positive_sum




def calc_years_from_base_dates(days_series, days_in_year):
	
	keys = ['contracted_index', 'merchant_index', 'opex_index', 'lease_index']
	
	years_from_base_dates = {}
	for key in keys:
		years = (days_series[key] / days_in_year).cumsum()
		years_from_base_dates[key] = years

	return years_from_base_dates




def import_seasonality(request):
	inp_seasonality = np.zeros(12)
	for i in range(1, 13):
		key = 'seasonality_m{}'.format(i)
		inp_seasonality[i - 1] = float(request.POST[key])
	return inp_seasonality

def get_constr_costs(request, inputs):
	construction_costs = np.zeros(24)

	delta = relativedelta(inputs['construction_end'], inputs['construction_start'])
	months = delta.years * 12 + delta.months + 1	

	for i in range(1, months+1):
		key = 'costs_m{}'.format(i)
		construction_costs[i-1] = float(request.POST[key])
	return construction_costs


def create_period_series(series_start_period, series_end_period, inputs):
	dates = {
		'contract': (inputs['start_contract'], inputs['end_contract']),
		'contract_index': (inputs['contract_index_start_date'], inputs['end_contract']),
		'elec_index': (inputs['merchant_index_start_date'], inputs['end_of_operations']),
		'opex_index': (inputs['opex_index_start_date'], inputs['end_of_operations']),
		'debt_interests_construction': (inputs['construction_start'], inputs['construction_end']),
		'debt_interests_operations': (inputs['COD'], inputs['debt_maturity_date']),
		'lease_index': (inputs['lease_index_start_date'], inputs['end_of_operations']),

		'operations': (inputs['COD'], inputs['end_of_operations']),

	}

	series = {key: generate_period_series(series_start_period, series_end_period, start, end) for key, (start, end) in dates.items()}
	
	return series


def generate_period_series(series_start_period,series_end_period,start,end):
	
	start_period_series = array_time(series_start_period,start,end)
	end_period_series = array_time(series_end_period,start,end)
	
	return start_period_series, end_period_series



def create_series(inputs):
	series_start_period, series_end_period = create_timeline_series(inputs)
	series = create_period_series(series_start_period, series_end_period, inputs)


	series_start_operations, series_end_operations = series['operations']


	series_start_contract, series_end_contract = series['contract']
	series_start_contract_index, series_end_contract_index = series['contract_index']
	series_start_elec_index, series_end_elec_index = series['elec_index']
	series_start_opex_index, series_end_opex_index = series['opex_index']
	series_start_debt_interests_construction, series_end_debt_interests_construction = series['debt_interests_construction']
	series_start_debt_interests_operations, series_end_debt_interests_operations = series['debt_interests_operations']

	series_start_lease_index, series_end_lease_index = series['lease_index']



	all_series = {
		'start_period': series_start_period,
		'end_period': series_end_period,
		'start_contract': series_start_contract,
		'end_contract': series_end_contract,
		'start_contract_index': series_start_contract_index,
		'end_contract_index': series_end_contract_index,
		'start_elec_index': series_start_elec_index,
		'end_elec_index': series_end_elec_index,
		'start_opex_index': series_start_opex_index,
		'end_opex_index': series_end_opex_index,
		'start_debt_interests_construction': series_start_debt_interests_construction,
		'end_debt_interests_construction': series_end_debt_interests_construction,
		'start_debt_interests_operations': series_start_debt_interests_operations,
		'end_debt_interests_operations': series_end_debt_interests_operations,

		'start_operations': series_start_operations,
		'end_operations': series_end_operations,
		'start_lease_index': series_start_lease_index,
		'end_lease_index': series_end_lease_index,
	}

	return all_series


def import_dev_tax_commune(request,city_name):

	response = json.loads(get_data(request, city_name).content)
	dev_tax_commune = float(response['data']['results'][0]['taux'])

	return dev_tax_commune

def calc_local_taxes(request,inputs,flags,dev_tax_commune):

	

	total_rate=dev_tax_commune/100+inputs['dev_tax_department_tax']
	
	if inputs['technology'].startswith('Solar'):
		development_tax=inputs['panels_surface']*inputs['dev_tax_taxable_base_solar']*total_rate/1000*flags['construction_start']
		archeological_tax=inputs['panels_surface']*inputs['archeological_tax_base_solar']*inputs['archeological_tax']/1000*flags['construction_start']

	else: 
		development_tax=inputs['wind_turbine_installed']*inputs['dev_tax_taxable_base_wind']*total_rate/1000*flags['construction_start']
		archeological_tax=0*flags['construction_start']

	local_taxes = development_tax+archeological_tax

	return development_tax, archeological_tax,local_taxes

def calc_production(request,seasonality,capacity_after_degradation, dict_scenario, key):

	seasonality=np.array(seasonality,dtype=float)

	P90 = float(request.POST['p90_10y'])/1000*seasonality*capacity_after_degradation
	P75 = float(request.POST['p75'])/1000*seasonality*capacity_after_degradation
	P50 = float(request.POST['p50'])/1000*seasonality*capacity_after_degradation

	if dict_scenario[key]["prod"] == 1:
		production = P90
	elif dict_scenario[key]["prod"] == 2:
		production = P75
	else:
		production = P50

	return production


def determine_debt_constraint(debt_amount,debt_amount_gearing):

	if debt_amount>debt_amount_gearing:
		constraint = "Gearing"
	else: 
		constraint = "DSCR"

	return constraint


def create_table_sensi(results_sensi):
	metrics = ["Min DSCR", "Avg. DSCR", "Min LLCR", "Equity IRR", "Audit"]
	percent_flags = [False, False, False, True, False]
	
	if len(metrics) != len(percent_flags):
		raise ValueError("The length of 'metrics' and 'percent_flags' must be equal.")
	
	table_sensi = pd.DataFrame()
	table_sensi[""] = metrics
	
	first_scenario_processed = False  # Flag to keep track of whether the first scenario has been processed

	for scenario in results_sensi.keys():
		scenario_data = []
		for i in range(len(metrics)):
			if metrics[i] == "Audit":  # Handling Audit metric separately
				scenario_data.append(str(results_sensi[scenario][i]))
			else:
				scenario_data.append(format_sensi_data(results_sensi[scenario][i], percent_flags[i]))
		table_sensi[scenario] = scenario_data

		if not first_scenario_processed:
			table_sensi['Blank Row'] = [''] * len(metrics)  # Adding a blank row
			first_scenario_processed = True  # Updating the flag
			
	return table_sensi


def create_table_uses(sum_construction_costs,optimised_devfee,senior_debt_fees_constr,total_costs,DSRA_initial_funding_max,development_tax_sum,archeological_tax_sum):

	senior_debt_i_and_fees =sum(senior_debt_fees_constr.values())
	local_taxes = development_tax_sum+archeological_tax_sum

	table_table_uses = pd.DataFrame({
				"Construction costs":["{:.1f}".format(sum_construction_costs)],
				"Development fee":["{:.1f}".format(optimised_devfee)],
				"Debt interests & fees":["{:.1f}".format(senior_debt_i_and_fees)],
				"Upfront fee":["{:.1f}".format(senior_debt_fees_constr['upfront_fee'])],
				"Commitment fees":["{:.1f}".format(senior_debt_fees_constr['commitment_fees'])],				
				"IDC":["{:.1f}".format(senior_debt_fees_constr['idc'])],
				"Local taxes":["{:.1f}".format(local_taxes)],
				"Development tax":["{:.1f}".format(development_tax_sum)],
				"Archeological tax":["{:.1f}".format(archeological_tax_sum)],
				"Initial DSRA funding":["{:.1f}".format(DSRA_initial_funding_max)],
				"Total":["{:.1f}".format(total_costs)],
				})
	return table_table_uses

def create_table_sources(injections,debt_amount):

	share_capital_drawn = sum(injections['share_capital'])
	shl_drawn = sum(injections['SHL'])
	equity_drawn=share_capital_drawn+shl_drawn

	fp_sources = equity_drawn+debt_amount

	table_sources = pd.DataFrame({
				"Equity":["{:.1f}".format(equity_drawn)],				
				"Share capital":["{:.1f}".format(share_capital_drawn)],
				"Shareholder loan":["{:.1f}".format(shl_drawn)],
				"Senior debt":["{:.1f}".format(debt_amount)],
				"Total":["{:.1f}".format(fp_sources)],
				})
	return table_sources




def create_table(results, metrics, formats={}):
	table = {}

	for metric, data in zip(metrics, results):
		fmt = formats.get(metric, "{}")
		formatted_val = fmt.format(data)
		table[metric] = {0: formatted_val}

	return table

debt_metrics = ["Debt amount", "Constraint", "Effective gearing", "Tenor (door-to-door)", "Average life", "Average DSCR", "Debt IRR"]
debt_formats = {
    "Debt amount": "{:.0f}",
    "Effective gearing": "{:.2%}",
    "Tenor (door-to-door)": "{:.1f}",
    "Average life": "{:.1f}",
    "Average DSCR": "{:.2f}x",
    "Debt IRR": "{:.2%}"
}

equity_metrics = ["Share capital IRR", "Shareholder loan IRR", "Equity IRR", "Payback date", "Payback time"]
equity_formats = {
    "Share capital IRR": "{:.2%}",
    "Shareholder loan IRR": "{:.2%}",
    "Equity IRR": "{:.2%}"
}

project_irr_metrics = ["Project IRR (pre-tax)", "Project IRR (post-tax)"]
project_irr_formats = {
    "Project IRR (pre-tax)": "{:.2%}",
    "Project IRR (post-tax)": "{:.2%}"
}

audit_metrics = ["Financing plan", "Balance sheet", "Debt maturity"]

def create_table_debt(results_debt_displayed):
    return create_table(results_debt_displayed, debt_metrics, debt_formats)

def create_table_equity(results_equity_displayed):
    return create_table(results_equity_displayed, equity_metrics, equity_formats)

def create_table_projectIRR(results_projectIRR_displayed):
    return create_table(results_projectIRR_displayed, project_irr_metrics, project_irr_formats)

def create_table_audit(results_audit_displayed):
    return create_table(results_audit_displayed, audit_metrics)





def find_payback_date(series_end_period,equity_cash_flows_cumul):

	# Find the indices where cumulative_equity is greater than or equal to zero
	valid_indices = np.where(equity_cash_flows_cumul >= 0)[0]

	if len(valid_indices) > 0:
		# Find the minimum date_series_end_period value at the valid indices
		payback_date_index = valid_indices[np.argmin(series_end_period[valid_indices])]
		payback_date = series_end_period[payback_date_index]
	else:
		payback_date = None
	"""payback_date = df.loc[df['Cumulative Equity for payback'] >= 0, 'Date Period end'].min()"""
	return payback_date






def compute_npv(cfads, discount_rate,series_end_period):
	npvs = []

	series_end_period=pd.to_datetime(series_end_period).dt.date
	

	for i in range(len(cfads)):
		npv = 0
		if cfads[i] > 1:
			for j in range(i, len(cfads)):
				end_date = series_end_period[j]
				start_date = series_end_period[i-1]
				time_delta = (end_date - start_date).days/365.25
				npv += cfads[j] / ((1+discount_rate) ** (time_delta))

			npvs.append(npv)
		else: 
			npvs.append(0)

	return npvs





def calculate_ratios(avg_interest_rate, CFADS_amo, CFADS, senior_debt_balance_eop, series_end_period):
	avg_i = avg_interest_rate[avg_interest_rate > 0].mean()

	LLCR_discounted_CFADS = compute_npv(CFADS_amo, avg_i, series_end_period)
	PLCR_discounted_CFADS = compute_npv(CFADS, avg_i, series_end_period)

	LLCR = divide_with_condition(LLCR_discounted_CFADS, senior_debt_balance_eop)
	PLCR = divide_with_condition(PLCR_discounted_CFADS, senior_debt_balance_eop)

	return LLCR, PLCR


def divide_with_condition(numerator, denominator):
	# Divide numerator by denominator, set 0 where denominator is less than or equal to 0.01
	return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0.01)

def find_last_payment_date(series_end_period,boolean_array):
	boolean_array = boolean_array > 0.1
	new_array = [date if boolean else 0 for boolean, date in zip(boolean_array, series_end_period)]
	non_zero_dates = [date for date in new_array if date != 0]
	max_date = max(non_zero_dates)
	return max_date



def calculate_tenor(final_repayment_date, construction_start):
	time_difference = final_repayment_date-construction_start
	tenor = round(time_difference.days / 365.25, 1)
	return tenor


def format_sensi_data(val, percent=False):
	if percent:
		return "{:.2%}".format(val)
	else:
		return "{:.2f}x".format(val)


def create_IRR_curve(equity_cash_flows,series_end_period):

	irr_values = []

	# Iterate through each period and calculate the IRR up to that period
	for i in range(1, len(equity_cash_flows)+1):
		subset_cash_flows = equity_cash_flows.iloc[:i]
		subset_dates = pd.to_datetime(series_end_period.iloc[:i]).dt.date

		try:
			irr = xirr(subset_dates, subset_cash_flows)*100
		except:
			irr = 0.0

		irr_values.append(max(irr,0,0))

	return irr_values 


def calc_debt_fees_construction(senior_debt):

	idc = sum(senior_debt['senior_debt_idc'])
	upfront_fee = np.max(senior_debt['upfront_fee'])
	commitment_fees= sum(senior_debt['commitment_fees'])

	senior_debt_fees_constr = {

		'idc' : idc,
		'upfront_fee' : upfront_fee,
		'commitment_fees' : commitment_fees,


	}


	return senior_debt_fees_constr



def optimise_devfee(request,debt_amount,sum_construction_costs,senior_debt_fees_constr,DSRA_initial_funding_max,local_taxes):

	dev_fee_switch = int(request.POST['devfee_choice'])
	gearing_max = float(request.POST['debt_gearing_max'])/100

	total_costs_wo_devfee = sum_construction_costs+sum(senior_debt_fees_constr.values())+DSRA_initial_funding_max+local_taxes


	if dev_fee_switch == 1:
		optimised_devfee = max(debt_amount/gearing_max-total_costs_wo_devfee,0)
	else:
		optimised_devfee = 0

	return optimised_devfee

def array_time(timeline,start,end):	
	timeline_result = timeline.clip(lower=pd.Timestamp(start),upper=pd.Timestamp(end))
	return timeline_result

def array_flag(timeline_end,start,timeline_start,end):	
	flag_result = (timeline_end>=pd.to_datetime(start))*(timeline_start<=pd.to_datetime(end)).astype(int)*(timeline_end!=timeline_start)
	return flag_result

def array_days(arr_end_date,arr_start_date,flag):
	number_days = ((arr_end_date-arr_start_date).dt.days + 1)*flag
	return number_days

def array_index(indexation_rate,indexation_year):
	arr_indexation = (1+indexation_rate)**indexation_year
	return arr_indexation

def npv(arr_cash_flow,arr_discount_factor):
	npv = sum(arr_cash_flow*arr_discount_factor)
	return npv

def array_elec_prices(series_end_period_year,dic_price_elec):
	electricity_prices = []
	
	for row in series_end_period_year:
		if str(row) in dic_price_elec.keys():
			electricity_prices.append(dic_price_elec[str(row)])
		else:
			electricity_prices.append(0)
	
	return electricity_prices

def create_seasonality_vector(request,series_start_period,series_end_period):
	
	inp_seasonality = import_seasonality(request)

	data = {'start':series_start_period,
			'end':series_end_period}

	df = pd.DataFrame(data)

	df_seasonality_result = pd.DataFrame(columns=series_end_period)

	for index, row in df.iterrows():
		start_date = row['start']
		end_date = row['end']
		dates_in_period = pd.date_range(start=start_date, end=end_date).values.astype('datetime64[D]').tolist()
		
		for i in range(1,13):
			count = 0
			days_in_month = 0

			try:
				for value in dates_in_period:
					
					if value.month == i:
						count += 1
						days_in_month = calendar.monthrange(value.year, value.month)[1]
				
				df_seasonality_result.loc[i,end_date] = count/days_in_month

			except ZeroDivisionError:

				df_seasonality_result.loc[i,end_date] = 0

	df_seasonality_result=df_seasonality_result.mul(inp_seasonality, axis=0)
	arr_time_seasonality = df_seasonality_result.sum(axis=0)
	arr_time_seasonality = arr_time_seasonality.values.tolist()

	return arr_time_seasonality

def last_day_month(period):	
	last_day_month = period.replace(day = calendar.monthrange(period.year, period.month)[1])
	return last_day_month

def first_day_month(date):
	first_day_month = date.replace(day=1)
	return first_day_month

def first_day_next_month(date,inputs):
	first_day_next_month = date.replace(day=1) + relativedelta(months=inputs['periodicity']) + datetime.timedelta(days=-1)
	return first_day_next_month

def get_quarters(date_list):
	date_series = pd.Series(date_list)
	quarters = pd.to_datetime(date_series, format='%Y-%m-%d').dt.quarter
	return quarters.tolist()
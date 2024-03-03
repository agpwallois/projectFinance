# Standard library imports
import calendar
import datetime
import time
from collections import defaultdict
# Third-party imports
import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta
from dateutil import parser
from dateutil.parser import ParserError
from pyxirr import xirr
import traceback
import math


# Django imports
from django.http import JsonResponse
from django.views.generic import ListView
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models import Sum, Case, When, Value, IntegerField, F

# Application-specific imports
from .forms import ProjectForm
from .models import Project, ComputationResult, SponsorCaseResult
from .property_taxes import property_tax, tfpb_standard_reduction
import requests
from django.urls import reverse
from api_integration.views import get_data
from sofr.views import create_SOFRForwardCurve
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
	project_data = {}
	
	project_counts_tech = Project.objects.values('technology').annotate(total_projects=Count('id'))
	project_counts_country = Project.objects.values('country').annotate(total_projects=Count('id'))


	capacity_per_tech = Project.objects.filter(financial_close_check=False).values('technology').annotate(
		total_capacity=Sum(
			Case(
				When(technology='Wind', then=F('wind_turbine_installed') * F('capacity_per_turbine') * 1000),
				default=F('panels_capacity'),
				output_field=IntegerField(),
			)
		)
	)

	capacity_per_country = Project.objects.filter(financial_close_check=False).values('country').annotate(
		total_capacity=Sum(
			Case(
				When(technology='Wind', then=F('wind_turbine_installed') * F('capacity_per_turbine') * 1000),
				default=F('panels_capacity'),
				output_field=IntegerField(),
			)
		)
	)

	for project in projects:
		if project.technology == 'Wind':
			project.calculated_value = project.wind_turbine_installed * project.capacity_per_turbine * 1000
		else:
			project.calculated_value = project.panels_capacity


	for project in projects:
		try:
			sponsor_result = SponsorCaseResult.objects.get(project=project).sponsor_case_result
			project_data[project.id] = sponsor_result
		except SponsorCaseResult.DoesNotExist:
			# Handle the case where computed data doesn't exist for a project
			project_data[project.id] = None


	technology_yearly_total_revenues_sum = defaultdict(dict)
	country_yearly_total_revenues_sum = defaultdict(dict)

	for project in projects:
		try:
			sponsor_result = SponsorCaseResult.objects.get(project=project).sponsor_case_result
			technology = project.technology
			country = project.country

			for year, value in sponsor_result['Dates']['Period end'].items():
				year = int(year)

				current_sum = sponsor_result['IS']['Total revenues'].get(str(year), 0)

				technology_yearly_total_revenues_sum[technology][year] = \
				technology_yearly_total_revenues_sum[technology].get(year, 0) + current_sum

				country_yearly_total_revenues_sum[country][year] = \
				country_yearly_total_revenues_sum[country].get(year, 0) + current_sum

		except SponsorCaseResult.DoesNotExist:
			pass
	

	yearly_revenues_technology = json.dumps(technology_yearly_total_revenues_sum)
	yearly_revenues_country = json.dumps(country_yearly_total_revenues_sum)

	sofr = import_sofr(request)


	context = {'projects': projects,
				'project_counts_tech': project_counts_tech,
				'project_counts_country': project_counts_country,
				'capacity_per_tech': capacity_per_tech,
				'capacity_per_country': capacity_per_country,
				'project_data': project_data,
				'yearly_revenues_technology': yearly_revenues_technology,
				'yearly_revenues_country': yearly_revenues_country,
				'sofr':sofr,
	}


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
		computation_to_display = {}
		results_to_display = {}

		for key in dict_scenario:
			
			production = calc_production(request,seasonality,capacity['after_degradation'], dict_scenario, key)*(1+dict_scenario[key]["sensi_prod"]) 
			capacity_factor = calc_capacity_factor(production,installed_capacity,days_series['days_operations'])


			production_under_contract = production * time_series['pct_in_contract_period'] * time_series['pct_in_operations_period']
			
			production_under_contract_cumul = calc_production_cumul(production_under_contract,flags['start_calendar_year'])

			contract_price = calc_contract_price(inputs['contract'],inputs['wind_turbine_installed'], inputs['rotor_diameter'],production_under_contract, production_under_contract_cumul, capacity_factor, days_series,time_series,flags)
		
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

			debt_fees = senior_debt['senior_debt_idc']+senior_debt['upfront_fee']+senior_debt['commitment_fees']
	

			valuation = calc_valuation(inputs['valuation_df'],date_series['end_period'],equity_cash_flows)

			dict_to_display = {
				"Dates": {
					"Period start": format_date(date_series,'start_period').tolist(),
					"Period end": format_date(date_series,'end_period').tolist(),
				},
				"FlagsC": {
					"Construction": flags['construction'].tolist(),
					"Construction start": flags['construction_start'].tolist(),
					"Construction end": flags['construction_end'].tolist(),			
				},
				"FlagsM": {
					"Year": time_series['series_end_period_year'].tolist(),
					"Days in period": days_series['period'].tolist(),
					"Days in year": time_series['days_in_year'].tolist(),
					"Years in period": time_series['years_in_period'].tolist(),		
					"Quarter": time_series['quarters'],	
					"Start of calendar year": flags['start_calendar_year'].tolist(),				
				},
				"FlagOftk_i": {
					"Indexation period": flags['contract_index_period'].tolist(),
					"Indexation start date": format_date(date_series,'start_contract_index').tolist(),
					"Indexation end date": format_date(date_series,'end_contract_index').tolist(),
					"Indexation (days)": days_series['contracted_index'] .tolist(),
					"Indexation": index['contracted'].tolist(),			
				},
				"FlagOp": {
					'Operations': flags['operations'].tolist(),
					'Years from COD (BoP)': time_series['years_from_COD_bop'].tolist(),
					'Years from COD (EoP)': time_series['years_from_COD_eop'].tolist(),
					'Years from COD (avg.)': time_series['years_from_COD_avg'].tolist(),
					'Years during operations': time_series['years_during_operations'].tolist(),
					'Liquidation': flags['liquidation'].tolist(),
					'Liquidation end': flags['liquidation_end'].tolist(),
					'Seasonality':seasonality,
					'Days in operations':days_series['days_operations'].tolist(),
					'Percentage in operations period': time_series['pct_in_operations_period'].tolist(),		
				},				
				"FlagFin": {
					"Amortisation period": flags["debt_amo"].tolist(),	
					"Days during construction": days_series["debt_interest_construction"].tolist(),	
					"Days during operations": days_series["debt_interest_operations"].tolist(),	
				},
				"IS": {
					"Contracted revenues": revenues["contracted"].tolist(),
					"Uncontracted electricity revenues": revenues["merchant"].tolist(),
					"Total revenues": revenues["total"].tolist(),
					"Operating expenses": opex.tolist(),
					"Lease": (-1*lease).tolist(),
					"Property tax": (-1*tfpb).tolist(),
					"EBITDA": EBITDA.tolist(),
					"Depreciation": (-1*depreciation).tolist(),
					"EBIT": income_statement["EBIT"].tolist(),
					"Senior debt interests": (-1*senior_debt["interests_operations"]).tolist(),
					"Shareholder loan interests": (-1*SHL_interests_operations).tolist(),
					"EBT": income_statement["EBT"].tolist(),
					"Corporate income tax": (-1*income_statement["corporate_income_tax"]).tolist(),
					"Net income": income_statement["net_income"].tolist(),
				  },
				"Mkt_i": {
					"Indexation": index["merchant"].tolist(),
					"Indexation (days)": days_series["merchant_index"].tolist(),
					"Indexation end date": format_date(date_series, "end_elec_index").tolist(),
					"Indexation period": flags["merchant_index_period"].tolist(),
					"Indexation start date": format_date(date_series, "start_elec_index").tolist(),
				},
				"Opex": {
					"Indexation": index["opex"].tolist(),
					"Indexation (days)": days_series["opex_index"].tolist(),
					"Indexation end date": format_date(date_series, "end_opex_index").tolist(),
					"Indexation period": flags["opex_index_period"].tolist(),
					"Indexation start date": format_date(date_series, "start_opex_index").tolist(),
					"Years from indexation start date": years_from_base_dates["opex_index"].tolist(),
				},
				"Lease": {
					"Indexation": index["lease"].tolist(),
					"Indexation (days)": days_series["lease_index"].tolist(),
					"Indexation end date": format_date(date_series, "end_lease_index").tolist(),
					"Indexation period": flags["lease_index_period"].tolist(),
					"Indexation start date": format_date(date_series, "start_lease_index").tolist(),
					"Years from indexation start date": years_from_base_dates["lease_index"].tolist(),
				},
				"Price": {
					"Contract price (unindexed)": prices["contracted_real"].tolist(),
					"Contract price (unindexed) correct": contract_price.tolist(),

					"Contract price (indexed)": prices["contracted_nom"].tolist(),
					"Electricity market price (unindexed)": prices["merchant_real"],
					"Electricity market price (indexed)": prices["merchant_nom"].tolist(),
				},
				"Prod": {
					"Capacity after degradation": capacity["after_degradation"].tolist(),
					"Capacity before degradation": capacity["before_degradation"].tolist(),
					"Capacity degradation factor": capacity["degradation_factor"].tolist(),
					"Production": production.tolist(),
					"Capacity factor": capacity_factor.tolist(),

					"Contracted production in calendar year to date": production_under_contract_cumul.tolist(),
				},
				"WCRec": {
					"Accounts receivables (BoP)": working_cap["acc_receivables_bop"].tolist(),
					"Revenue accrued in period": revenues["total"].tolist(),
					"Payment received in period": ((-1*working_cap["revenues_paid"])+(-1*working_cap["acc_receivables_bop"])).tolist(),
					"Accounts receivables (EoP)": working_cap["acc_receivables_eop"].tolist(),
				},
				"WCPay": {
					"Accounts payables (BoP)": working_cap["acc_payables_bop"].tolist(),
					"Costs accrued in period": (opex+lease).tolist(),
					"Payment made in period": ((-1*working_cap["costs_paid"])+(-1*working_cap["acc_payables_bop"])).tolist(),
					"Accounts payables (EoP)": working_cap["acc_payables_eop"].tolist(),
				},
				"CF_op": {
					"EBITDA": EBITDA.tolist(),
					"Net movement in working capital": working_cap["wc_variation"].tolist(),
					"Corporate income tax": (-1*income_statement["corporate_income_tax"]).tolist(),
					"Cash flows from operating activities": cf_statement["cash_flows_operating"].tolist(),
				},
				"CF_in": {
					"Construction costs": (-1*construction_costs).tolist(),
					"Development tax": (-1*development_tax).tolist(),
					"Archaeological tax": (-1*archeological_tax).tolist(),
					"Development fee": (-1*development_fee).tolist(),
					"Capitalised IDC": (-1*senior_debt["senior_debt_idc"]).tolist(),
					"Cash flows from investing activities": cf_statement["cash_flows_investing"].tolist(),
				},
				"CF_fi": {
					"Arrangement fee (upfront)": (-1*senior_debt["upfront_fee"]).tolist(),
					"Commitment fees": (-1*senior_debt["commitment_fees"]).tolist(),
					"Senior debt drawdowns": injections["debt"].tolist(),
					"Equity injections": injections["equity"].tolist(),
					"Cash flows from financing activities": cf_statement["cash_flows_financing"].tolist(),
				},
				"WCMov": {
					"Cash flow from (to) creditors": (-1*working_cap["cashflows_from_creditors"]).tolist(),
					"Cash flow from (to) debtors": working_cap["cashflows_from_debtors"].tolist(),
					"Net movement in working capital": working_cap["wc_variation"].tolist(),
				},
				"CFADS": {
					"CFADS": CFADS.tolist(),
					"Senior debt interests": (-1*senior_debt['interests_operations']).tolist(),
					"Senior debt principal": (-1*senior_debt_repayments).tolist(),
				},
				"CFDSRA": {
					"Additions to DSRA": (-1*DSRA["dsra_additions"]).tolist(),
					"Release of excess funds": (-1*DSRA["dsra_release"]).tolist(),
				},
				"CFDistr": {
					"Cash available for distribution": cash_available_for_distribution.tolist(),
					"Transfers to distribution account": (-1*transfers_distribution_account).tolist(),
				},
				"OpAcc": {
					"Operating account balance (BoP)": operating_account_bop.tolist(),
					"Operating account balance (EoP)": operating_account_eop.tolist(),
				},
				"FP_u": {
					"Construction costs": construction_costs.tolist(),
					"Development fee": development_fee.tolist(),
					"Development tax": development_tax.tolist(),
					"Archaeological tax": archeological_tax.tolist(),
					"Interests during construction": senior_debt["senior_debt_idc"].tolist(),
					"Arrangement fee (upfront)": senior_debt["upfront_fee"].tolist(),
					"Commitment fees": senior_debt["commitment_fees"].tolist(),
					"Initial DSRA funding": DSRA_initial_funding.tolist(),
					"Total uses": total_uses.tolist(),
				},
				"FP_s": {
					"Senior debt drawdowns": injections['debt'].tolist(),
					"Share capital injections": injections['share_capital'].tolist(),
					"Shareholder loan injections": injections['SHL'].tolist(),
					"Total sources": total_sources.tolist(),
				},
				"Debt_a": {
					"Amount available (BoP)": senior_debt["senior_debt_available_bop"].tolist(),
					"Drawdowns": (-1*injections['debt']).tolist(),
					"Amount available (EoP)": senior_debt["senior_debt_available_eop"].tolist(),
				},
				"Debt_b": {
					"Opening balance": senior_debt["balance_bop"].tolist(),
					"Drawdowns": injections['debt'].tolist(),
					"Scheduled repayments": (-1*senior_debt_repayments).tolist(),
					"Closing balance": senior_debt["balance_eop"].tolist(),
				},
				"Debt_i": {
					"Arrangement fee (upfront)": senior_debt["upfront_fee"].tolist(),
					"Commitment fees": senior_debt["commitment_fees"].tolist(),
					"Debt interests": senior_debt["interests"].tolist(),
				},
				"Sizing": {
					"CFADS": CFADS_amo.tolist(),
					"Target DSCR": debt_amount_DSCR["target_DSCR"].tolist(),
					"Target DS": debt_amount_DSCR["target_DS"].tolist(),
					"Average interest rate": discount_factor["avg_interest_rate"].tolist(),
					"Discount factor": discount_factor["discount_factor"].tolist(),
					"Cumulative discount factor": discount_factor["discount_factor_cumul"].tolist(),
					"Interests during operations": senior_debt["interests_operations"].tolist(),
					"Debt repayment target": senior_debt_repayments_target.tolist(),
				},
				"DSRA": {
					"Cash available for DSRA": DSRA["cash_available_for_dsra"].tolist(),
					"DSRA target liquidity": DSRA["dsra_target"].tolist(),
					"DSRA target additions": DSRA["dsra_additions_required"].tolist(),
					"DSRA (BoP)": DSRA["dsra_bop"].tolist(),
					"Additions to DSRA": DSRA["dsra_additions"].tolist(),
					"Release of excess funds": DSRA["dsra_release"].tolist(),
					"DSRA (EoP)": DSRA["dsra_eop"].tolist(),
				},
				"Distrib_BOP": {
					"Balance brought forward": distribution_account["distribution_account_bop"].tolist(),
					"Transfers to distribution account": transfers_distribution_account.tolist(),
				},
				"Distrib_SHLi": {
					"Cash available for interests": distribution_account["cash_available_for_SHL_interests"].tolist(),
					"Shareholder loan interests paid": (-1*distribution_account["SHL_interests_paid"]).tolist(),
				},
				"Distrib_Div": {
					"Cash available for dividends": distribution_account["cash_available_for_dividends"].tolist(),
					"Dividends paid": (-1*distribution_account["dividends_paid"]).tolist(),
				},
				"Distrib_SHLp": {
					"Cash available for repayment": distribution_account["cash_available_for_SHL_repayments"].tolist(),
					"Shareholder loan repayment": (-1*distribution_account["SHL_repayments"]).tolist(),
				},
				"Distrib_SC": {
					"Cash available for reductions": distribution_account["cash_available_for_redemption"].tolist(),
					"Share capital reductions": (-1*share_capital_repayment).tolist(),
				},
				"Distrib_EOP": {
					"Distribution account balance": distribution_account_eop.tolist(),
				},
				"DevTax": {
					"Development tax": development_tax.tolist(),
				},
				"ArchTax": {
					"Archeological tax": archeological_tax.tolist(),
				},
				"PropTax": {
					"Property value": gross_property_value.tolist(),
					"Land value": gross_land_value.tolist(),
					"Property tax": tfpb.tolist(),
				},
				"CFETaxBase": {
					"Property value before deductions": gross_property_value.tolist(),
					"Standard deduction": (-1*cfe_std_deduction).tolist(),
					"Tax base": cfe_tax_base.tolist(),
					"Notional CFE due in period": cfe_due.tolist(),
					"Local tax management fee due": cfe_mgt_fee.tolist(),
					"Gross CFE due": cfe_total_due.tolist(),
				},
				"SHL": {
					"Opening balance": distribution_account['SHL_balance_bop'].tolist(),
					"Drawdowns": injections['SHL'].tolist(),
					"Capitalised interest": SHL_interests_construction.tolist(),
					"Repayment": (-1*distribution_account['SHL_repayments']).tolist(),
					"Closing balance": distribution_account['SHL_balance_eop'].tolist(),
				},
				"iSHL": {
					"Interests (construction)": SHL_interests_construction.tolist(),
					"Interests (operations)": SHL_interests_operations.tolist(),
				},
				"RE_b": {
					"Distributable profit": distribution_account['distributable_profit'].tolist(),
					"Balance brought forward": distribution_account['retained_earnings_bop'].tolist(),
					"Net income": income_statement['net_income'].tolist(),
					"Dividends declared": (-1*distribution_account['dividends_paid']).tolist(),
					"Retained earnings": distribution_account['retained_earnings_eop'].tolist(),
				},
				"Eqt": {
					"Opening balance": share_capital_bop.tolist(),
					"Contributions": injections['share_capital'].tolist(),
					"Capital reductions": (-1*share_capital_repayment).tolist(),
					"Closing balance": share_capital_eop.tolist(),
				},
				"BS_a": {
					"Property, Plant, and Equipment": PPE.tolist(),
					"Accounts receivables": working_cap['acc_receivables_eop'].tolist(),
					"Cash or cash equivalents": total_cash.tolist(),
					"Operating account balance": operating_account_eop.tolist(),
					"DSRA balance": DSRA['dsra_eop'].tolist(),
					"Distribution account balance": distribution_account_eop.tolist(),
					"Total assets": total_assets.tolist(),
				},
				"BS_l": {
					"Share capital (EoP)": share_capital_eop.tolist(),
					"Retained earnings": distribution_account['retained_earnings_eop'].tolist(),
					"Shareholder loan (EoP)": distribution_account['SHL_balance_eop'].tolist(),
					"Senior debt (EoP)": senior_debt['balance_eop'].tolist(),
					"Accounts payables (EoP)": working_cap['acc_payables_eop'].tolist(),
					"Total liabilities": total_liabilities.tolist(),
				},
				"Ratio": {
					"DSCR": DSCR_effective.tolist(),
					"LLCR": LLCR.tolist(),
					"PLCR": PLCR.tolist(),
				},

				"Audit": {
					"Balance sheet balanced": audit['balance_sheet'].tolist(),
					"Financing plan balanced": audit['financing_plan'].tolist(),
				},
				"Graphs": {
					"Cumulative total uses":total_uses_cumul.tolist(),
					"Senior debt drawdowns neg": (-1*injections['debt']).tolist(),
					"Share capital injections neg": (-1*injections['share_capital']).tolist(),
					"Shareholder loan injections neg": (-1*injections['SHL']).tolist(),
					"Dividends paid pos":distribution_account['dividends_paid'].tolist(),
					"Lease pos": lease.tolist(),
					"Operating expenses pos":(opex+tfpb).tolist(),
					"Senior debt repayments":senior_debt_repayments.tolist(),
					"EBITDA margin": EBITDA_margin.tolist(),
					"arr_construction_costs_cumul": construction_costs_cumul.tolist(),	
					"Share capital injections and repayment":(-1*injections['share_capital']+share_capital_repayment).tolist(),
					"Shareholder loan injections and repayment":(-1*injections['SHL']+distribution_account['SHL_repayments']).tolist(),
					"Share capital repayment pos":share_capital_repayment.tolist(),
					"Debt service":DS_effective.tolist(),
					"IRR curve":irr_values,
					"Gearing during financing plan":gearing_during_finplan.tolist(),
					"Debt fees":debt_fees.tolist(),
					"Local taxes":local_taxes.tolist(),

				},
			}
	
			dict_results = {
				"Equity metrics": {
					"Share capital IRR": share_capital_irr,
					"Shareholder loan IRR": SHL_irr,
					"Equity IRR": equity_irr,
					"Payback date": payback_date, 
					"Payback time": payback_time, 
				},
				"Sensi": {
					"Min DSCR": DSCR_min,
					"Avg. DSCR": DSCR_avg,
					"Min LLCR": LLCR_min,
					"Equity IRR": equity_irr,
					"Audit": check_all,
				},
				"Project IRR": {
					"Project IRR (pre-tax)": project_irr_pre_tax,
					"Project IRR (post-tax)": project_irr_post_tax,
				},
				"Debt metrics": {
					"Debt amount": debt_amount,
					"Constraint": debt_constraint,
					"Effective gearing": gearing_eff,
					"Tenor (door-to-door)": tenor_debt,
					"Average life": average_debt_life,
					"Average DSCR": DSCR_avg,
					"Debt IRR": debt_irr,
				},
				"Audit": {
					"Financing plan": check['financing_plan'],
					"Balance sheet": check['balance_sheet'],
					"Debt maturity": check['debt_maturity'],
				},
				"Valuation": {
					"Valuation1": valuation['less_1'],
					"Valuation": valuation['normal'],					
					"Valuation2": valuation['plus_1'],

				},


				}
			
			computation_to_display[key] = dict_to_display
			results_to_display[key] = dict_results
	
		dict_uses_sources = {
			"Uses": {
				"Construction costs": sum_construction_costs,
				"Development fee": optimised_devfee,
				"Debt interests & fees": sum(senior_debt_fees_constr.values()),
				"Upfront fee": senior_debt_fees_constr['upfront_fee'],
				"Commitment fees": senior_debt_fees_constr['commitment_fees'],
				"IDC": senior_debt_fees_constr['idc'],
				"Local taxes": development_tax_sum+archeological_tax_sum,
				"Development tax": development_tax_sum,
				"Archeological tax": archeological_tax_sum,
				"Initial DSRA funding": DSRA_initial_funding_max,
				"Total": total_costs,
			},
			"Sources": {
				"Equity": sum(injections['share_capital'])+sum(injections['SHL']),
				"Share capital": sum(injections['share_capital']),
				"Shareholder loan": sum(injections['SHL']),
				"Senior debt": debt_amount,
				"Total": sum(injections['share_capital'])+sum(injections['SHL'])+debt_amount,
			},
		}

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
		
		computation_displayed = computation_to_display[key]
		computation_displayed_sums = calc_sum_nested_dict(computation_displayed)
		computation_displayed_sums_per_year = calc_sum_per_year_nested_dict(computation_displayed)
		computation_displayed_end_year = extract_values_on_december_31(computation_displayed)
		computation_construction = extract_values_construction(computation_displayed)

		

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


		computation_sponsor_case_sums_per_year = calc_sum_per_year_nested_dict(computation_to_display["Sponsor Case"])

		if not inputs['financial_close_check']:
			ComputationResult.objects.filter(project=project).delete()
			SponsorCaseResult.objects.filter(project=project).delete()
			lender_case_results_save, sponsor_case_results_save = 0, 0
		else:
			lender_case_results_save_obj, _ = ComputationResult.objects.get_or_create(
				project=project,
				defaults={'financial_close_result': computation_displayed_sums_per_year}
			)
			lender_case_results_save = lender_case_results_save_obj.financial_close_result

			sponsor_case_results_save_obj, _ = SponsorCaseResult.objects.get_or_create(
				project=project,
				defaults={'sponsor_case_result': computation_sponsor_case_sums_per_year}
			)
			sponsor_case_results_save_obj.sponsor_case_result = computation_sponsor_case_sums_per_year
			sponsor_case_results_save_obj.save()
			sponsor_case_results_save = sponsor_case_results_save_obj.sponsor_case_result


			

		
		if not inputs['financial_close_check']:
			outcome = {"test":[0,0]}
		else:
			outcome = calc_outcome(lender_case_results_save,computation_displayed_sums_per_year)


		results_displayed = create_tables(dict_uses_sources, results_to_display, key, output_table_formats, outcome)



		return JsonResponse({
			"calculation_detail":inputs['calculation_detail'],

			"df":computation_displayed,
			"df_sum":computation_displayed_sums,
			"df_sum_y":computation_displayed_sums_per_year,
			"df_end_y":computation_displayed_end_year,
			"df_construction":computation_construction,

			"FC_results":lender_case_results_save,
			"sponsor_results":sponsor_case_results_save,

			"tables":results_displayed,
			"outcome":outcome,
			
			"dic_price_elec_keys":dic_price_elec_keys.tolist(),
			"data_dump_sidebar":data_dump_sidebar.tolist(),
			"tfpb_rates":tfpb_rates,
			"dev_tax_rates":dev_tax_rates,



			},safe=False, status=200)

	except Exception as e:
		traceback_info = traceback.extract_tb(e.__traceback__)
		last_trace = traceback_info[-1]
		error_data = {
			'error_type': e.__class__.__name__,
			'message': str(e),
			'line_number': last_trace.lineno
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

def calc_sum_per_year_nested_dict(computation_displayed):

	year_sum = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

	dates = computation_displayed.get("Dates", {})
	period_end_series = dates.get("Period end", [])

	if not period_end_series:
		return year_sum

	for i in range(len(period_end_series)):
		date_str = period_end_series[i]
		# Extract the year from the date string
		year = date_str.split("/")[-1]

		for key, sub_dict in computation_displayed.items():
			if key == "Dates":
				for subkey, series in sub_dict.items():
					year_sum[key][subkey][year] = year
			else: 
				for subkey, series in sub_dict.items():
					if len(series) > i:
						value = series[i]
						# Convert the value to float if it's not already
						value = float(value) if isinstance(value, (int, float)) else 0.0
						# Accumulate the values for each year
						year_sum[key][subkey][year] += value

	return dict(year_sum)

def extract_values_on_december_31(computation_displayed):
	
	values_on_december_31 = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

	dates = computation_displayed.get("Dates", {})
	period_end_series = dates.get("Period end", [])

	if not period_end_series:
		return values_on_december_31

	for i in range(len(period_end_series)):
		end_date_str = period_end_series[i]
		year = end_date_str.split("/")[-1]

		for key, sub_dict in computation_displayed.items():
			if key != "Dates":
				for subkey, series in sub_dict.items():
					if len(series) > i:
						if end_date_str.startswith("31/12") or i == len(period_end_series) - 1:
							value = series[i]
							value = float(value) if isinstance(value, (int, float)) else 0.0
							values_on_december_31[key][subkey][year] += value

	return values_on_december_31

def extract_values_construction(computation_displayed):
	
	values_in_construction = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

	flags = computation_displayed.get("FlagsC", {})
	construction_period = flags.get("Construction", [])

	for i in range(len(construction_period)):
		construction = construction_period[i]

		for key, sub_dict in computation_displayed.items():
			for subkey, series in sub_dict.items():
				if len(series) > i:
					if construction == True: 
						value = series[i]
						values_in_construction[key][subkey][i] = value
	return values_in_construction




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

	financial_close_check = request.POST.get('financial_close_check', False)

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

		'contract': post_data['contract'],

		'rotor_diameter': float(post_data['rotor_diameter']),

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

		'financial_close_check': financial_close_check,

		'valuation_df': float(post_data['discount_factor_valuation'])/100,

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



def calc_contract_price(contract_type, wind_turbine_installed, rotor_diameter,production_under_contract, production_under_contract_cumul,capacity_factor, days_series,time_series,flags):
	if contract_type == 'FiT':
		return calc_contract_E17_price(wind_turbine_installed,rotor_diameter,production_under_contract, production_under_contract_cumul)
	elif contract_type == 'CfD - E16':
		return calc_contract_E16_price(capacity_factor, days_series,time_series,flags)
	elif contract_type == 'CfD - E17':
		return calc_contract_E17_price(wind_turbine_installed,rotor_diameter,production_under_contract, production_under_contract_cumul)
	elif contract_type == 'CfD - AO':
		return calc_contract_E17_price(wind_turbine_installed,rotor_diameter,production_under_contract, production_under_contract_cumul)
	elif contract_type == 'Corporate PPA':
		return calc_contract_E17_price(wind_turbine_installed,rotor_diameter,production_under_contract, production_under_contract_cumul)
	else:
		raise ValueError("Invalid contract type")


def calc_contract_E17_price(wind_turbine_installed,rotor_diameter,production_under_contract, production_under_contract_cumul):

	# Constants for price calculation
	coefficient_KI = 13/(rotor_diameter/110)
	annual_production_ceiling = 1/20*coefficient_KI*math.pi*(rotor_diameter/2)**2*wind_turbine_installed

	# Rotor diameter price adjustment thresholds
	lower_rotor_diameter = 80
	upper_rotor_diameter = 100
	before_ceiling_lower_price = 74
	before_ceiling_upper_price = 72
	
	# Calculate price before reaching the ceiling
	before_ceiling_price = before_ceiling_lower_price + ((before_ceiling_upper_price - before_ceiling_lower_price) / (upper_rotor_diameter - lower_rotor_diameter)) * (rotor_diameter - lower_rotor_diameter)
	
	# Fixed price after exceeding the ceiling
	after_ceiling_price = 40

	# Determine production above the annual limit
	production_above_ceiling = np.maximum(production_under_contract_cumul-annual_production_ceiling,0)

	# Calculate contract price based on whether production is above or below the ceiling
	contract_E17_price = np.where(production_under_contract > 0, (production_above_ceiling * after_ceiling_price + (production_under_contract - production_above_ceiling) * before_ceiling_price) / production_under_contract, 0)
	
	return contract_E17_price


def calc_contract_E16_price(capacity_factor, days_series, time_series,flags):

	avg_equiv_operating_hours_per_year_lower = 2400
	avg_equiv_operating_hours_per_year_mid = 2800
	avg_equiv_operating_hours_per_year_upper = 3600

	TDCC_index_factor = 0.9875

	price_lower = 82
	price_mid = 68
	price_upper = 28

	equiv_operating_hours = sum(capacity_factor*days_series['contracted']*24)/sum(time_series['pct_in_contract_period'])
	
	contract_E16_price = interpolate_E16(equiv_operating_hours)*flags['contract']

	return contract_E16_price

def interpolate_E16(x):

	points = np.array([[2400, 80.98], [2800, 67.15], [3600, 27.65]])
	# If x is below the lowest x value in the points, return the corresponding y value
	if x <= points[0][0]:
		return points[0][1]
	# If x is above the highest x value in the points, return the corresponding y value
	elif x >= points[-1][0]:
		return points[-1][1]
	# Otherwise, interpolate between the appropriate points
	else:
		for i in range(len(points) - 1):
			if points[i][0] <= x <= points[i + 1][0]:
				x1, y1 = points[i]
				x2, y2 = points[i + 1]
				# Linear interpolation formula
				y = y1 + (y2 - y1) * (x - x1) / (x2 - x1)
				return y




def calc_production_cumul(production, start_calendar_year):

	cumulative_production = np.zeros_like(production)
	for i in range(len(production)):
		if start_calendar_year[i] == 1:
			cumulative_production[i] = production[i]
		else:
			cumulative_production[i] = cumulative_production[i - 1] + production[i]

	return cumulative_production


def calc_valuation(valuation_df, end_period, equity_cash_flows):

	end_period = pd.to_datetime(end_period)
	current_date = pd.Timestamp(datetime.datetime.now().date())
	time_since_today = end_period.apply(lambda date: (current_date - date).days)
	time_since_today = time_since_today.clip(lower=0)

	discount_factor = valuation_df
	discount_factor_less_1 = valuation_df-0.01
	discount_factor_plus_1 = valuation_df+0.01

	discount_factor_vector = np.where(time_since_today != 0, (1 / (1 + discount_factor)**(time_since_today/365)), 1)
	discount_factor_less_1_vector = np.where(time_since_today != 0, (1 / (1 + discount_factor_less_1)**(time_since_today/365)), 1)
	discount_factor_plus_1_vector = np.where(time_since_today != 0, (1 / (1 + discount_factor_plus_1)**(time_since_today/365)), 1)


	valuation = np.sum(equity_cash_flows*discount_factor_vector)
	valuation_less_1 = np.sum(equity_cash_flows*discount_factor_less_1_vector)
	valuation_plus_1 = np.sum(equity_cash_flows*discount_factor_plus_1_vector)


	valuation_results = {
		'normal': {
			'discount_factor': discount_factor,
			'valuation': valuation
		},
		'less_1': {
			'discount_factor': discount_factor_less_1,
			'valuation': valuation_less_1
		},
		'plus_1': {
			'discount_factor': discount_factor_plus_1,
			'valuation': valuation_plus_1
		},
	}

	return valuation_results

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





def get_elec_prices(request, construction_end, liquidation_date, dict_scenario, key):
	dic_price_elec = create_price_elec_dict(request, construction_end, liquidation_date, dict_scenario, key)
	dic_price_elec_keys = np.array(list(dic_price_elec.keys()))
	return dic_price_elec, dic_price_elec_keys


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
		degradation_factor = 1*flags['operations']
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



def import_sofr(request):

	sofr = create_SOFRForwardCurve(request)

	return sofr

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





def calc_capacity_factor(production,installed_capacity,days_operations):

	capacity_factor = np.where(days_operations>0,production/((installed_capacity*days_operations*24)/1000),0)

	return capacity_factor





def determine_debt_constraint(debt_amount,debt_amount_gearing):
	if debt_amount>debt_amount_gearing:
		constraint = "Gearing"
	else: 
		constraint = "DSCR"
	return constraint





def calc_outcome(lender_case_results_save,computation_displayed_sums_per_year):
	

	total_uses_values_initial = lender_case_results_save['FP_u']['Total uses'].values()
	total_uses_integers_initial = [int(value) for value in total_uses_values_initial]
	sum_construction_costs_fc = sum(total_uses_integers_initial)

	total_uses_values_now = computation_displayed_sums_per_year['FP_u']['Total uses'].values()
	total_uses_integers_now = [int(value) for value in total_uses_values_now]
	sum_construction_costs_now = sum(total_uses_integers_now)


	diff_sum = sum_construction_costs_now-sum_construction_costs_fc
	diff_sum_pct = diff_sum/sum_construction_costs_fc*100
	
	outcome = {
	"Total Uses": [sum_construction_costs_fc, sum_construction_costs_now, diff_sum, diff_sum_pct],
	"Total Sources": [sum_construction_costs_fc, sum_construction_costs_now, diff_sum, diff_sum_pct],

	}	

	return outcome




def create_tables(dict_uses_sources, results_to_display, key, output_table_formats,outcome):
	table_dict = {
	"Uses": dict_uses_sources["Uses"],
	"Sources": dict_uses_sources["Sources"],
	"Project IRR": results_to_display[key]["Project IRR"],
	"Equity metrics": results_to_display[key]["Equity metrics"],
	"Debt metrics": results_to_display[key]["Debt metrics"],
	"Audit": results_to_display[key]["Audit"],
	"Sensi": results_to_display,
	"Valuation": results_to_display[key]["Valuation"],
	"Outcome": outcome,

	}

	tables = {}
	for i, argument in table_dict.items():
		if i == "Sensi":
			tables[i] = create_table_sensi(argument)
		elif i == "Valuation":
			tables[i] = create_table_val(argument)
		elif i == "Outcome":
			tables[i] = create_table_outcome(argument)
		else:
			tables[i] = create_table(argument, output_table_formats)
	return tables






def create_table_outcome(results):
	metrics = [("Metric", "{:.0f}"),("", None),("Initial", "{:.0f}"), ("Current", "{:.0f}"), 
	("Diff.", "{:.0f}"), ("Variation", "{:.1%}"),]  # Specific format only for "Audit"

	table_sensi = {"": [metric[0] for metric in metrics]}
	table_sensi["Unit"] = ["kEUR","kEUR","kEUR","%"]

	# Initialize an empty list to hold all rows
	all_rows = []

	for scenario, data in results.items():
		scenario_data = []
		for j, value in enumerate(data):
			format_string = metrics[j][1]
			if format_string:  # Apply formatting if specified
				formatted_value = format_string.format(value)
			else:
				formatted_value = value  # No formatting
			scenario_data.append(formatted_value)

		all_rows.append((scenario, scenario_data))

	# Add the processed rows to the table_sensi dictionary
	for scenario, data in all_rows:
		table_sensi[scenario] = data

	return table_sensi



def create_table_sensi(results):
	metrics = [("Min DSCR", "{:.2f}x"), ("Avg. DSCR", "{:.2f}x"), 
	("Min LLCR", "{:.2f}x"), ("Equity IRR", "{:.2%}"), 
	("Audit", None)]  # Specific format only for "Audit"

	table_sensi = {"": [metric[0] for metric in metrics]}

	# Initialize an empty list to hold all rows including the blank one
	all_rows = []

	for scenario, data in results.items():
		sensi = data.get('Sensi')
		scenario_data = []
		for j, value in enumerate(sensi.values()):
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

	# Add the processed rows to the table_sensi dictionary
	for scenario, data in all_rows:
		table_sensi[scenario] = data

	return table_sensi



def create_table_val(valuation_results):
	table_val = {}

	discount_factors = []
	valuations = []

	for scenario, values in valuation_results.items():
		discount_factors.append('{:.1f}%'.format(values['discount_factor'] * 100))
		valuations.append(int(values['valuation']))

	table_val['Discount factor'] = discount_factors
	table_val['Valuation'] = valuations

	return table_val


def create_table(results, specific_formats=None):
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
			# Apply the formatting to non-string data
			formatted_val = fmt.format(data)

		table[metric] = {0: formatted_val}

	return table

output_table_formats = {
"Effective gearing": "{:.2%}",
"Average DSCR": "{:.2f}x",
"Debt IRR": "{:.2%}",
"Share capital IRR": "{:.2%}",
"Shareholder loan IRR": "{:.2%}",
"Equity IRR": "{:.2%}",
"Project IRR (pre-tax)": "{:.2%}",
"Project IRR (post-tax)": "{:.2%}",
"Financing plan": None,
"Balance sheet	": None,
"Maturity": None,
}

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
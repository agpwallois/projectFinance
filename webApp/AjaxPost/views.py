from django.http import JsonResponse
from django.http.response import HttpResponse

from django.views.generic import ListView

from django.shortcuts import render, redirect
from .forms import ProjectForm
from .models import Project

import calendar
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import dateutil.parser
from datetime import date
from dateutil import parser
import math
from dateutil.parser import ParserError
import time

import pandas as pd
import numpy as np
import numpy_financial as npf
from django.core import serializers
import json
import scipy.optimize

from pyxirr import xirr

class ProjectView(ListView):
	model = Project
	template_name = 'project_list.html'
	context_object_name = "projects"

def Viewdata(request):
	return render(request, 'project_view.html')

def test(request):
	
	Debti = 100
	Debt = 40
	interest = 0

	while Debti!=Debt:
		Debti = Debt
		EBITDA = 250
		interest = Debti * 0.1
		CFADS = EBITDA
		DS = EBITDA/1.3
		Debt = DS * 1/(1+interest/Debt)




	context={
		'Debt': Debt,
		'interest': interest,
		'Debti': Debti,

		}
	return render(request, "test.html", context)

def project_view(request,id):

	project_form = ProjectForm()
	project = Project.objects.get(id=id)

	if request.method == "POST":

		project_form = ProjectForm(request.POST, instance=project)

		if project_form.is_valid():
			project_form.save()

			""" Timeline """

			construction_start = import_construction_start(request)
			construction_end = import_construction_end(request)

			COD = calculate_COD(construction_end)
			end_of_operations = calculate_end_of_operations(request,construction_end)
			liquidation = calculate_liquidation_date(request,end_of_operations)

			debt_maturity = calculate_debt_maturity(request, construction_start)

			""" Capacity and Production inputs """
		
			inp_seasonality = import_seasonality(request)

			""" Construction costs inputs """

			arr_construction_costs = import_construction_costs(request,construction_start,construction_end)

			""" Offtake contract and Electricity price inputs """

			inp_price_merchant_index_rate_start_date = request.POST['price_elec_indexation_start_date']
			date_price_elec_index_start = datetime.datetime.strptime(inp_price_merchant_index_rate_start_date, "%Y-%m-%d").date()
		
			""" Electricity price inputs """
			dic_price_elec = create_price_elec_dict(request, construction_end,liquidation)
			dic_price_elec_keys = np.array(list(dic_price_elec.keys()))

			""" Operating costs """

			inp_opex_index_start_date = request.POST['opex_indexation_start_date']
			date_opex_index_start = datetime.datetime.strptime(inp_opex_index_start_date, "%Y-%m-%d").date()

			""" Senior debt """


			start_contract = request.POST['start_contract']
			end_contract = request.POST['end_contract']

			contract_index_start_date = request.POST['contract_indexation_start_date']
			date_contract_index_start = datetime.datetime.strptime(contract_index_start_date, "%Y-%m-%d").date()
		


			# INPUT IMPORT #

			inp_income_tax_rate = float(request.POST['corporate_income_tax'])/100
			inp_debt_gearing_max = float(request.POST['debt_gearing_max'])/100
			inp_upfront_fee = float(request.POST['debt_upfront_fee'])/100
			inp_commitment_fee = float(request.POST['debt_commitment_fee'])/100
			inp_injection = int(request.POST['injection_choice'])
			inp_subgearing=float(request.POST['subgearing'])/100
			inp_target_DSCR = float(request.POST['debt_target_DSCR'])
			inp_all_in_interest = np.array([
				float(request.POST['debt_margin']),
				float(request.POST['debt_swap_rate']),
				float(request.POST['debt_swap_margin']),
				float(request.POST['debt_reference_rate_buffer']),
				])
			inp_debt_interest_rate = np.sum(inp_all_in_interest)/100			
			inp_length_operations = int(request.POST['operating_life'])
			inp_SHL_margin_rate = float(request.POST['SHL_margin'])/100
			inp_devfee_paid_FC = float(request.POST['devfee_paid_FC'])
			inp_devfee_paid_COD = float(request.POST['devfee_paid_COD'])
			inp_price_contract = float(request.POST['contract_price'])
			inp_index_rate_merchant = float(request.POST['price_elec_indexation'])/100
			inp_index_rate_contract = float(request.POST['contract_indexation'])/100
			inp_index_rate_opex = float(request.POST['opex_indexation'])/100
			inp_payment_delay_rev=int(request.POST['payment_delay_revenues'])
			inp_payment_delay_costs=int(request.POST['payment_delay_costs'])
			inp_opex = float(request.POST['opex'])
			
			periodicity = int(request.POST['periodicity'])

			inp_dsra = 6 if int(request.POST['DSRA_choice']) == 1 else 12
			inp_cash_min = int(request.POST['cash_min'])

			start_construction = request.POST['start_construction']
			construction_end = request.POST['end_construction']

			calculation_detail = int(request.POST['calculation_detail'])

			""" Arrays instanciation """

			df = pd.DataFrame()

			""" Create date series """

			start_time = time.time()
			period_start,period_end = create_period_series(request,start_construction,construction_end,periodicity)
			end_time = time.time()
			elapsed_time  = end_time-start_time

			arr_date_start_contract_period, arr_date_end_contract_period = create_contract_period_series(period_start,period_end,start_contract,end_contract)
			arr_date_start_contract_index_period, arr_date_end_contract_index_period = create_contract_index_series(request,period_start,period_end,start_contract,end_contract,date_contract_index_start)			
			arr_date_start_elec_index = array_time(period_start,date_price_elec_index_start,end_of_operations)
			arr_date_end_elec_index = array_time(period_end,date_price_elec_index_start,end_of_operations)
			arr_date_start_opex_index = array_time(period_start,date_opex_index_start,end_of_operations)	
			arr_date_end_opex_index = array_time(period_end,date_opex_index_start,end_of_operations)

			""" Create flag series """

			flag_operations = create_flag_operations(COD,period_start,period_end,end_of_operations)
			flag_construction = create_flag_construction(period_start,construction_end)
			flag_construction_end = create_flag_construction_end(period_end,construction_end)
			flag_construction_start = create_flag_construction_start(COD,period_start,construction_start)
			flag_liquidation = create_flag_liquidation(period_end,end_of_operations)
			flag_liquidation_end = create_flag_liquidation_end(period_end,liquidation)
			
			flag_contract = array_flag(arr_date_end_contract_period,start_contract,arr_date_start_contract_period,end_contract)
			flag_contract_indexation_period = array_flag(arr_date_end_contract_index_period,date_contract_index_start,arr_date_start_contract_index_period,end_contract)
			
			flag_elec_indexation_period = array_flag(arr_date_end_elec_index,date_price_elec_index_start,arr_date_start_elec_index,end_of_operations)
			flag_opex_indexation_period= array_flag(arr_date_end_opex_index,date_opex_index_start,arr_date_start_opex_index,end_of_operations)

			flag_debt_amo = (period_end<=pd.to_datetime(debt_maturity)).astype(int)*flag_operations

			""" Create time series """

			days_in_period = array_days(period_end,period_start,1)
			days_in_year = period_end.dt.is_leap_year*366+(1-period_end.dt.is_leap_year)*365
			years_in_period = days_in_period/days_in_year
			years_during_operations = years_in_period*flag_operations
			years_from_COD_eop = years_during_operations.cumsum()
			years_from_COD_bop = years_from_COD_eop-years_during_operations
			years_from_COD_avg = (years_from_COD_eop+years_from_COD_bop)/2
			period_end_year = period_end.dt.year

			days_in_contract = array_days(arr_date_end_contract_period,arr_date_start_contract_period,flag_contract)
			days_contract_indexation = array_days(arr_date_end_contract_index_period,arr_date_start_contract_index_period,flag_contract_indexation_period)
			pct_in_contract_period=days_in_contract/days_in_period

			days_elec_indexation = array_days(arr_date_end_elec_index,arr_date_start_elec_index,flag_elec_indexation_period)
			days_opex_indexation = array_days(arr_date_end_opex_index,arr_date_start_opex_index,flag_opex_indexation_period)

			years_from_base_date_contract = calculate_years_from_base_date(days_contract_indexation,days_in_year)
			years_from_base_date_elec = calculate_years_from_base_date(days_elec_indexation,days_in_year)
			years_from_base_date_opex = calculate_years_from_base_date(days_opex_indexation,days_in_year)


			seasonality = array_seasonality(period_start,period_end,inp_seasonality)
			capacity_before_degradation = calculate_capacity(request,flag_operations)
			degradation_factor = calculate_degradation_factor(request,years_from_COD_avg)
			capacity_after_degradation = capacity_before_degradation*degradation_factor
			production = calculate_production(request,seasonality,capacity_after_degradation)



			elec_index_indice =array_index(inp_index_rate_merchant,years_from_base_date_elec)
			contract_index_indice =array_index(inp_index_rate_contract,years_from_base_date_contract)
			opex_index_indice =array_index(inp_index_rate_opex,years_from_base_date_opex)


			electricity_prices_real = array_elec_prices(period_end_year,dic_price_elec)
			electricity_prices_indexed = electricity_prices_real*elec_index_indice

			contract_prices_real=inp_price_contract*flag_contract
			contract_prices_indexed=contract_prices_real*contract_index_indice


			contracted_revenues = production*contract_prices_indexed*pct_in_contract_period/1000
			market_revenues = production*electricity_prices_indexed*(1-pct_in_contract_period)/1000
			total_revenues = contracted_revenues+market_revenues

			
			opex = inp_opex*opex_index_indice*years_during_operations

			EBITDA = total_revenues-opex
			EBITDA_margin =np.divide(EBITDA,total_revenues,out=np.zeros_like(EBITDA), where=total_revenues>0)


			revenues_in_period_paid = (1-inp_payment_delay_rev/days_in_period)*total_revenues
			accounts_receivables_eop= total_revenues-revenues_in_period_paid
			accounts_receivables_bop = np.roll(accounts_receivables_eop, 1)

			costs_in_period_paid = (1-inp_payment_delay_costs/days_in_period)*opex
			accounts_payables_eop = opex-costs_in_period_paid
			accounts_payables_bop = np.roll(accounts_payables_eop, 1)

			cashflows_from_creditors = np.ediff1d(accounts_receivables_eop, to_begin=accounts_receivables_eop[0])
			cashflows_from_debtors =np.ediff1d(accounts_payables_eop, to_begin=accounts_payables_eop[0])
			working_cap_movement = cashflows_from_debtors-cashflows_from_creditors

			construction_costs = np.hstack([arr_construction_costs,np.zeros(flag_operations.size-arr_construction_costs.size)])*flag_construction
			construction_costs_cumul = construction_costs.cumsum()
			construction_costs_max = max(construction_costs_cumul)

			# INSTANTIATION #

			target_debt_amount = construction_costs_max*inp_debt_gearing_max
			total_costs=construction_costs_max
			optimised_devfee = 0

			senior_debt_repayments_target = np.full(period_end.size, 0)

			debt_amount_not_converged = True
			debt_sculpting_not_converged = True
			distributable_profit = np.full(period_end.size, 1)

			total_uses=construction_costs

			SHL_balance_bop = np.full(period_end.size, 1)
			SHL_interests_construction= np.full(period_end.size, 0)
			SHL_interests_operations= np.full(period_end.size, 0)
			dsra_bop= np.full(period_end.size, 0)
			dsra_initial_funding= np.full(period_end.size, 0)
			dsra_initial_funding_max=0
			size = period_end.size

			# DEBT LOOP #

			"""while debt_amount_not_converged or debt_sculpting_not_converged:"""
			for i in range(30):
				debt_amount = target_debt_amount
				equity_amount= total_costs-debt_amount
				senior_debt_repayments = senior_debt_repayments_target

				gearing_eff = (debt_amount/total_costs)

				total_uses_cumul = total_uses.cumsum()

				if inp_injection == 1:
					equity_injections_cumul = np.clip(total_uses_cumul, None, equity_amount) 
					equity_injections = np.ediff1d(equity_injections_cumul, to_begin=equity_injections_cumul[0])
					share_capital_injections = equity_injections*(1-inp_subgearing)
					SHL_injections = equity_injections*inp_subgearing		
					senior_debt_drawdowns = total_uses - equity_injections
					senior_debt_drawdowns_cumul = senior_debt_drawdowns.cumsum()
				elif inp_injection == 2:
					senior_debt_drawdowns_cumul = np.clip(total_uses_cumul * gearing_eff, None, debt_amount)
					senior_debt_drawdowns = np.ediff1d(senior_debt_drawdowns_cumul, to_begin=senior_debt_drawdowns_cumul[0])
					equity_injections = total_uses - senior_debt_drawdowns
					share_capital_injections = equity_injections*(1-inp_subgearing)
					SHL_injections = equity_injections*inp_subgearing

				# Calculate senior debt balance
				senior_debt_balance_eop=(senior_debt_drawdowns-senior_debt_repayments).cumsum()
				senior_debt_balance_bop=senior_debt_balance_eop+senior_debt_repayments-senior_debt_drawdowns

				# Calculate senior debt interests
				senior_debt_interests=senior_debt_balance_bop*inp_debt_interest_rate*days_in_period/360
				senior_debt_interests_operations=senior_debt_interests*flag_debt_amo
				senior_debt_interests_construction=senior_debt_interests*flag_construction

				# Calculate upfront fee 
				upfront_fee=flag_construction_start*debt_amount*inp_upfront_fee

				# Calculate debt available
				senior_debt_available_eop=(debt_amount-senior_debt_balance_bop)*flag_construction
				senior_debt_available_bop=senior_debt_available_eop+senior_debt_drawdowns

				# Calculate capitalised fees 
				commitment_fees=senior_debt_available_bop*inp_commitment_fee*days_in_period/360
				capitalised_fees_idc_cumul = (senior_debt_interests_construction+upfront_fee+commitment_fees+SHL_interests_construction).cumsum()
				capitalised_fees_idc_max = max(capitalised_fees_idc_cumul)
				
				# Calculate depreciation
				depreciation = (construction_costs_max+capitalised_fees_idc_max+optimised_devfee)*years_during_operations/inp_length_operations

				# Calculate total uses	
				total_uses=construction_costs+senior_debt_interests_construction+optimised_devfee+upfront_fee+commitment_fees+dsra_initial_funding

				# Calculate EBIT, EBT, and net income
				EBIT=EBITDA-depreciation
				EBT=EBIT-senior_debt_interests_operations-SHL_interests_operations
				corporate_income_tax=np.clip(inp_income_tax_rate*EBT, 0, None)
				net_income=EBT-corporate_income_tax

				# Calculate cash flows
				cash_flows_operating=EBITDA+working_cap_movement-corporate_income_tax
				cash_flows_investing=-(construction_costs+senior_debt_interests_construction+optimised_devfee)
				cash_flows_financing=upfront_fee+commitment_fees+senior_debt_drawdowns+equity_injections

				CFADS=cash_flows_operating

				CFADS_amo = CFADS*flag_debt_amo
				target_DSCR=inp_target_DSCR*flag_debt_amo
				target_DS=CFADS_amo/inp_target_DSCR

				avg_interest_rate=np.divide(senior_debt_interests_operations,senior_debt_balance_bop,out=np.zeros_like(senior_debt_interests_operations), where=senior_debt_balance_bop!=0)/days_in_period*360
				discount_factor=(1/(1+(avg_interest_rate*days_in_period/360)))*flag_debt_amo+flag_construction
				discount_factor_cumul=discount_factor.cumprod()

				debt_amount_DSCR = npv(target_DS,discount_factor_cumul)

				"""clarifier"""

				interests_during_construction = sum(senior_debt_interests_construction)
				upfront_fee_max = np.max(upfront_fee)
				commitment_fee= sum(commitment_fees)

				optimised_devfee = optimise_devfee(request,debt_amount_DSCR,construction_costs_max,interests_during_construction)
				total_costs = construction_costs_max+interests_during_construction+optimised_devfee+upfront_fee_max+commitment_fee+dsra_initial_funding_max

				debt_amount_gearing = total_costs*inp_debt_gearing_max
				target_debt_amount = min(debt_amount_DSCR,debt_amount_gearing)

				development_fee = inp_devfee_paid_FC * optimised_devfee * flag_construction_start + inp_devfee_paid_COD * optimised_devfee * flag_construction_end
				development_fee_cumul = development_fee.cumsum()

				cumul_debt_drawn  = max(senior_debt_drawdowns_cumul)
				npv_CFADS = npv(CFADS_amo,discount_factor_cumul)
			
				DSCR_sculpting = npv_CFADS / cumul_debt_drawn if cumul_debt_drawn > 0 else 1
				
				senior_debt_repayments_target = np.minimum(senior_debt_balance_bop,CFADS_amo/DSCR_sculpting - senior_debt_interests_operations)

				DS_effective=senior_debt_repayments+senior_debt_interests_operations
				DSCR_effective = np.divide(CFADS_amo,DS_effective,out=np.zeros_like(CFADS_amo), where=DS_effective!=0)

				# Calculate DSRA
				cash_available_for_dsra = np.maximum(CFADS - DS_effective,0)
				dsra_target = calculate_dsra_target(inp_dsra,periodicity,DS_effective)*flag_debt_amo
				dsra_initial_funding = calculate_dsra_funding(dsra_target)*flag_construction_end
				dsra_additions_available = np.minimum(cash_available_for_dsra,dsra_target)
				dsra_target = dsra_target+dsra_initial_funding
				dsra_eop=np.clip((dsra_initial_funding+dsra_additions_available).cumsum(),0,dsra_target)
				dsra_eop_mov=np.ediff1d(dsra_eop, to_begin=dsra_eop[0])
				dsra_additions=np.maximum(dsra_eop_mov,0)
				dsra_release = np.minimum(dsra_eop_mov,0)
				dsra_bop=np.roll(dsra_eop, 1)
				dsra_mov = (dsra_eop-dsra_bop)*flag_debt_amo
				dsra_initial_funding_max = max(dsra_initial_funding)

				

				cash_available_for_distribution = (CFADS - senior_debt_interests_operations - senior_debt_repayments - dsra_mov - inp_cash_min*flag_operations)
				transfers_distribution_account = cash_available_for_distribution

				operating_account_eop=CFADS - senior_debt_interests_operations - senior_debt_repayments - dsra_mov-transfers_distribution_account
				operating_account_bop=np.roll(operating_account_eop, 1)

				start_time = time.time()


				SHL_balance_bop=np.array(SHL_balance_bop)
				days_in_period=np.array(days_in_period)
				flag_operations=np.array(flag_operations)
				flag_construction=np.array(flag_construction)
				transfers_distribution_account=np.array(transfers_distribution_account)
				distributable_profit=np.array(distributable_profit)
				SHL_injections=np.array(SHL_injections)
				net_income=np.array(net_income)


	
				distribution_account = calculate_distribution_account(SHL_balance_bop, inp_SHL_margin_rate, days_in_period, flag_operations, flag_construction,
						  transfers_distribution_account, distributable_profit, SHL_injections, net_income)


				SHL_interests_operations = distribution_account['SHL_interests_operations']
				SHL_interests_construction = distribution_account['SHL_interests_construction']
				cash_available_for_SHL_interests = distribution_account['cash_available_for_SHL_interests']
				SHL_interests_paid = distribution_account['SHL_interests_paid']
				cash_available_for_dividends = distribution_account['cash_available_for_dividends']
				cash_available_for_SHL_repayments = distribution_account['cash_available_for_SHL_repayments']
				dividends_paid = distribution_account['dividends_paid']
				SHL_repayments = distribution_account['SHL_repayments']
				cash_available_for_redemption = distribution_account['cash_available_for_redemption']

				distribution_account_eop = distribution_account['distribution_account_eop']
				distribution_account_bop = distribution_account['distribution_account_bop']
				SHL_balance_eop = distribution_account['SHL_balance_eop']
				SHL_balance_bop = distribution_account['SHL_balance_bop']
				retained_earnings_eop = distribution_account['retained_earnings_eop']
				retained_earnings_bop = distribution_account['retained_earnings_bop']
				distributable_profit = distribution_account['distributable_profit']

				
				end_time = time.time()
				execution_time_distribution_account = end_time - start_time

				""" Convergence tests """

				debt_amount_not_converged = abs(debt_amount-target_debt_amount)>0.1
				difference = senior_debt_repayments_target-senior_debt_repayments
				debt_sculpting_not_converged = np.where(difference == 0, True, False)
				debt_sculpting_not_converged = np.any(np.logical_not(debt_sculpting_not_converged))

			share_capital_repayment=distribution_account_bop*flag_liquidation_end
			distribution_account_eop=distribution_account_eop-share_capital_repayment

			share_capital_eop = (share_capital_injections - share_capital_repayment).cumsum()
			share_capital_bop = share_capital_eop - (share_capital_injections-share_capital_repayment)

			share_capital_cash_flows=-equity_injections+dividends_paid+share_capital_repayment
			SHL_cash_flows= -SHL_injections+SHL_interests_operations+SHL_repayments
			equity_cash_flows = share_capital_cash_flows+SHL_cash_flows
			equity_cash_flows_cumul = equity_cash_flows.cumsum()
			debt_cash_flows = -senior_debt_drawdowns+senior_debt_repayments+senior_debt_interests+upfront_fee+commitment_fees

			total_cash = operating_account_eop+dsra_eop+distribution_account_eop

			""" Balance sheet """		

			PPE = construction_costs_cumul+capitalised_fees_idc_cumul+development_fee_cumul-depreciation.cumsum()
			total_assets = PPE+accounts_receivables_eop+operating_account_eop+distribution_account_eop+dsra_eop

			total_liabilities = share_capital_eop+SHL_balance_eop+senior_debt_balance_eop+retained_earnings_eop+accounts_payables_eop

			total_sources = senior_debt_drawdowns+equity_injections

			audit_financing_plan = total_uses-total_sources
			audit_balance_sheet = total_assets-total_liabilities

			share_capital_injections_repayments = -share_capital_injections+share_capital_repayment
			SHL_injections_repayments=-SHL_injections+SHL_repayments
			dividends_and_share_capital_repayment = dividends_paid+share_capital_repayment

			irr_values = create_IRR_curve(equity_cash_flows,period_end)

			""" Debt ratios """

			avg_i = avg_interest_rate[avg_interest_rate>0].mean()

			LLCR_discounted_CFADS=compute_npv(CFADS_amo,avg_i,period_end)
			PLCR_discounted_CFADS=compute_npv(CFADS,avg_i,period_end)

			LLCR = np.divide(LLCR_discounted_CFADS,senior_debt_balance_eop,out=np.zeros_like(LLCR_discounted_CFADS), where=senior_debt_balance_eop>0.01)
			PLCR = np.divide(PLCR_discounted_CFADS,senior_debt_balance_eop,out=np.zeros_like(PLCR_discounted_CFADS), where=senior_debt_balance_eop>0.01)
			
			""" Outputs """

			test_numpy = is_numpy_array(period_start)
			test_panda= is_pandas_array(period_start)

			debt_constraint = determine_debt_constraint(debt_amount_DSCR,debt_amount_gearing)
			table_uses = create_table_uses(construction_costs_max,optimised_devfee,interests_during_construction,upfront_fee_max,commitment_fee,total_costs,dsra_initial_funding_max)
			table_sources = create_table_sources(share_capital_injections,SHL_injections,debt_amount)
			table_debt = create_table_debt(DSCR_effective,debt_amount,debt_constraint,total_costs,flag_debt_amo,period_end,debt_cash_flows)
			table_projectIRR = create_table_projectIRR(total_uses,EBITDA,corporate_income_tax,period_end)
			table_equity = create_table_equity(construction_start,period_end,share_capital_cash_flows,SHL_cash_flows,equity_cash_flows,equity_cash_flows_cumul)
			table_financing_terms = create_table_financing_terms(request,construction_start,debt_amount,period_end,senior_debt_balance_eop,share_capital_eop,SHL_balance_eop,years_in_period,senior_debt_balance_bop,SHL_balance_bop,SHL_injections)
			table_audit = create_table_audit(audit_financing_plan,audit_balance_sheet)

			gearing_during_finplan = senior_debt_drawdowns.cumsum()/(equity_injections.cumsum()+senior_debt_drawdowns.cumsum())

			COD_formatted,end_of_operations_formatted,liquidation_formatted,debt_maturity_formatted = format_dates(COD,end_of_operations,liquidation,debt_maturity)

			sum_seasonality = np.sum(seasonality)
			sum_seasonality = (sum_seasonality / np.sum(seasonality)) * 100
			sum_construction_costs = np.sum(arr_construction_costs)


			data_detailed = {
				'AAA Ttest': LLCR_discounted_CFADS,
				

				'Date Period start': pd.to_datetime(period_start).dt.strftime('%d/%m/%Y'),
				'Date Period end': pd.to_datetime(period_end).dt.strftime('%d/%m/%Y'),

				'FlagCons Construction': flag_construction,
				'FlagCons Construction start': flag_construction_start,
				'FlagCons Construction end': flag_construction_end,
				
				'FlagMod Year': period_end_year,
				'FlagMod Days in period': days_in_period,
				'FlagMod Days in year': days_in_year,
				'FlagMod Years in period': years_in_period,

				'FlagOftk_t Contract period': flag_contract,
				'FlagOftk_t Contract start date': pd.to_datetime(arr_date_start_contract_period).dt.strftime('%d/%m/%Y'),
				'FlagOftk_t Contract end date': pd.to_datetime(arr_date_end_contract_period).dt.strftime('%d/%m/%Y'),
				'FlagOftk_t Days in contract period': days_in_contract,
				'FlagOftk_t Percentage in contract period': pct_in_contract_period,

				'FlagOftk_i Indexation period': flag_contract_indexation_period,
				'FlagOftk_i Indexation start date': pd.to_datetime(arr_date_start_contract_index_period).dt.strftime('%d/%m/%Y'),
				'FlagOftk_i Indexation end date': pd.to_datetime(arr_date_end_contract_index_period).dt.strftime('%d/%m/%Y'),
				'FlagOftk_i Indexation (days)': days_contract_indexation,
				'FlagOftk_i Indexation': contract_index_indice,

				'FlagOp Operations': flag_operations,
				'FlagOp Years from COD (BoP)': years_from_COD_bop,
				'FlagOp Years from COD (EoP)': years_from_COD_eop,
				'FlagOp Years from COD (avg.)': years_from_COD_avg,
				'FlagOp Years during operations': years_during_operations,
				'FlagOp Liquidation': flag_liquidation,
				'FlagOp Liquidation end': flag_liquidation_end,
				'FlagOp Seasonality':seasonality,

				'FlagFin Amortisation period': flag_debt_amo,

				
				'IS Contracted revenues': contracted_revenues,
				'IS Uncontracted electricity revenues': market_revenues,
				'IS Total revenues': total_revenues,
				'IS Operating expenses': -opex,
				'IS EBITDA':EBITDA,
				'IS Depreciation':-depreciation,
				'IS EBIT':EBIT,
				'IS Senior debt interests':-senior_debt_interests_operations,
				'IS Shareholder loan interests':-SHL_interests_operations,
				'IS EBT':EBT, 
				'IS Corporate income tax':-corporate_income_tax,
				'IS Net income':net_income,

			
				'Mkt_i Indexation': elec_index_indice,
				'Mkt_i Indexation (days)': days_elec_indexation,
				'Mkt_i Indexation end date': pd.to_datetime(arr_date_end_elec_index).dt.strftime('%d/%m/%Y'),
				'Mkt_i Indexation period': flag_elec_indexation_period,
				'Mkt_i Indexation start date': pd.to_datetime(arr_date_start_elec_index).dt.strftime('%d/%m/%Y'),
				
				'Opex Indexation': opex_index_indice,
				'Opex Indexation (days)': days_opex_indexation,
				'Opex Indexation end date': pd.to_datetime(arr_date_end_opex_index).dt.strftime('%d/%m/%Y'),
				'Opex Indexation period': flag_opex_indexation_period,
				'Opex Indexation start date': pd.to_datetime(arr_date_start_opex_index).dt.strftime('%d/%m/%Y'),
				'Opex Years from indexation start date': years_from_base_date_opex,
				
				'Price Contract price (unindexed)': contract_prices_real,
				'Price Contract price (indexed)': contract_prices_indexed,
				'Price Electricity market price (unindexed)': electricity_prices_real,
				'Price Electricity market price (indexed)': electricity_prices_indexed,
				
				'Prod Capacity after degradation': capacity_after_degradation,
				'Prod Capacity before degradation': capacity_before_degradation,
				'Prod Capacity degradation factor': degradation_factor,
				'Prod Production': production,
				
				'EBITDA margin': EBITDA_margin,
				'arr_construction_costs_cumul': construction_costs_cumul,							



				'WCRec Accounts receivables (BoP)':accounts_receivables_bop,
				'WCRec Revenue accrued in period':total_revenues,
				'WCRec Payment received in period':-revenues_in_period_paid-accounts_receivables_bop,
				'WCRec Accounts receivables (EoP)':accounts_receivables_eop,

				'WCPay Accounts payables (BoP)':accounts_payables_bop,
				'WCPay Costs accrued in period':opex,
				'WCPay Payment made in period':-costs_in_period_paid-accounts_payables_bop,
				'WCPay Accounts payables (EoP)':accounts_payables_eop,

				'WCMov Cash flow from (to) creditors':-cashflows_from_creditors,
				'WCMov Cash flow from (to) debtors':cashflows_from_debtors,
				'WCMov Net movement in working capital':working_cap_movement,
				
				'CF_op EBITDA':EBITDA,
				'CF_op Net movement in working capital':working_cap_movement,
				'CF_op Corporate income tax':-corporate_income_tax,
				'CF_op Cash flows from operating activities':cash_flows_operating,
				
				'CF_in Construction costs':-construction_costs,
				'CF_in Development fee':-optimised_devfee,
				'CF_in Capitalised IDC':-senior_debt_interests_construction,
				'CF_in Cash flows from investing activities':cash_flows_investing,
			
				'CF_fi Arrangement fee (upfront)':-upfront_fee,
				'CF_fi Commitment fees':-commitment_fees,				
				'CF_fi Senior debt drawdowns':senior_debt_drawdowns,
				'CF_fi Equity injections':equity_injections,
				'CF_fi Cash flows from financing activities':cash_flows_financing,
				
				'CFADS CFADS':CFADS,
				'CFADS Senior debt interests':-senior_debt_interests_operations,
				'CFADS Senior debt principal':-senior_debt_repayments,

				'CFDSRA Additions to DSRA':-dsra_additions,
				'CFDSRA Release of excess funds':-dsra_release,

				'CFDistr Cash available for distribution':cash_available_for_distribution,
				'CFDistr Transfers to distribution account':-transfers_distribution_account,

				'OpAccB Operating account balance (BoP)':operating_account_bop,

				'OpAccE Operating account balance (EoP)':operating_account_eop,



				'FP_u Construction costs': construction_costs,
				'FP_u Development fee': development_fee,	
				'FP_u Interests during construction':senior_debt_interests_construction,
				'FP_u Arrangement fee (upfront)':upfront_fee,
				'FP_u Commitment fees':commitment_fees,
				'FP_u Initial DSRA funding':dsra_initial_funding,

				'FP_u Total uses':total_uses,

				'FP_s Senior debt drawdowns': senior_debt_drawdowns,
				'FP_s Share capital injections': share_capital_injections,
				'FP_s Shareholder loan injections': SHL_injections,
				'FP_s Total sources': total_sources,

				'Debt_a Amount available (BoP)':senior_debt_available_bop,
				'Debt_a Drawdowns':-senior_debt_drawdowns,
				'Debt_a Amount available (EoP)':senior_debt_available_eop,
			
				'Debt_b Opening balance':senior_debt_balance_bop,
				'Debt_b Drawdowns':senior_debt_drawdowns,
				'Debt_b Scheduled repayments':-senior_debt_repayments,
				'Debt_b Closing balance':senior_debt_balance_eop,
			
				'Debt_i Arrangement fee (upfront)':upfront_fee,
				'Debt_i Commitment fees':commitment_fees,
				'Debt_i Debt interests':senior_debt_interests,
				
				'Sizing CFADS':CFADS_amo,
				'Sizing Target DSCR':target_DSCR,
				'Sizing Target DS':target_DS,
				'Sizing Average interest rate':avg_interest_rate,
				'Sizing Discount factor':discount_factor,
				'Sizing Cumulative discount factor':discount_factor_cumul,
				'Sizing Interests during operations':senior_debt_interests_operations,
				'Sizing Debt repayment target':senior_debt_repayments_target,

				'DSRA Cash available for DSRA':cash_available_for_dsra,
				'DSRA DSRA target liquidity':dsra_target,
				'DSRA DSRA (BoP)':dsra_bop,
				'DSRA Additions to DSRA':dsra_additions,
				'DSRA Release of excess funds':dsra_release,
				'DSRA DSRA (EoP)':dsra_eop,


							
				'DistrBOP Balance brought forward':distribution_account_bop,
				'DistrBOP Transfers to distribution account':transfers_distribution_account,

				'DistrSHLi Cash available for interests':cash_available_for_SHL_interests,
				'DistrSHLi Shareholder loan interests paid':-SHL_interests_paid,

				'DistrDiv Cash available for dividends':cash_available_for_dividends,
				'DistrDiv Dividends paid':-dividends_paid,

				'DistrSHLp Cash available for repayment':cash_available_for_SHL_repayments,
				'DistrSHLp Shareholder loan repayment':-SHL_repayments,

				'DistrSC Cash available for reductions':cash_available_for_redemption,
				'DistrSC Share capital reductions':-share_capital_repayment,

				'DistrEOP Distribution account balance':distribution_account_eop,
				
				'SHL Opening balance':SHL_balance_bop,
				'SHL Drawdowns':SHL_injections,
				'SHL Capitalised interest':SHL_interests_construction,
				'SHL Repayment':-SHL_repayments,
				'SHL Closing balance':SHL_balance_eop,
				
				'iSHL Interests (construction)':SHL_interests_construction,
				'iSHL Interests (operations)':SHL_interests_operations,

				'RE_b Distributable profit':distributable_profit,			
				'RE_b Balance brought forward':retained_earnings_bop,
				'RE_b Net income': net_income,		
				'RE_b Dividends declared': -dividends_paid,
				'RE_b Retained earnings':retained_earnings_eop,


				'Eqt Opening balance':share_capital_bop,			
				'Eqt Contributions':share_capital_injections,
				'Eqt Capital reductions':-share_capital_repayment,
				'Eqt Closing balance':share_capital_eop,

				'BS_a Property, Plant, and Equipment': PPE,
				'BS_a Accounts receivables': accounts_receivables_eop,
				'BS_a Cash or cash equivalents': total_cash,
				'BS_a Operating account balance': operating_account_eop,
				'BS_a DSRA balance': dsra_eop,

				'BS_a Distribution account balance': distribution_account_eop,

				'BS_a Total assets': total_assets,
			
				'BS_l Share capital (EoP)': share_capital_eop,
				'BS_l Retained earnings': retained_earnings_eop,
				'BS_l Shareholder loan (EoP)': SHL_balance_eop,
				'BS_l Senior debt (EoP)': senior_debt_balance_eop,
				'BS_l Accounts payables (EoP)': accounts_payables_eop,
				'BS_l Total liabilities': total_liabilities,

				'Cumulative total uses':total_uses_cumul,
				'Senior debt drawdowns neg': -1 * senior_debt_drawdowns,
				'Share capital injections neg': -1 * share_capital_injections,
				'Shareholder loan injections neg': -1 * SHL_injections,
				'Dividends paid pos':dividends_paid,
				'Operating expenses pos':opex,
				'Senior debt repayments':senior_debt_repayments,
				'Ratio DSCR':DSCR_effective,
				'Ratio LLCR':LLCR,
				'Ratio PLCR':PLCR,

				'Share capital injections and repayment':share_capital_injections_repayments,
				'Shareholder loan injections and repayment':SHL_injections_repayments,
				'Share capital repayment pos':share_capital_repayment,
				'Debt service':DS_effective,

				'IRR curve':irr_values,

				'Gearing during financing plan':gearing_during_finplan,
				'Audit Balance sheet balanced': audit_balance_sheet,
				'Audit Financing plan balanced': audit_financing_plan,
			}

			df = pd.DataFrame(data_detailed)
			df_sum = df.apply(pd.to_numeric, errors='coerce').sum()

			final_repayment_date_debt=find_last_payment_date(period_end, senior_debt_balance_eop)
			

			data_dump_sidebar = np.array([
				COD_formatted,
				end_of_operations_formatted,
				sum_seasonality,
				sum_construction_costs,
				liquidation_formatted,
				debt_maturity_formatted,
				debt_amount_DSCR,
				debt_amount_gearing,
				target_debt_amount,
				debt_amount,
				optimised_devfee,
				DSCR_sculpting,
				final_repayment_date_debt,
				execution_time_distribution_account,
				test_numpy,
				test_panda,
				])


		

			return JsonResponse({
				"df":df.to_dict(),
				"df_sum":df_sum.to_dict(),
				"table_uses":table_uses.to_dict(),
				"table_sources":table_sources.to_dict(),
				"table_projectIRR":table_projectIRR.to_dict(),
				"table_equity":table_equity.to_dict(),
				"table_debt":table_debt.to_dict(),
				"calculation_detail":calculation_detail,
				"table_financing_terms":table_financing_terms.to_dict(),
				"table_audit":table_audit.to_dict(),
				"dic_price_elec_keys":dic_price_elec_keys.tolist(),
				"data_dump_sidebar":data_dump_sidebar.tolist(),
				},safe=False, status=200)
		else:
			
			data = {'error':project_form.errors.as_json()}
			
			return JsonResponse(data, status=400)

	else:
		project_form = ProjectForm(instance=project)

	context={
		'project_form': project_form,
		'project':project,
		}
	
	return render(request, "project_view.html", context)


"""USED"""

def create_period_series(request,start_construction,construction_end,periodicity):

	
	liquidation = int(request.POST['liquidation'])

	operating_life = int(request.POST['operating_life'])

	formatted_start_construction = datetime.datetime.strptime(start_construction, "%Y-%m-%d").date()
	formatted_construction_end = datetime.datetime.strptime(construction_end, "%Y-%m-%d").date()

	COD = formatted_construction_end + datetime.timedelta(days=1) 
	end_of_operations = formatted_construction_end + relativedelta(years=operating_life)
	start_liquidation = end_of_operations + datetime.timedelta(days=1) 
	end_liquidation = end_of_operations + relativedelta(months=liquidation)
	first_day_start_liquidation = end_of_operations + datetime.timedelta(days=1) 

	freq_start_period = str(periodicity)+"MS"
	freq_end_period = str(periodicity)+"M"

	first_day_start_construction = first_day_month(formatted_start_construction)
	first_day_start_operations = first_day_month(COD)
	first_day_start_liquidation = first_day_month(end_of_operations)
	
	last_day_construction_end = end_date_period(formatted_construction_end)
	last_day_end_operations = end_date_period(end_of_operations)
	
	#Période mensuelle pendant le plan de financement puis selon la périodicité
	start_period_construction = pd.Series(pd.date_range(first_day_start_construction,last_day_construction_end, freq='MS')).clip(lower=pd.Timestamp(formatted_start_construction))
	start_period_operations = pd.Series(pd.date_range(first_day_start_operations, last_day_end_operations,freq=freq_start_period)).clip(lower=pd.Timestamp(COD))
	start_period_liquidation = pd.Series(pd.date_range(first_day_start_liquidation, end_liquidation,freq=freq_start_period)).clip(lower=pd.Timestamp(start_liquidation))
	
	period_start = pd.concat([start_period_construction,start_period_operations,start_period_liquidation], ignore_index=True)

	first_day_start_operations_plus_freq = first_day_next_month(COD,periodicity)
	last_day_end_operations_plus_freq = first_day_next_month(end_of_operations,periodicity)
	first_day_start_liquidation_plus_freq = first_day_next_month(first_day_start_liquidation,periodicity)
	last_day_end_liquidation_plus_freq = first_day_next_month(end_liquidation,periodicity)

	#Période mensuelle pendant le plan de financement puis selon la périodicité
	end_period_construction = pd.Series(pd.date_range(first_day_start_construction,last_day_construction_end, freq='M')).clip(upper=pd.Timestamp(formatted_construction_end))
	end_period_operations = pd.Series(pd.date_range(first_day_start_operations_plus_freq, last_day_end_operations_plus_freq,freq=freq_end_period)).clip(upper=pd.Timestamp(end_of_operations))
	end_period_liquidation= pd.Series(pd.date_range(first_day_start_liquidation_plus_freq, last_day_end_liquidation_plus_freq,freq=freq_end_period)).clip(upper=pd.Timestamp(end_liquidation))
	
	period_end = pd.concat([end_period_construction,end_period_operations,end_period_liquidation], ignore_index=True)
	
	return period_start, period_end


def calculate_distribution_account(SHL_balance_bop, inp_SHL_margin_rate, days_in_period, flag_operations, flag_construction,
					 transfers_distribution_account, distributable_profit, SHL_injections, net_income):
	
	for i in range(100):
	
		SHL_interests_operations = SHL_balance_bop * inp_SHL_margin_rate * days_in_period / 360 * flag_operations
		SHL_interests_construction = SHL_balance_bop * inp_SHL_margin_rate * days_in_period / 360 * flag_construction

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


def create_price_elec_dict(request, construction_end,liquidation):
	
	choice = int(request.POST['price_elec_choice'])

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


def calculate_dsra_target(inp_dsra,periodicity,DS_effective):

	look_forward=int(inp_dsra/periodicity)	

	looking_forward_debt_service = []
	for i in range(len(DS_effective)):
		forward_debt_service = sum(DS_effective[i+1:min(i+1+look_forward, len(DS_effective))])
		looking_forward_debt_service.append(forward_debt_service)

	return looking_forward_debt_service

def calculate_dsra_funding(dsra_target):
	
	positive_sum = 0
	count = 0

	for num in dsra_target:
		if num > 0:
			positive_sum += num
			count += 1

		if count == 1:
			break

	return positive_sum


def calculate_interests(balance_bop,rate,days,flag):
	interests=balance_bop*rate*days/360*flag
	return interests

def calculate_years_from_base_date(days_of_indexation, days_in_year):
	years_from_base_date = (days_of_indexation/days_in_year).cumsum()
	return years_from_base_date		


def import_construction_start(request):
	inp_construction_start = request.POST['start_construction']
	construction_start = datetime.datetime.strptime(inp_construction_start, "%Y-%m-%d").date()

	return construction_start

def import_construction_end(request):

	inp_construction_end = request.POST['end_construction']
	construction_end = datetime.datetime.strptime(inp_construction_end, "%Y-%m-%d").date()
	
	return construction_end		

def calculate_COD(construction_end):

	COD = construction_end + datetime.timedelta(days=1) 

	return COD

def calculate_end_of_operations(request,construction_end):

	inp_life = int(request.POST['operating_life'])
	end_of_operations = construction_end + relativedelta(years=inp_life)

	return end_of_operations

def calculate_liquidation_date(request,end_of_operations):

	inp_liquidation = int(request.POST['liquidation'])
	liquidation = end_of_operations + relativedelta(months=inp_liquidation)

	return liquidation

def calculate_debt_maturity(request,construction_start):

	inp_debt_tenor = float(request.POST['debt_tenor'])
	debt_maturity = construction_start + relativedelta(months=+int(inp_debt_tenor*12)-1)
	debt_maturity = debt_maturity.replace(day = calendar.monthrange(debt_maturity.year, debt_maturity.month)[1])

	return	debt_maturity

def format_dates(COD,end_of_operations,liquidation,debt_maturity):

	COD_formatted = COD.strftime("%d/%m/%Y")
	end_of_operations_formatted = end_of_operations.strftime("%d/%m/%Y")
	liquidation_formatted = liquidation.strftime("%d/%m/%Y")
	debt_maturity_formatted = debt_maturity.strftime("%d/%m/%Y")


	return COD_formatted,end_of_operations_formatted,liquidation_formatted,debt_maturity_formatted

def import_seasonality(request):
	inp_seasonality = np.zeros(12)
	for i in range(1, 13):
		key = 'seasonality_m{}'.format(i)
		inp_seasonality[i - 1] = float(request.POST[key])
	return inp_seasonality

def import_construction_costs(request, construction_start, construction_end):
	construction_costs = np.zeros(12)

	delta = relativedelta(construction_end, construction_start)
	months = delta.years * 12 + delta.months + 1	

	for i in range(1, months):
		key = 'costs_m{}'.format(i)
		construction_costs[i-1] = float(request.POST[key])
	return construction_costs

def create_flag_operations(COD,period_start,period_end,end_of_operations):
	flag_operations = ((period_end>pd.to_datetime(COD))*(period_start<pd.to_datetime(end_of_operations))).astype(int)
	return flag_operations 

def create_flag_construction(period_start,construction_end):
	flag_construction = (period_start<pd.to_datetime(construction_end)).astype(int)
	return flag_construction

def create_flag_construction_end(period_end,construction_end):
	flag_construction_end = (period_end==pd.to_datetime(construction_end)).astype(int)
	return flag_construction_end 

def create_flag_construction_start(COD,period_start,construction_start):
	flag_construction_start = (period_start==pd.to_datetime(construction_start)).astype(int)
	return flag_construction_start 

def create_flag_liquidation(period_end,end_of_operations):
	flag_liquidation = (period_end>pd.to_datetime(end_of_operations + datetime.timedelta(days=1))).astype(int)
	return flag_liquidation 

def create_flag_liquidation_end(period_end,liquidation):
	flag_liquidation_end = (period_end==pd.to_datetime(liquidation)).astype(int)
	return flag_liquidation_end 

def create_contract_period_series(period_start,period_end,start_contract,end_contract):
	
	arr_date_start_contract_period = array_time(period_start,start_contract,end_contract)
	arr_date_end_contract_period = array_time(period_end,start_contract,end_contract)
	
	return arr_date_start_contract_period, arr_date_end_contract_period

def create_contract_index_series(request,period_start,period_end,start_contract,end_contract,date_contract_index_start):
	

	arr_date_start_contract_index_period = array_time(period_start,date_contract_index_start,end_contract)
	arr_date_end_contract_index_period = array_time(period_end,date_contract_index_start,end_contract)
	
	return arr_date_start_contract_index_period, arr_date_end_contract_index_period


def calculate_capacity(request,flag_operations):

	capacity_installed = int(request.POST['panels_capacity'])

	capacity_before_degradation = capacity_installed*flag_operations

	return capacity_before_degradation 

def calculate_degradation_factor(request,years_from_COD_avg):
	
	degradation = float(request.POST['annual_degradation'])/100		
	degradation_factor = 1/(1+degradation)**years_from_COD_avg
	
	return degradation_factor


def calculate_production(request,seasonality,capacity_after_degradation):

	if int(request.POST['production_choice']) == 1:
		inp_production = float(request.POST['p50'])
	elif int(request.POST['production_choice']) == 2:
		inp_production = float(request.POST['p90_10y'])
	else: 
		inp_production = float(request.POST['P99_10y'])

	seasonality=np.array(seasonality,dtype=float)

	production = inp_production/1000*seasonality*capacity_after_degradation


	return production



def determine_debt_constraint(debt_amount_DSCR,debt_amount_gearing):

	if debt_amount_DSCR>debt_amount_gearing:
		constraint = "Gearing"
	else: 
		constraint = "DSCR"

	return constraint


def create_table_uses(construction_costs_max,optimised_devfee,interests_during_construction,upfront_fee_max,commitment_fee,total_costs,dsra_initial_funding_max):

	senior_debt_i_and_fees =upfront_fee_max+commitment_fee+interests_during_construction

	table_table_uses = pd.DataFrame({
				"Construction costs":["{:.1f}".format(construction_costs_max)],
				"Development fee":["{:.1f}".format(optimised_devfee)],
				"Debt interests & fees":["{:.1f}".format(senior_debt_i_and_fees)],
				"Upfront fee":["{:.1f}".format(upfront_fee_max)],
				"Commitment fees":["{:.1f}".format(commitment_fee)],				
				"IDC":["{:.1f}".format(interests_during_construction)],
				"Initial DSRA funding":["{:.1f}".format(dsra_initial_funding_max)],
				"Total":["{:.1f}".format(total_costs)],
				})
	return table_table_uses


def create_table_sources(share_capital_injections,SHL_injections,debt_amount):

	share_capital_drawn = sum(share_capital_injections)
	shl_drawn = sum(SHL_injections)
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


def create_table_debt(DSCR_effective,debt_amount,debt_constraint,total_costs,flag_debt_amo,period_end,debt_cash_flows):
	
	DSCR_avg = DSCR_effective[flag_debt_amo == 1].mean()
	gearing_eff = (debt_amount/total_costs)

	debt_irr = xirr(pd.to_datetime(period_end).dt.date,debt_cash_flows)



	table_debt = pd.DataFrame({
					"Senior debt amount":["{:.1f}".format(debt_amount)],
					"Senior debt constraint":[debt_constraint],
					"Effective gearing":["{:.2%}".format(gearing_eff)],
					"Average DSCR":["{:.2f}".format(DSCR_avg)+"x"],
					"Debt IRR":["{:.2%}".format(debt_irr)],
					})
	return table_debt


def create_table_equity(construction_start,period_end,share_capital_cash_flows,SHL_cash_flows,equity_cash_flows,equity_cash_flows_cumul):

	share_capital_irr = xirr(pd.to_datetime(period_end).dt.date,share_capital_cash_flows)
	SHL_irr = xirr(pd.to_datetime(period_end).dt.date,SHL_cash_flows)
	equity_irr = xirr(pd.to_datetime(period_end).dt.date,equity_cash_flows)


	
	payback_date = find_payback_date(period_end,equity_cash_flows_cumul)

	try:
		payback_date = parser.parse(str(payback_date)).date()
		time_difference = payback_date-construction_start
		payback_time = round(time_difference.days / 365.25, 1)
		payback_date=payback_date.strftime("%d/%m/%Y")
	except ParserError:
		payback_date="error"
		payback_time="error"


	table_equity = pd.DataFrame({
				"Share capital IRR":["{:.2%}".format(share_capital_irr)],
				"Shareholder loan IRR":["{:.2%}".format(SHL_irr)],
				"Equity IRR":["{:.2%}".format(equity_irr)],
				"Payback date":[(payback_date)],
				"Payback time":[(payback_time)],

				})

	return table_equity


def find_payback_date(period_end,equity_cash_flows_cumul):

	# Find the indices where cumulative_equity is greater than or equal to zero
	valid_indices = np.where(equity_cash_flows_cumul >= 0)[0]

	if len(valid_indices) > 0:
		# Find the minimum date_period_end value at the valid indices
		payback_date_index = valid_indices[np.argmin(period_end[valid_indices])]
		payback_date = period_end[payback_date_index]
	else:
		payback_date = None
	"""payback_date = df.loc[df['Cumulative Equity for payback'] >= 0, 'Date Period end'].min()"""
	return payback_date



def create_table_projectIRR(total_uses,EBITDA,corporate_income_tax,period_end):


	project_cash_flows_pre_tax = -total_uses+EBITDA
	project_cash_flows_post_tax = project_cash_flows_pre_tax+corporate_income_tax

	project_irr_pre_tax = xirr(pd.to_datetime(period_end).dt.date,project_cash_flows_pre_tax)
	project_irr_post_tax = xirr(pd.to_datetime(period_end).dt.date,project_cash_flows_post_tax)



	table_projectIRR = pd.DataFrame({
				"Project IRR (pre-tax)":["{:.2%}".format(project_irr_pre_tax)],
				"Project IRR (post-tax)":["{:.2%}".format(project_irr_post_tax)],
				})

	return table_projectIRR


def compute_npv(cfads, discount_rate,period_end):
	npvs = []

	period_end=pd.to_datetime(period_end).dt.date
	

	for i in range(len(cfads)):
		npv = 0
		if cfads[i] > 1:
			for j in range(i, len(cfads)):
				end_date = period_end[j]
				start_date = period_end[i-1]
				time_delta = (end_date - start_date).days/365.25
				npv += cfads[j] / ((1+discount_rate) ** (time_delta))

			npvs.append(npv)
		else: 
			npvs.append(0)

	return npvs



def find_last_payment_date(period_end,boolean_array):
	boolean_array = boolean_array > 0
	new_array = [date if boolean else 0 for boolean, date in zip(boolean_array, period_end)]
	non_zero_dates = [date for date in new_array if date != 0]
	max_date = max(non_zero_dates)
	return max_date



def calculate_tenor(final_repayment_date, construction_start):
	time_difference = final_repayment_date-construction_start
	tenor = round(time_difference.days / 365.25, 1)
	return tenor




def create_table_financing_terms(request,construction_start,debt_amount,period_end,senior_debt_balance_eop,share_capital_eop,SHL_balance_eop,years_in_period,senior_debt_balance_bop,SHL_balance_bop,SHL_injections):

	inp_debt_gearing_max = request.POST['debt_gearing_max']+"%"
	inp_target_DSCR = request.POST['debt_target_DSCR']+"x"
	inp_subgearing=float(request.POST['subgearing'])
	subgearing_capital=str(100-inp_subgearing)+"%"
	subgearing_SHL=str(inp_subgearing)+"%"
	inp_injection = request.POST['injection_choice']

	final_repayment_date_debt=find_last_payment_date(period_end, senior_debt_balance_eop)
	final_repayment_date_equity=find_last_payment_date(period_end,share_capital_eop)	
	final_repayment_date_SHL=find_last_payment_date(period_end,SHL_balance_eop)

	final_repayment_date_debt = final_repayment_date_debt.strftime("%Y-%m-%d %H:%M:%S")
	final_repayment_date_debt = parser.parse(final_repayment_date_debt).date()

	
	final_repayment_date_equity = final_repayment_date_equity.strftime("%Y-%m-%d %H:%M:%S")
	final_repayment_date_equity = parser.parse(final_repayment_date_equity).date()


	final_repayment_date_SHL = final_repayment_date_SHL.strftime("%Y-%m-%d %H:%M:%S")
	final_repayment_date_SHL = parser.parse(final_repayment_date_SHL).date()

	tenor_debt = calculate_tenor(final_repayment_date_debt,construction_start)
	tenor_equity = calculate_tenor(final_repayment_date_equity,construction_start)
	tenor_SHL = calculate_tenor(final_repayment_date_SHL,construction_start)

	equity_injection_choice = {"1":"Equity first", "2":"Prorata"}

	if debt_amount>0:
		average_debt_life = sum(x * y for x, y in zip(years_in_period, senior_debt_balance_bop))/debt_amount
		average_debt_life = round(average_debt_life,1)
	else:
		average_debt_life=""	

	SHL_amount = sum(SHL_injections)

	if SHL_amount>0:
		average_SHL_life = sum(x * y for x, y in zip(years_in_period, SHL_balance_bop))/SHL_amount
		average_SHL_life = round(average_SHL_life,1)
	else:
		average_SHL_life=""

	table_financing_terms = pd.DataFrame({
				"":["Share capital","Shareholder loan","Senior Debt"],
				"Equity injection":[equity_injection_choice[inp_injection],equity_injection_choice[inp_injection],equity_injection_choice[inp_injection]],
				"Average life (from FC)":["",average_SHL_life,average_debt_life],
				"Date of final repayment":[final_repayment_date_equity,final_repayment_date_SHL,final_repayment_date_debt],
				"Tenor (door-to-door)":[tenor_equity,tenor_SHL,tenor_debt],
				"Subgearing":[subgearing_capital,subgearing_SHL,""],
				"Maximum gearing":["","",inp_debt_gearing_max],
				"Minimum DSCR":["","",inp_target_DSCR],
				})

	return table_financing_terms



def create_table_audit(audit_financing_plan,audit_balance_sheet):

	check_financing_plan_balanced = abs(sum(audit_financing_plan))<0.01
	check_balance_sheet_balanced = abs(sum(audit_balance_sheet))<0.01

	table_audit = pd.DataFrame({
		"Financing plan":[check_financing_plan_balanced],
		"Balance sheet":[check_balance_sheet_balanced],

		})

	return table_audit

def create_IRR_curve(equity_cash_flows,period_end):

	irr_values = []

	# Iterate through each period and calculate the IRR up to that period
	for i in range(1, len(equity_cash_flows)+1):
		subset_cash_flows = equity_cash_flows.iloc[:i]
		subset_dates = pd.to_datetime(period_end.iloc[:i]).dt.date

		try:
			irr = xirr(subset_dates, subset_cash_flows)*100
		except:
			irr = 0.0

		irr_values.append(max(irr,0,0))

	return irr_values 

def optimise_devfee(request,debt_amount_DSCR,construction_costs_max,interests_during_construction):

	dev_fee_switch = int(request.POST['devfee_choice'])
	gearing_max = float(request.POST['debt_gearing_max'])/100

	total_costs_wo_devfee = construction_costs_max+interests_during_construction


	if dev_fee_switch == 1:
		optimised_devfee = max(debt_amount_DSCR/gearing_max-total_costs_wo_devfee,0)
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

def array_elec_prices(period_end_year,dic_price_elec):
	electricity_prices = []
	
	for row in period_end_year:
		if str(row) in dic_price_elec.keys():
			electricity_prices.append(dic_price_elec[str(row)])
		else:
			electricity_prices.append(0)
	
	return electricity_prices

def array_seasonality(period_start,period_end,inp_seasonality):
	data = {'start':period_start,
			'end':period_end}

	df = pd.DataFrame(data)

	df_seasonality_result = pd.DataFrame(columns=period_end)

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

def end_date_period(period):	
	end_date_period = period.replace(day = calendar.monthrange(period.year, period.month)[1])
	return end_date_period

def first_day_month(date):
	first_day_month = date.replace(day=1)
	return first_day_month

def first_day_next_month(date,periodicity):
	first_day_next_month = date.replace(day=1) + relativedelta(months=periodicity) + datetime.timedelta(days=-1)
	return first_day_next_month



def is_numpy_array(arr):
	return isinstance(arr, np.ndarray)

def is_pandas_array(arr):
	return isinstance(arr, (pd.DataFrame, pd.Series))
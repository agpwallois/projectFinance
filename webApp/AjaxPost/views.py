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

import math

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
	return render(request, "testrr.html", context)

def project_view(request,id):

	project_form = ProjectForm()
	project = Project.objects.get(id=id)

	if request.method == "POST":
		project_form = ProjectForm(request.POST, instance=project)

		if project_form.is_valid():
			project_form.save()

			""" Timing inputs """

			inp_construction_start = request.POST['start_construction']
			inp_construction_end = request.POST['end_construction']
			inp_life = int(request.POST['operating_life'])
			
			inp_liquidation = int(request.POST['liquidation'])

			start_period = datetime.datetime.strptime(inp_construction_start, "%Y-%m-%d").date()
			end_construction = datetime.datetime.strptime(inp_construction_end, "%Y-%m-%d").date()

			"""int_operating_periods = math.ceil(int(inp_life)*12/int(periodicity)+1)"""

			date_COD = end_construction + datetime.timedelta(days=1) 
			formatted_date_COD = date_COD.strftime("%d/%m/%Y")
			date_operations_end = end_construction + relativedelta(years=inp_life)
			formatted_date_operations_end = date_operations_end.strftime("%d/%m/%Y")

			date_liquidation = date_operations_end + relativedelta(months=inp_liquidation)
			formatted_date_liquidation = date_liquidation.strftime("%d/%m/%Y")




			""" Capacity and Production inputs """

			inp_availability = float(request.POST['availability'])	

			seasonality = np.array([
			float(request.POST['seasonality_m1']),
			float(request.POST['seasonality_m2']),
			float(request.POST['seasonality_m3']),
			float(request.POST['seasonality_m4']),
			float(request.POST['seasonality_m5']),
			float(request.POST['seasonality_m6']),
			float(request.POST['seasonality_m7']),
			float(request.POST['seasonality_m8']),
			float(request.POST['seasonality_m9']),
			float(request.POST['seasonality_m10']),
			float(request.POST['seasonality_m11']),
			float(request.POST['seasonality_m12']),
			])

			sum_seasonality = np.sum(seasonality)
			sum_seasonality = (sum_seasonality / np.sum(seasonality)) * 100

			""" Construction costs inputs """

			arr_construction_costs = np.array([
			float(request.POST['costs_m1']),
			float(request.POST['costs_m2']),
			float(request.POST['costs_m3']),
			float(request.POST['costs_m4']),
			float(request.POST['costs_m5']),
			float(request.POST['costs_m6']),
			float(request.POST['costs_m7']),
			float(request.POST['costs_m8']),
			float(request.POST['costs_m9']),
			float(request.POST['costs_m10']),
			float(request.POST['costs_m11']),
			float(request.POST['costs_m12']),
			])

			sum_construction_costs = np.sum(arr_construction_costs)

			r = relativedelta(end_construction,start_period)
			months_construction = (r.years * 12) + r.months + 1
			months_construction = math.ceil(int(months_construction))

			""" Offtake contract and Electricity price inputs """

			inp_price_merchant_index_rate_start_date = request.POST['price_elec_indexation_start_date']
			date_price_elec_index_start = datetime.datetime.strptime(inp_price_merchant_index_rate_start_date, "%Y-%m-%d").date()
		
			""" Electricity price inputs """
			dic_price_elec = create_price_elec_dict(request)
			dic_price_elec_keys = np.array(list(dic_price_elec.keys()))

			""" Operating costs """

			inp_opex_index_start_date = request.POST['opex_indexation_start_date']
			date_opex_index_start = datetime.datetime.strptime(inp_opex_index_start_date, "%Y-%m-%d").date()

			""" Senior debt """

			inp_debt_commitment_fee = float(request.POST['debt_commitment_fee'])/100

			inp_debt_tenor = float(request.POST['debt_tenor'])
			date_debt_maturity = start_period + relativedelta(months=+int(inp_debt_tenor*12)-1)
			formatted_date_debt_maturity = date_debt_maturity.strftime("%d/%m/%Y")
			date_debt_maturity = date_debt_maturity.replace(day = calendar.monthrange(date_debt_maturity.year, date_debt_maturity.month)[1])

			inp_debt_gearing_max = float(request.POST['debt_gearing_max'])/100

			""" Arrays instanciation """

			df = pd.DataFrame()

			""" Create date series """

			arr_start_period,arr_end_period = create_period_series(request)

			df = df_timeline(df,arr_start_period,arr_end_period)
			df = df_flags_operations(df,date_COD,arr_start_period,arr_end_period,end_construction,date_operations_end,date_liquidation)
			df = df_timeline_contract(df,request,arr_start_period,arr_end_period)

			arr_end_period_year = arr_end_period.dt.year

			df['FlagMod Year'] = arr_end_period_year

			arr_date_start_elec_index = array_time(arr_start_period,date_price_elec_index_start,date_operations_end)
			df['Date Electricity price indexation start date'] = pd.to_datetime(arr_date_start_elec_index).dt.strftime('%d/%m/%Y')
			
			arr_date_end_elec_index = array_time(arr_end_period,date_price_elec_index_start,date_operations_end)
			df['Date Electricity price indexation end date'] = pd.to_datetime(arr_date_end_elec_index).dt.strftime('%d/%m/%Y')

			arr_date_start_opex_index = array_time(arr_start_period,date_opex_index_start,date_operations_end)
			df['Date Opex indexation start date'] = pd.to_datetime(arr_date_start_opex_index).dt.strftime('%d/%m/%Y')
			
			arr_date_end_opex_index = array_time(arr_end_period,date_opex_index_start,date_operations_end)
			df['Date Opex indexation end date'] = pd.to_datetime(arr_date_end_opex_index).dt.strftime('%d/%m/%Y')


			""" Create flag series """

			df['arr_flag_elec_index'] = array_flag(arr_date_end_elec_index,date_price_elec_index_start,arr_date_start_elec_index,date_operations_end)
			df['arr_flag_opex_index'] = array_flag(arr_date_end_opex_index,date_opex_index_start,arr_date_start_opex_index,date_operations_end)
			df['arr_flag_debt_amortisation'] = (arr_end_period<pd.to_datetime(date_debt_maturity)).astype(int)*df['FlagOp Operations']

			""" Create time series """

			df['FlagMod Days in period'] = array_days(arr_end_period,arr_start_period,1)
			df['FlagOftk Percentage in contract period']=df['FlagOftk Days in contract period']/df['FlagMod Days in period']

			df['arr_time_days_merchant_index'] = array_days(arr_date_end_elec_index,arr_date_start_elec_index,df['arr_flag_elec_index'])
			df['arr_time_days_opex_index'] = array_days(arr_date_end_opex_index,arr_date_start_opex_index,df['arr_flag_opex_index'])

			df['FlagMod Days in year'] = arr_end_period.dt.is_leap_year*366 + (1-arr_end_period.dt.is_leap_year)*365
			df['FlagMod Years in period'] = df['FlagMod Days in period']/df['FlagMod Days in year']
			df['FlagOp Years during operations'] = df['FlagMod Years in period']*df['FlagOp Operations']
			df['FlagOp Years from COD (EoP)'] = df['FlagOp Years during operations'].cumsum()
			df['FlagOp Years from COD (BoP)'] = df['FlagOp Years from COD (EoP)']-df['FlagOp Years during operations']
			df['FlagOp Years from COD (avg.)'] = (df['FlagOp Years from COD (BoP)']+df['FlagOp Years from COD (EoP)'])/2

			df['arr_time_years_contract_index']=(df['arr_time_days_contract_index']/df['FlagMod Days in year']).cumsum()
			df['arr_time_years_merchant_index']=(df['arr_time_days_merchant_index']/df['FlagMod Days in year']).cumsum()
			df['arr_time_years_opex_index']=(df['arr_time_days_opex_index']/df['FlagMod Days in year']).cumsum()

			df = df_production(df,request,arr_start_period,arr_end_period,seasonality)
			df = df_indexation(df,request)
			df = df_prices(df,request,arr_end_period_year,dic_price_elec)
			df = df_revenues(df)
			df = df_opex(df,request)
			df = df_EBITDA(df)

			df['FP_u Construction costs'] = np.hstack([arr_construction_costs,np.zeros(df['FlagOp Operations'].size-arr_construction_costs.size)])*df['FlagCons Construction']
			df['arr_construction_costs_cumul'] = df['FP_u Construction costs'].cumsum()
			construction_costs = max(df['arr_construction_costs_cumul'])

			number_columns = sum(df['FlagCons Construction'])+sum(df['FlagOp Operations'])+sum(df['FlagOp Liquidation'])-1

			debt_amount = 1000
			debt_amount_target = 2000
			optimised_devfee = 0
			df['arr_sizing_debt_repayment_target'] = np.full(number_columns+1, -200)
			df['RE Distributable profit'] = np.full(number_columns+1, 0)
			df['Distr Cash available for dividends'] = np.full(number_columns+1, 0)
			df['FP_u Development fee']= np.full(number_columns+1, 0)
			df['Distr Cash available for dividends'] = np.full(number_columns+1, 0)
			df['Distr Distribution account balance (BoP)'] = np.full(number_columns+1, 0)




			df['FP_u Total uses'] = df['FP_u Construction costs']

			debt_amount_not_converged = True

			while debt_amount_not_converged or debt_sculpting_not_converged:
				
				""" Parameters to converge iteratively """

				debt_amount = debt_amount_target
				df['Debt Senior debt principal repayment'] = -df['arr_sizing_debt_repayment_target']

				""" Calculation """

				df = df_debt(df,request,debt_amount)
				df = df_depreciation(df,request,construction_costs,optimised_devfee)
				df = df_fin_plan(df)
				df = df_income_statement(df,request)
				df = df_cash_flow(df)

				""" Debt sizing """

				df = df_debt_sizing(df,request)

				debt_amount_DSCR = npv(df['arr_sizing_target_DS_sizing'],df['arr_sizing_debt_period_discount_factor_cumul'])
				
				idc = sum(df['FP_u Interests during construction'])
				total_costs_wo_devfee = construction_costs+idc

				optimised_devfee = optimise_devfee(request,debt_amount_DSCR,total_costs_wo_devfee)
				total_costs = construction_costs+idc+optimised_devfee

				debt_amount_gearing = total_costs*inp_debt_gearing_max
				debt_amount_target = min(debt_amount_DSCR,debt_amount_gearing)

				df['FP_u Development fee'] = optimised_devfee * df['FlagCons Construction end']
				df['arr_development_fee_cumul'] = df['FP_u Development fee'].cumsum()

				""" Debt sculpting """

				df = df_debt_sculpting(df)

				""" Convergence tests """

				debt_amount_not_converged = abs(debt_amount-debt_amount_target)>0
				debt_sculpting_not_converged = sum(df['arr_sculpting_test'])!=0

			""" Distribution account """
			
			for i in range(100):
				
				df = df_distr_account(df)

			""" Balance sheet """		

			df['Distr Share capital reimbursement'] = df['Distr Distribution account balance (BoP)']*df['FlagOp Liquidation end']
			df['Distr Distribution account balance (EoP)'] = df['Distr Distribution account balance (EoP)']-df['Distr Share capital reimbursement']
			
			df = df_balance_sheet(df)

			df = create_IRR_curve(df,arr_end_period)




			check_balance_sheet_balanced = abs(sum(df['Audit Balance sheet balanced']))<0.001
			check_financing_plan_balanced = abs(sum(df['Audit Financing plan balanced']))<0.001
	
			""" Financing plan """

			equity_drawn = sum(df['FP_s Equity injections'])

			if debt_amount_DSCR>debt_amount_gearing:
				constraint = "Gearing"
			else: 
				constraint = "DSCR"

			gearing_eff = (debt_amount/total_costs)
			DSCR_avg = df['arr_ratios_DSCR'].where(df['arr_flag_debt_amortisation']==1).mean()

			fp_uses = total_costs
			fp_sources = equity_drawn+debt_amount

			df_result_fp_uses = pd.DataFrame({
				"Construction costs":["{:.1f}".format(construction_costs)],
				"Development fee":["{:.1f}".format(optimised_devfee)],
				"Interests during construction":["{:.1f}".format(idc)],
				"Total":["{:.1f}".format(fp_uses)],
				})

			df_result_fp_sources = pd.DataFrame({
				"Equity":["{:.1f}".format(equity_drawn)],
				"Debt":["{:.1f}".format(debt_amount)],
				"Total":["{:.1f}".format(fp_sources)],
				})

			irr = xirr(pd.to_datetime(arr_end_period).dt.date,df['arr_sponsors_cash_flows'])

			df_result = pd.DataFrame({
				"Debt amount":["{:.1f}".format(debt_amount)],
				"Debt constraint":[constraint],
				"Effective gearing":["{:.2%}".format(gearing_eff)],
				"Average DSCR":["{:.2f}".format(DSCR_avg)+"x"],
				})

			df_audit = pd.DataFrame({
				"Balance sheet":[check_balance_sheet_balanced],
				"Financing plan":[check_financing_plan_balanced],

				})
			
			df_sum = df.apply(pd.to_numeric, errors='coerce').sum()

			data_dump_summary = np.array([])

			df_result_equity = pd.DataFrame({
				"IRR":["{:.2%}".format(irr)],
				})



			data_dump_sidebar = np.array([
				formatted_date_COD,
				formatted_date_operations_end,
				sum_seasonality,
				sum_construction_costs,
				formatted_date_liquidation,
				formatted_date_debt_maturity,
				])


			return JsonResponse({

				"df":df.to_dict(),
				"df_sum":df_sum.to_dict(),

				"df1":df.to_json(),

				"df_result":df_result.to_dict(),
				"df_result_equity":df_result_equity.to_dict(),

				"df_result_fp_uses":df_result_fp_uses.to_dict(),
				"df_result_fp_sources":df_result_fp_sources.to_dict(),

				"df_audit":df_audit.to_dict(),

				"seasonality":seasonality.tolist(),
				"dic_price_elec_keys":dic_price_elec_keys.tolist(),
				"data_dump_sidebar":data_dump_sidebar.tolist(),
				"data_dump_summary":data_dump_summary.tolist(),


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

def create_period_series(request):

	periodicity = int(request.POST['periodicity'])
	liquidation = int(request.POST['liquidation'])
	start_construction = request.POST['start_construction']
	end_construction = request.POST['end_construction']
	operating_life = int(request.POST['operating_life'])

	formatted_start_construction = datetime.datetime.strptime(start_construction, "%Y-%m-%d").date()
	formatted_end_construction = datetime.datetime.strptime(end_construction, "%Y-%m-%d").date()

	COD = formatted_end_construction + datetime.timedelta(days=1) 
	date_operations_end = formatted_end_construction + relativedelta(years=operating_life)
	start_liquidation = date_operations_end + datetime.timedelta(days=1) 
	end_liquidation = date_operations_end + relativedelta(months=liquidation)
	first_day_start_liquidation = date_operations_end + datetime.timedelta(days=1) 

	freq_start_period = str(periodicity)+"MS"
	freq_end_period = str(periodicity)+"M"

	first_day_start_construction = first_day_month(formatted_start_construction)
	first_day_start_operations = first_day_month(COD)
	first_day_start_liquidation = first_day_month(date_operations_end)
	
	last_day_end_construction = end_date_period(formatted_end_construction)
	last_day_end_operations = end_date_period(date_operations_end)
	
	#Période mensuelle pendant le plan de financement puis selon la périodicité
	start_period_construction = pd.Series(pd.date_range(first_day_start_construction,last_day_end_construction, freq='MS')).clip(lower=pd.Timestamp(formatted_start_construction))
	start_period_operations = pd.Series(pd.date_range(first_day_start_operations, last_day_end_operations,freq=freq_start_period)).clip(lower=pd.Timestamp(COD))
	start_period_liquidation = pd.Series(pd.date_range(first_day_start_liquidation, end_liquidation,freq=freq_start_period)).clip(lower=pd.Timestamp(start_liquidation))
	
	arr_start_period = pd.concat([start_period_construction,start_period_operations,start_period_liquidation], ignore_index=True)

	first_day_start_operations_plus_freq = first_day_next_month(COD,periodicity)
	last_day_end_operations_plus_freq = first_day_next_month(date_operations_end,periodicity)
	first_day_start_liquidation_plus_freq = first_day_next_month(first_day_start_liquidation,periodicity)
	last_day_end_liquidation_plus_freq = first_day_next_month(end_liquidation,periodicity)

	#Période mensuelle pendant le plan de financement puis selon la périodicité
	end_period_construction = pd.Series(pd.date_range(first_day_start_construction,last_day_end_construction, freq='M')).clip(upper=pd.Timestamp(formatted_end_construction))
	end_period_operations = pd.Series(pd.date_range(first_day_start_operations_plus_freq, last_day_end_operations_plus_freq,freq=freq_end_period)).clip(upper=pd.Timestamp(date_operations_end))
	end_period_liquidation= pd.Series(pd.date_range(first_day_start_liquidation_plus_freq, last_day_end_liquidation_plus_freq,freq=freq_end_period)).clip(upper=pd.Timestamp(end_liquidation))
	
	arr_end_period = pd.concat([end_period_construction,end_period_operations,end_period_liquidation], ignore_index=True)
	
	return arr_start_period, arr_end_period

def create_price_elec_dict(request):
	
	choice = int(request.POST['price_elec_choice'])

	end_construction = datetime.datetime.strptime(request.POST['end_construction'], "%Y-%m-%d").date()
	COD = end_construction + datetime.timedelta(days=1)
	COD_year = int(COD.year)

	years = [str(year) for year in range(COD_year, COD_year+30)]

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

def df_timeline(df,arr_start_period,arr_end_period):
	df_copy = df.copy()
	df_copy['Date Period start'] = pd.to_datetime(arr_start_period).dt.strftime('%d/%m/%Y')
	df_copy['Date Period end'] = pd.to_datetime(arr_end_period).dt.strftime('%d/%m/%Y')
	return df_copy 

def df_flags_operations(df,COD,arr_start_period,arr_end_period,end_construction,date_operations_end,liquidation):
	df_copy = df.copy()
	df_copy['FlagOp Operations'] = ((arr_end_period>pd.to_datetime(COD))*(arr_start_period<pd.to_datetime(date_operations_end))).astype(int)
	df_copy['FlagOp Liquidation'] = (arr_end_period>pd.to_datetime(date_operations_end + datetime.timedelta(days=1))).astype(int)
	df_copy['FlagOp Liquidation end'] = (arr_end_period==pd.to_datetime(liquidation)).astype(int)

	df_copy['FlagCons Construction'] = (arr_start_period<pd.to_datetime(end_construction)).astype(int)
	df_copy['FlagCons Construction end'] = (arr_end_period==pd.to_datetime(end_construction)).astype(int)
	return df_copy 

def df_timeline_contract(df,request,arr_start_period,arr_end_period):
	df_copy = df.copy()

	start_contract = request.POST['start_contract']
	end_contract = request.POST['end_contract']

	contract_index_start_date = request.POST['contract_indexation_start_date']
	date_contract_index_start = datetime.datetime.strptime(contract_index_start_date, "%Y-%m-%d").date()

	arr_date_start_contract_period = array_time(arr_start_period,start_contract,end_contract)
	arr_date_end_contract_period = array_time(arr_end_period,start_contract,end_contract)

	df_copy['Date Contract start date'] = pd.to_datetime(arr_date_start_contract_period).dt.strftime('%d/%m/%Y')
	df_copy['Date Contract end date'] = pd.to_datetime(arr_date_end_contract_period).dt.strftime('%d/%m/%Y')


	df_copy['FlagOftk Contract Period'] = array_flag(arr_date_end_contract_period,start_contract,arr_date_start_contract_period,end_contract)
	df_copy['FlagOftk Days in contract period'] = array_days(arr_date_end_contract_period,arr_date_start_contract_period,df_copy['FlagOftk Contract Period'])

	arr_date_start_contract_index = array_time(arr_start_period,date_contract_index_start,end_contract)
	arr_date_end_contract_index = array_time(arr_end_period,date_contract_index_start,end_contract)
	df_copy['arr_flag_contract_index'] = array_flag(arr_date_end_contract_index,date_contract_index_start,arr_date_start_contract_index,end_contract)
	df_copy['arr_time_days_contract_index'] = array_days(arr_date_end_contract_index,arr_date_start_contract_index,df_copy['arr_flag_contract_index'])
	
	return df_copy 

def df_production(df,request,arr_start_period,arr_end_period,seasonality):
	df_copy = df.copy()

	capacity_installed = int(request.POST['panels_capacity'])
	degradation_factor = float(request.POST['annual_degradation'])/100		

	if int(request.POST['production_choice']) == 1:
		production = int(request.POST['p50'])
	elif int(request.POST['production_choice']) == 2:
		production = int(request.POST['p90_10y'])
	else: 
		production = int(request.POST['P99_10y'])

	df_copy['FlagOp Seasonality'] = array_seasonality(arr_start_period,arr_end_period,seasonality)
	df_copy['Prod Capacity before degradation'] = capacity_installed*df_copy['FlagOp Operations']
	df_copy['Prod Capacity degradation'] = 1/(1+degradation_factor)**df_copy['FlagOp Years from COD (avg.)']
	df_copy['Prod Capacity after degradation'] = df_copy['Prod Capacity before degradation']*df_copy['Prod Capacity degradation']
	df_copy['Prod Production'] = production/1000*df_copy['FlagOp Seasonality']*df_copy['Prod Capacity after degradation']

	return df_copy 

def df_indexation(df,request):
	df_copy = df.copy()
	
	index_rate_merchant = float(request.POST['price_elec_indexation'])/100
	index_rate_contract = float(request.POST['contract_indexation'])/100
	index_rate_opex = float(request.POST['opex_indexation'])/100

	df_copy['arr_index_merchant'] = array_index(index_rate_merchant,df_copy['arr_time_years_merchant_index'])
	df_copy['arr_index_contract'] = array_index(index_rate_contract,df_copy['arr_time_years_contract_index'])
	df_copy['arr_index_opex'] = array_index(index_rate_opex,df_copy['arr_time_years_opex_index'])
	return df_copy 

def df_prices(df,request,arr_end_period_year,dic_price_elec):
	df_copy = df.copy()

	price_contract = float(request.POST['contract_price'])

	df_copy['Price Electricity market price before indexation'] = array_elec_prices(arr_end_period_year,dic_price_elec)
	df_copy['Price Electricity market price after indexation'] = df_copy['Price Electricity market price before indexation']*df_copy['arr_index_merchant']
	df_copy['Price Contract price before indexation'] = price_contract*df['FlagOftk Contract Period']
	df_copy['Price Contract price after indexation'] = df_copy['Price Contract price before indexation']*df_copy['arr_index_contract']
	return df_copy 

def df_revenues(df):
	df_copy = df.copy()
	df_copy['IS Contracted revenues'] = df_copy['Price Contract price after indexation']*df_copy['Prod Production']*df_copy['FlagOftk Percentage in contract period']/1000
	df_copy['IS Uncontracted electricity revenues'] = df_copy['Price Electricity market price after indexation']*df_copy['Prod Production']*(1-df_copy['FlagOftk Percentage in contract period'])/1000
	df_copy['IS Total revenues'] = df_copy['IS Contracted revenues']+df_copy['IS Uncontracted electricity revenues']
	return df_copy 

def df_opex(df,request):
	df_copy = df.copy()
	
	opex = float(request.POST['opex'])

	df_copy['IS Operating expenses'] = -opex*df_copy['arr_index_opex']*df_copy['FlagOp Years during operations']
	return df_copy 

def df_EBITDA(df):
	df_copy = df.copy()
	df_copy['IS EBITDA'] = df_copy['IS Total revenues']+df_copy['IS Operating expenses']
	df_copy['arr_EBITDA_margin'] = np.divide(df_copy['IS EBITDA'],df_copy['IS Total revenues'], out=np.zeros_like(df_copy['IS EBITDA']), where=df_copy['IS Total revenues']!=0)*100
	return df_copy 

def df_debt(df,request,debt_amount):
	df_copy = df.copy()

	inp_debt_gearing_max = float(request.POST['debt_gearing_max'])/100

	inp_all_in_interest = np.array([
		float(request.POST['debt_margin']),
		float(request.POST['debt_swap_rate']),
		float(request.POST['debt_swap_margin']),
		float(request.POST['debt_reference_rate_buffer']),
		])

	inp_debt_interest_rate = np.sum(inp_all_in_interest)/100

	df_copy['FP_u Cumulative total uses'] = df_copy['FP_u Total uses'].cumsum()
	df_copy['Debt Cumulative senior debt drawdowns'] = (df_copy['FP_u Cumulative total uses']*inp_debt_gearing_max).clip(upper=debt_amount)
	df_copy['Debt Senior debt drawdowns'] = np.ediff1d(df_copy['Debt Cumulative senior debt drawdowns'],to_begin=df_copy['Debt Cumulative senior debt drawdowns'][0])
	df_copy['arr_equity_drawn'] = df_copy['FP_u Total uses']-df_copy['Debt Senior debt drawdowns']
	df_copy['Debt Senior debt balance (EoP)'] = (df_copy['Debt Cumulative senior debt drawdowns']+df_copy['Debt Senior debt principal repayment'].cumsum()).clip(lower=0)
	df_copy['Debt Senior debt balance (BoP)'] = np.roll(df_copy['Debt Senior debt balance (EoP)'], 1)
	df_copy['Debt Senior debt interests'] = df_copy['Debt Senior debt balance (BoP)']*inp_debt_interest_rate*df_copy['FlagMod Days in period']/360
	df_copy['arr_sizing_debt_interest_operations'] = df_copy['Debt Senior debt interests']*df_copy['arr_flag_debt_amortisation']
	df_copy['arr_sizing_debt_interest_construction'] = df_copy['Debt Senior debt interests']*df_copy['FlagCons Construction']
	df_copy['arr_capitalised_costs_cumul'] = df_copy['arr_sizing_debt_interest_construction'].cumsum()
	return df_copy 

def df_depreciation(df,request,construction_costs,optimised_devfee):
	df_copy = df.copy()

	length_operations = int(request.POST['operating_life'])
	
	debt_capitalised_interest = max(df_copy['arr_capitalised_costs_cumul'])
	df_copy['IS Depreciation'] = -(construction_costs+debt_capitalised_interest+optimised_devfee)*df_copy['FlagOp Years during operations']/length_operations

	return df_copy 

def df_fin_plan(df):
	df_copy = df.copy()

	df_copy['FP_u Interests during construction'] = df_copy['Debt Senior debt interests']*df_copy['FlagCons Construction']
	df_copy['FP_u Total uses'] = df_copy['FP_u Construction costs']+df_copy['FP_u Interests during construction']+df_copy['FP_u Development fee']
	return df_copy 


def create_IRR_curve(df,arr_end_period):
	df_copy= df.copy()

	irr_values = []

	# Iterate through each period and calculate the IRR up to that period
	for i in range(1, len(df_copy['arr_sponsors_cash_flows'])+1):
		subset_cash_flows = df_copy['arr_sponsors_cash_flows'].iloc[:i]
		subset_dates = pd.to_datetime(arr_end_period.iloc[:i]).dt.date

		try:
		    irr = xirr(subset_dates, subset_cash_flows)*100
		except:
		    irr = 0.0

		irr_values.append(irr)

	df_copy['IRR curve'] = irr_values
	return df_copy 


def df_income_statement(df,request):
	df_copy = df.copy()

	income_tax_rate = float(request.POST['corporate_income_tax'])/100

	df_copy['IS EBIT'] = df_copy['IS EBITDA']+df_copy['IS Depreciation']
	df_copy['IS Interests'] = -df_copy['arr_sizing_debt_interest_operations']
	df_copy['IS EBT'] = df_copy['IS EBIT']+df_copy['IS Interests']
	df_copy['IS Corporate income tax'] = -income_tax_rate*df_copy['IS EBT'].clip(lower=0)
	df_copy['IS Net income'] = df_copy['IS EBT']+df_copy['IS Corporate income tax']
	return df_copy 


def df_cash_flow(df):
	df_copy = df.copy()
	df_copy['CF_op EBITDA'] = df_copy['IS EBITDA']
	df_copy['CF_op Corporate income tax'] = df_copy['IS Corporate income tax']
	df_copy['CF_op Cash flows from operating activities'] = df_copy['CF_op EBITDA']+df_copy['CF_op Corporate income tax']
	df_copy['CF_in Construction costs'] = -df_copy['FP_u Construction costs']
	df_copy['CF_in Development fee'] = -df_copy['FP_u Development fee']
	df_copy['CF_in Interests during construction'] = -df_copy['FP_u Interests during construction'] 
	df_copy['CF_in Cash flows from investing activities'] = df_copy['CF_in Construction costs']+df_copy['CF_in Interests during construction']+df_copy['CF_in Development fee']
	df_copy['CF_fi Senior debt drawdowns'] = df_copy['Debt Senior debt drawdowns']
	df_copy['CF_fi Equity injections'] = df_copy['arr_equity_drawn']
	df_copy['CF_fi Cash flows from financing activities'] = df_copy['CF_fi Senior debt drawdowns']+df_copy['CF_fi Equity injections']
	df_copy['CFADS CFADS'] = df_copy['CF_op Cash flows from operating activities']+df_copy['CF_in Cash flows from investing activities']+df_copy['CF_fi Cash flows from financing activities']
	df_copy['CFADS Senior debt interests'] = -df_copy['arr_sizing_debt_interest_operations'] 
	df_copy['CFADS Senior debt principal'] = df_copy['Debt Senior debt principal repayment']
	return df_copy 


def df_debt_sizing(df,request):
	df_copy = df.copy()

	target_DSCR = float(request.POST['debt_target_DSCR'])

	df_copy['arr_sizing_CFADS'] = df_copy['CFADS CFADS']*df_copy['arr_flag_debt_amortisation']
	df_copy['arr_sizing_target_DS_sizing'] = df_copy['arr_sizing_CFADS']/target_DSCR

	df_copy['arr_sizing_debt_avg_interest'] = np.divide(df_copy['arr_sizing_debt_interest_operations'],df_copy['Debt Senior debt balance (BoP)'],out=np.zeros_like(df_copy['arr_sizing_debt_interest_operations']), where=df_copy['Debt Senior debt balance (BoP)']!=0)/df_copy['FlagMod Days in period']*360
	df_copy['arr_sizing_debt_period_discount_factor'] = (1/(1+(df_copy['arr_sizing_debt_avg_interest']*df_copy['FlagMod Days in period']/360)))*df_copy['arr_flag_debt_amortisation']+df_copy['FlagCons Construction']
	df_copy['arr_sizing_debt_period_discount_factor_cumul'] = df_copy['arr_sizing_debt_period_discount_factor'].cumprod()
	return df_copy 


def df_debt_sculpting(df):
	df_copy = df.copy()

	cumul_debt_drawn  = max(df_copy['Debt Cumulative senior debt drawdowns'])
	npv_CFADS = npv(df_copy['arr_sizing_CFADS'],df_copy['arr_sizing_debt_period_discount_factor_cumul'])
	DSCR_sculpting = npv_CFADS/cumul_debt_drawn
	df_copy['arr_sizing_debt_repayment_target'] = (df_copy['arr_sizing_CFADS']/DSCR_sculpting-df_copy['arr_sizing_debt_interest_operations']).clip(lower=0)
	df_copy['arr_sculpting_test'] = df_copy['arr_sizing_debt_repayment_target']+df_copy['Debt Senior debt principal repayment']
	return df_copy 


def df_distr_account(df):
	df_copy = df.copy()

	df_copy['Distr Dividends paid'] = df_copy['Distr Cash available for dividends'].where(df_copy['Distr Cash available for dividends'] < df_copy['RE Distributable profit'], df_copy['RE Distributable profit'])

	df_copy['Distr Transfers to the distribution account'] = df_copy['CFADS CFADS']+df_copy['CFADS Senior debt interests']+df_copy['CFADS Senior debt principal']
	df_copy['Distr Distribution account balance (EoP)'] = df_copy['Distr Transfers to the distribution account'].cumsum()-df_copy['Distr Dividends paid'].cumsum()
	df_copy['Distr Distribution account balance (BoP)'] = df_copy['Distr Distribution account balance (EoP)']+df_copy['Distr Dividends paid']-df_copy['Distr Transfers to the distribution account']
	df_copy['Distr Cash available for dividends'] = df_copy['Distr Distribution account balance (BoP)'] + df_copy['Distr Transfers to the distribution account']
	
	df_copy['RE Retained earnings (EoP)'] = df_copy['IS Net income'].cumsum()-df_copy['Distr Dividends paid'].cumsum()
	df_copy['RE Retained earnings (BoP)'] = df_copy['RE Retained earnings (EoP)']+df_copy['Distr Dividends paid']-df_copy['IS Net income']
	df_copy['RE Distributable profit'] = (df_copy['RE Retained earnings (BoP)']+df_copy['IS Net income']).clip(lower=0)

	return df_copy 


def df_balance_sheet(df):
	df_copy = df.copy()

	df_copy['RE Net income'] = df_copy['IS Net income']
	df_copy['RE Dividend declared'] = df_copy['Distr Dividends paid']

	df_copy['BS_a Assets'] = df_copy['arr_construction_costs_cumul']+df_copy['arr_capitalised_costs_cumul']+df_copy['arr_development_fee_cumul']+df_copy['IS Depreciation'].cumsum()
	df_copy['BS_a Distribution account balance'] = df_copy['Distr Distribution account balance (EoP)']

	df_copy['BS_a Total assets'] = df_copy['BS_a Assets']+df_copy['BS_a Distribution account balance']

	df_copy['BS_l Retained earnings'] = df_copy['RE Retained earnings (EoP)']
	df_copy['BS_l Senior debt'] = df_copy['Debt Senior debt balance (EoP)']
	df_copy['BS_l Equity'] = df_copy['arr_equity_drawn'].cumsum()-df_copy['Distr Share capital reimbursement']

	df_copy['BS_l Total liabilities'] = df_copy['BS_l Equity'] + df_copy['BS_l Senior debt'] + df_copy['BS_l Retained earnings']

	df_copy['arr_debt_service_repayment'] = -df_copy['Debt Senior debt principal repayment']
	df_copy['Debt Debt service'] = (df_copy['arr_sizing_debt_interest_operations']-df_copy['Debt Senior debt principal repayment'])
	df_copy['arr_ratios_DSCR'] = np.divide(df_copy['arr_sizing_CFADS'],df_copy['Debt Debt service'], out=np.zeros_like(df_copy['arr_sizing_CFADS']), where=df_copy['Debt Debt service']!=0)

	df_copy['arr_sponsors_cash_flows'] = -df_copy['arr_equity_drawn']+df_copy['Distr Dividends paid']+df_copy['Distr Share capital reimbursement']
	df_copy['Equity injections and reimbursement'] = -df_copy['arr_equity_drawn']+df_copy['Distr Share capital reimbursement']

	df_copy['FP_s Senior debt'] = df_copy['Debt Senior debt drawdowns']
	df_copy['FP_s Equity injections'] = df_copy['arr_equity_drawn']
	df_copy['FP_s Total sources'] = df_copy['FP_s Senior debt']+df_copy['FP_s Equity injections']

	df_copy['Audit Financing plan balanced'] = df_copy['FP_u Total uses']-df_copy['FP_s Total sources']
	df_copy['Audit Balance sheet balanced'] = df_copy['BS_a Total assets']-df_copy['BS_l Total liabilities']

	return df_copy 

def optimise_devfee(request,debt_amount_DSCR,total_costs_wo_devfee):

	dev_fee_switch = int(request.POST['devfee_choice'])
	gearing_max = float(request.POST['debt_gearing_max'])/100

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

def array_elec_prices(arr_end_period_year,dic_price_elec):
	electricity_prices = []
	
	for row in arr_end_period_year:
		if str(row) in dic_price_elec.keys():
			electricity_prices.append(dic_price_elec[str(row)])
	
	return electricity_prices


def array_seasonality(arr_start_period,arr_end_period,seasonality):
	data = {'start':arr_start_period,
			'end':arr_end_period}

	df = pd.DataFrame(data)

	df_seasonality_result = pd.DataFrame(columns=arr_end_period)

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

	df_seasonality_result=df_seasonality_result.mul(seasonality, axis=0)
	arr_time_seasonality = df_seasonality_result.sum(axis=0)
	arr_time_seasonality = arr_time_seasonality.values.tolist()

	return arr_time_seasonality

"""def xnpv(rate, values, dates):
	'''Equivalent of Excel's XNPV function.

	>>> from datetime import date
	>>> dates = [date(2010, 12, 29), date(2012, 1, 25), date(2012, 3, 8)]
	>>> values = [-10000, 20, 10100]
	>>> xnpv(0.1, values, dates)
	-966.4345...
	'''
	if rate <= -1.0:
		return float('inf')
	d0 = dates[0]    # or min(dates)
	return sum([ vi / (1.0 + rate)**((di - d0).days / 365.0) for vi, di in zip(values, dates)])

def xirr(values, dates):
	'''Equivalent of Excel's XIRR function.

	>>> from datetime import date
	>>> dates = [date(2010, 12, 29), date(2012, 1, 25), date(2012, 3, 8)]
	>>> values = [-10000, 20, 10100]
	>>> xirr(values, dates)
	0.0100612...
	'''
	try:
		return scipy.optimize.newton(lambda r: xnpv(r, values, dates), 0.0)
	except RuntimeError:    # Failed to converge?
		return scipy.optimize.brentq(lambda r: xnpv(r, values, dates), -1.0, 1e10)"""

"""UNUSED"""


def end_period(request,start_period,periodicity_switch,latest_date):
	periodicity = int(request.POST['periodicity'])	
	start_period_plus_periodicity = start_period + relativedelta(months=+int(periodicity)-1)*periodicity_switch
	end_period = min(latest_date,start_period_plus_periodicity.replace(day = calendar.monthrange(start_period_plus_periodicity.year, start_period_plus_periodicity.month)[1]))
	return end_period


def end_date_period(period):	
	end_date_period = period.replace(day = calendar.monthrange(period.year, period.month)[1])
	return end_date_period

def end_date_period_test(period):	
	end_date_period = period.replace(day = calendar.monthrange(period.year, period.month)[1]) + datetime.timedelta(days=1)
	return end_date_period

def first_day_previous_month(date):
	first_day_previous_month = date.replace(day=1) + relativedelta(months=-1)
	return first_day_previous_month

def first_day_month(date):
	first_day_month = date.replace(day=1)
	return first_day_month

def first_day_next_month(date):
	first_day_next_month = date.replace(day=1) + relativedelta(months=1)
	return first_day_next_month

def first_day_next_month(date,periodicity):
	first_day_next_month = date.replace(day=1) + relativedelta(months=periodicity) + datetime.timedelta(days=-1)
	return first_day_next_month

def previous_end_date_period(period):	
	end_date_period = period + relativedelta(months=-int(1))
	end_date_period.replace(day = calendar.monthrange(end_date_period.year, end_date_period.month)[1])
	return end_date_period

def days_in_period(start_period,end_period):
	days_in_period = (end_period + datetime.timedelta(days=1) - start_period).days
	return days_in_period

def years_in_period(start_period,end_period):
	days_in_period = (end_period + datetime.timedelta(days=1) - start_period).days
	days_year = 366 if calendar.isleap(end_period.year) else 365
	years_in_period = days_in_period/days_year
	return years_in_period

def array_time_array(start_date, end_date, start_period, end_period):
	days_to_consider_in_period = max(0,((min(end_date,end_period)-max(start_date,start_period)).days+1))
	days_year = 366 if calendar.isleap(end_period.year) else 365
	years_of_timeline = days_to_consider_in_period/days_year
	return years_of_timeline

def interests(debt_drawn, interest_rate, days_in_period):
	interests = debt_drawn*interest_rate*days_in_period/360
	return interests

def commitment_fee(amount_available, commitment_fee_rate, days_in_period):
	commitment_fee = amount_available*commitment_fee_rate*days_in_period/360
	return commitment_fee				

def days_in_month(start_date, end_date):

	dates_in_period = pd.date_range(start=start_date, end=end_date).values.astype('datetime64[D]').tolist()
	arr_time_days_in_period_per_months = np.array([])
	arr_time_days_in_period = np.array([])
	days_in_month = 0

	for i in range(1,13):
		count = 0
		try:
			for value in dates_in_period:
				
				if value.month == i:
					count += 1
					days_in_month = calendar.monthrange(value.year, value.month)[1]
			
			arr_time_days_in_period_per_months = np.append(arr_time_days_in_period_per_months,count/days_in_month)

		except ZeroDivisionError:

			arr_time_days_in_period_per_months = np.append(arr_time_days_in_period_per_months,0)

	return arr_time_days_in_period_per_months





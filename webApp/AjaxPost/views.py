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
		
			seasonality = import_seasonality(request)

			""" Construction costs inputs """

			arr_construction_costs = import_construction_costs(request)

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

			inp_debt_gearing_max = float(request.POST['debt_gearing_max'])/100

			""" Arrays instanciation """

			df = pd.DataFrame()

			""" Create date series """

			arr_start_period,arr_end_period = create_period_series(request)

			df = create_timeline(df,arr_start_period,arr_end_period)
			df = create_flags_operations(df,COD,arr_start_period,arr_end_period,construction_start,construction_end,end_of_operations,liquidation)
			df = create_timeline_contract(df,request,arr_start_period,arr_end_period)

			arr_end_period_year = arr_end_period.dt.year
			df['FlagMod Year'] = arr_end_period_year


			arr_date_start_elec_index = array_time(arr_start_period,date_price_elec_index_start,end_of_operations)


			arr_date_end_elec_index = array_time(arr_end_period,date_price_elec_index_start,end_of_operations)

			arr_date_start_opex_index = array_time(arr_start_period,date_opex_index_start,end_of_operations)
			
			arr_date_end_opex_index = array_time(arr_end_period,date_opex_index_start,end_of_operations)

			""" Create flag series """

			df['Mkt_i Indexation period'] = array_flag(arr_date_end_elec_index,date_price_elec_index_start,arr_date_start_elec_index,end_of_operations)
			df['Opex Indexation period'] = array_flag(arr_date_end_opex_index,date_opex_index_start,arr_date_start_opex_index,end_of_operations)
			df['FlagFin Amortisation period'] = (arr_end_period<=pd.to_datetime(debt_maturity)).astype(int)*df['FlagOp Operations']


			df['Mkt_i Indexation start date'] = pd.to_datetime(arr_date_start_elec_index).dt.strftime('%d/%m/%Y')
			df['Mkt_i Indexation start date'] = df['Mkt_i Indexation start date']*df['Mkt_i Indexation period']

			df['Mkt_i Indexation end date'] = pd.to_datetime(arr_date_end_elec_index).dt.strftime('%d/%m/%Y')
			df['Mkt_i Indexation end date'] = df['Mkt_i Indexation end date']*df['Mkt_i Indexation period']


			df['Opex Indexation start date'] = pd.to_datetime(arr_date_start_opex_index).dt.strftime('%d/%m/%Y')
			df['Opex Indexation end date'] = pd.to_datetime(arr_date_end_opex_index).dt.strftime('%d/%m/%Y')
			df['Opex Indexation start date'] = df['Opex Indexation start date']*df['Opex Indexation period']
			df['Opex Indexation end date'] = df['Opex Indexation end date']*df['Opex Indexation period']


			""" Create time series """

			df['FlagMod Days in period'] = array_days(arr_end_period,arr_start_period,1)
			df['FlagOftk_t Percentage in contract period']=df['FlagOftk_t Days in contract period']/df['FlagMod Days in period']

			df['Mkt_i Indexation (days)'] = array_days(arr_date_end_elec_index,arr_date_start_elec_index,df['Mkt_i Indexation period'])
			df['Opex Indexation (days)'] = array_days(arr_date_end_opex_index,arr_date_start_opex_index,df['Opex Indexation period'])

			df['FlagMod Days in year'] = arr_end_period.dt.is_leap_year*366 + (1-arr_end_period.dt.is_leap_year)*365
			df['FlagMod Years in period'] = df['FlagMod Days in period']/df['FlagMod Days in year']

			df['FlagOp Years during operations'] = df['FlagMod Years in period']*df['FlagOp Operations']
			df['FlagOp Years from COD (EoP)'] = df['FlagOp Years during operations'].cumsum()
			df['FlagOp Years from COD (BoP)'] = df['FlagOp Years from COD (EoP)']-df['FlagOp Years during operations']
			df['FlagOp Years from COD (avg.)'] = (df['FlagOp Years from COD (BoP)']+df['FlagOp Years from COD (EoP)'])/2

			df['FlagOftk_i Years from indexation start date']=(df['FlagOftk_i Indexation (days)']/df['FlagMod Days in year']).cumsum()
			df['Mkt_i Years from indexation start date']=(df['Mkt_i Indexation (days)']/df['FlagMod Days in year']).cumsum()
			df['Opex Years from indexation start date']=(df['Opex Indexation (days)']/df['FlagMod Days in year']).cumsum()

			df = calculate_production(df,request,arr_start_period,arr_end_period,seasonality)
			df = calculate_indexation(df,request)
			df = calculate_prices(df,request,arr_end_period_year,dic_price_elec)
			df = calculate_revenues(df)
			df = calculate_opex(df,request)
			df = calculate_EBITDA(df)

			df['FP_u Construction costs'] = np.hstack([arr_construction_costs,np.zeros(df['FlagOp Operations'].size-arr_construction_costs.size)])*df['FlagCons Construction']
			df['arr_construction_costs_cumul'] = df['FP_u Construction costs'].cumsum()
			construction_costs = max(df['arr_construction_costs_cumul'])

			df,target_debt_amount,optimised_devfee,debt_amount_not_converged,total_costs = instantiate_variables(df)
			

			while debt_amount_not_converged or debt_sculpting_not_converged:
				
				debt_amount = target_debt_amount
				equity_amount= total_costs-debt_amount
				df['Debt_b Principal repayment'] = -df['Sizing Debt repayment target']

				df = calculate_debt(df,request,debt_amount,total_costs,equity_amount)

				df = calculate_depreciation(df,request,construction_costs,optimised_devfee)
				df = calculate_financing_plan(df)
				df = calculate_income_statement(df,request)
				df = calculate_cash_flow_statement(df)
				

				df = calculate_debt_sizing(df,request)

				debt_amount_DSCR = npv(df['Sizing Target debt service'],df['Sizing Cumulative discount factor'])

				interests_during_construction = sum(df['FP_u Interests during construction'])
				upfront_fee = sum(df['Debt_i Arrangement fee (upfront)'])
				commitment_fee= sum(df['Debt_i Commitment fees'])


				optimised_devfee = optimise_devfee(request,debt_amount_DSCR,construction_costs,interests_during_construction)
				total_costs = construction_costs+interests_during_construction+optimised_devfee+upfront_fee+commitment_fee

				debt_amount_gearing = total_costs*inp_debt_gearing_max
				target_debt_amount = min(debt_amount_DSCR,debt_amount_gearing)

				devfee_paid_FC = float(request.POST['devfee_paid_FC'])
				devfee_paid_COD = float(request.POST['devfee_paid_COD'])

				df['FP_u Development fee'] = devfee_paid_FC * optimised_devfee * df['FlagCons Construction start'] + devfee_paid_COD * optimised_devfee * df['FlagCons Construction end']
				df['arr_development_fee_cumul'] = df['FP_u Development fee'].cumsum()

				df = calculate_debt_sculpting(df)

				""" Convergence tests """

				debt_amount_not_converged = abs(debt_amount-target_debt_amount)>0
				debt_sculpting_not_converged = sum(df['arr_sculpting_test'])!=0

			""" Distribution account """

			df = calculate_distribution_account(df)
			
			""" Balance sheet """		

			df['Distr Share capital reimbursement'] = df['Distr Distribution account balance (BoP)']*df['FlagOp Liquidation end']
			df['Distr Distribution account balance (EoP)'] = df['Distr Distribution account balance (EoP)']-df['Distr Share capital reimbursement']
			
			df = calculate_equity(df)
			df = calculate_balance_sheet(df)

			df = create_IRR_curve(df,arr_end_period)

			""" Outputs """
		
			debt_constraint = determine_debt_constraint(debt_amount_DSCR,debt_amount_gearing)
			table_uses = create_table_uses(construction_costs,optimised_devfee,interests_during_construction,upfront_fee,commitment_fee,total_costs)
			table_sources = create_table_sources(df,debt_amount)
			table_debt = create_table_debt(df,debt_amount,debt_constraint,total_costs)
			table_projectIRR = create_table_projectIRR(df,arr_end_period)
			table_equity = create_table_equity(df,construction_start,arr_end_period)
			table_financing_terms = create_table_financing_terms(request,df,construction_start,debt_amount)
			table_audit = create_table_audit(df)

			df = calculate_gearing_financing_plan(df)

			df_sum = df.apply(pd.to_numeric, errors='coerce').sum()

			COD_formatted,end_of_operations_formatted,liquidation_formatted,debt_maturity_formatted = format_dates(COD,end_of_operations,liquidation,debt_maturity)

			sum_seasonality = np.sum(seasonality)
			sum_seasonality = (sum_seasonality / np.sum(seasonality)) * 100
			sum_construction_costs = np.sum(arr_construction_costs)


			data_dump_sidebar = np.array([
				COD_formatted,
				end_of_operations_formatted,
				sum_seasonality,
				sum_construction_costs,
				liquidation_formatted,
				debt_maturity_formatted,
				])

			df = reorder_columns(df)

			return JsonResponse({

				"df":df.to_dict(),
				"df_sum":df_sum.to_dict(),
				"table_projectIRR":table_projectIRR.to_dict(),

				"table_debt":table_debt.to_dict(),
				"table_equity":table_equity.to_dict(),
				"table_uses":table_uses.to_dict(),
				"table_sources":table_sources.to_dict(),
				"table_audit":table_audit.to_dict(),
				"table_financing_terms":table_financing_terms.to_dict(),

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

def create_period_series(request):

	periodicity = int(request.POST['periodicity'])
	liquidation = int(request.POST['liquidation'])
	start_construction = request.POST['start_construction']
	construction_end = request.POST['end_construction']
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
	
	arr_start_period = pd.concat([start_period_construction,start_period_operations,start_period_liquidation], ignore_index=True)

	first_day_start_operations_plus_freq = first_day_next_month(COD,periodicity)
	last_day_end_operations_plus_freq = first_day_next_month(end_of_operations,periodicity)
	first_day_start_liquidation_plus_freq = first_day_next_month(first_day_start_liquidation,periodicity)
	last_day_end_liquidation_plus_freq = first_day_next_month(end_liquidation,periodicity)

	#Période mensuelle pendant le plan de financement puis selon la périodicité
	end_period_construction = pd.Series(pd.date_range(first_day_start_construction,last_day_construction_end, freq='M')).clip(upper=pd.Timestamp(formatted_construction_end))
	end_period_operations = pd.Series(pd.date_range(first_day_start_operations_plus_freq, last_day_end_operations_plus_freq,freq=freq_end_period)).clip(upper=pd.Timestamp(end_of_operations))
	end_period_liquidation= pd.Series(pd.date_range(first_day_start_liquidation_plus_freq, last_day_end_liquidation_plus_freq,freq=freq_end_period)).clip(upper=pd.Timestamp(end_liquidation))
	
	arr_end_period = pd.concat([end_period_construction,end_period_operations,end_period_liquidation], ignore_index=True)
	
	return arr_start_period, arr_end_period

def create_price_elec_dict(request):
	
	choice = int(request.POST['price_elec_choice'])

	construction_end = datetime.datetime.strptime(request.POST['end_construction'], "%Y-%m-%d").date()
	COD = construction_end + datetime.timedelta(days=1)
	COD_year = int(COD.year)

	construction_end_year = construction_end.year

	years = [str(year) for year in range(construction_end_year, construction_end_year+30)]

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


def reorder_columns(df):

	df_copy = df.copy()
	# Define a dictionary with set names as keys and ordered columns as values
	ordered_columns_dict = {
		'set1': ['Debt_a Debt available (BoP)', 'Debt_a Debt drawdowns', 'Debt_a Debt available (EoP)'],
		'set2': ['Debt_b Senior debt balance (BoP)', 'Debt_b Debt drawdowns', 'Debt_b Principal repayment', 'Debt_b Senior debt balance (EoP)'],
		'set3': ['Debt_i Arrangement fee (upfront)', 'Debt_i Commitment fees', 'Debt_i Debt interests'],
		'set4': ['Distr Distribution account balance (BoP)', 'Distr Transfers to the distribution account', 'Distr Dividends paid', 'Distr Share capital reimbursement', 'Distr Distribution account balance (EoP)'],
		'set5': ['RE_b Retained earnings (BoP)', 'RE_b Net income', 'RE_b Dividends declared', 'RE_b Retained earnings (EoP)'],
		'set6': ['FP_u Construction costs', 'FP_u Development fee', 'FP_u Arrangement fee (upfront)', 'FP_u Commitment fees', 'FP_u Interests during construction', 'FP_u Total uses'],
		'set7': ['Sizing CFADS','Sizing Target DSCR', 'Sizing Target debt service', 'Sizing Average interest rate', 'Sizing Discount factor', 'Sizing Cumulative discount factor', 'Sizing Interests during operations', 'Sizing Debt repayment target'],
		'set8': ['FlagCons Construction start','FlagCons Construction', 'FlagCons Construction end'],
		'set9': ['FlagOp Operations','FlagOp Years during operations', 'FlagOp Years from COD (BoP)','FlagOp Years from COD (EoP)','FlagOp Years from COD (avg.)','FlagOp Seasonality','FlagOp Liquidation','FlagOp Liquidation end'],
		'set10': ['FlagOftk_i Indexation period'],
		'set11': ['Mkt_i Indexation period','Mkt_i Indexation start date'],
		'set12': ['FlagOftk_t Contract period'],
		'set13': ['Eqt Share Capital (BoP)','Eqt Share Capital injections','Eqt Share capital reimbursement','Eqt Share Capital (EoP)'],




	}

	remaining_columns = [col for col in df_copy.columns if col not in ordered_columns_dict.values()]
	new_columns = []

	# Append ordered columns from each set to the new_columns list
	for ordered_columns in ordered_columns_dict.values():
		new_columns += ordered_columns

	new_columns += remaining_columns

	df_copy = df_copy[new_columns]

	return df_copy


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
	seasonality = np.zeros(12)
	for i in range(1, 13):
		key = 'seasonality_m{}'.format(i)
		seasonality[i - 1] = float(request.POST[key])
	return seasonality

def import_construction_costs(request):
	construction_costs = np.zeros(12)
	for i in range(1, 13):
		key = 'costs_m{}'.format(i)
		construction_costs[i - 1] = float(request.POST[key])
	return construction_costs


def instantiate_variables(df):

	target_debt_amount = 100
	total_costs=100
	optimised_devfee = 0
	df['Sizing Debt repayment target'] = -100
	df['RE_c Distributable profit'] = 0
	df['RE_c Cash available for dividends'] = 0
	df['FP_u Development fee']= 0

	df['FP_u Total uses'] = df['FP_u Construction costs']

	debt_amount_not_converged = True

	return df,target_debt_amount,optimised_devfee,debt_amount_not_converged,total_costs

def create_timeline(df,arr_start_period,arr_end_period):
	df_copy = df.copy()
	df_copy['Date Period start'] = pd.to_datetime(arr_start_period).dt.strftime('%d/%m/%Y')
	df_copy['Date Period end'] = pd.to_datetime(arr_end_period).dt.strftime('%d/%m/%Y')


	return df_copy 





def calculate_gearing_financing_plan(df):
	df_copy = df.copy()

	df_copy['Gearing during financing plan']=df_copy['FP_s Senior debt'].cumsum()/(df_copy['FP_s Equity injections'].cumsum()+df_copy['FP_s Senior debt'].cumsum())
	
	return df_copy 


def create_flags_operations(df,COD,arr_start_period,arr_end_period,construction_start,construction_end,end_of_operations,liquidation):
	df_copy = df.copy()
	df_copy['FlagOp Operations'] = ((arr_end_period>pd.to_datetime(COD))*(arr_start_period<pd.to_datetime(end_of_operations))).astype(int)
	df_copy['FlagOp Liquidation'] = (arr_end_period>pd.to_datetime(end_of_operations + datetime.timedelta(days=1))).astype(int)
	df_copy['FlagOp Liquidation end'] = (arr_end_period==pd.to_datetime(liquidation)).astype(int)

	df_copy['FlagCons Construction'] = (arr_start_period<pd.to_datetime(construction_end)).astype(int)
	df_copy['FlagCons Construction end'] = (arr_end_period==pd.to_datetime(construction_end)).astype(int)
	df_copy['FlagCons Construction start'] = (arr_start_period==pd.to_datetime(construction_start)).astype(int)

	return df_copy 

def create_timeline_contract(df,request,arr_start_period,arr_end_period):
	df_copy = df.copy()

	start_contract = request.POST['start_contract']
	end_contract = request.POST['end_contract']

	contract_index_start_date = request.POST['contract_indexation_start_date']
	date_contract_index_start = datetime.datetime.strptime(contract_index_start_date, "%Y-%m-%d").date()

	arr_date_start_contract_period = array_time(arr_start_period,start_contract,end_contract)
	arr_date_end_contract_period = array_time(arr_end_period,start_contract,end_contract)

	df_copy['FlagOftk_t Contract start date'] = pd.to_datetime(arr_date_start_contract_period).dt.strftime('%d/%m/%Y')
	df_copy['FlagOftk_t Contract end date'] = pd.to_datetime(arr_date_end_contract_period).dt.strftime('%d/%m/%Y')



	arr_date_start_contract_index_period = array_time(arr_start_period,date_contract_index_start,end_contract)
	arr_date_end_contract_index_period = array_time(arr_end_period,date_contract_index_start,end_contract)



	df_copy['FlagOftk_t Contract period'] = array_flag(arr_date_end_contract_period,start_contract,arr_date_start_contract_period,end_contract)
	df_copy['FlagOftk_t Days in contract period'] = array_days(arr_date_end_contract_period,arr_date_start_contract_period,df_copy['FlagOftk_t Contract period'])

	df_copy['FlagOftk_i Indexation start date'] = pd.to_datetime(arr_date_start_contract_index_period).dt.strftime('%d/%m/%Y')
	df_copy['FlagOftk_i Indexation end date'] = pd.to_datetime(arr_date_end_contract_index_period).dt.strftime('%d/%m/%Y')

	df_copy['FlagOftk_i Indexation period'] = array_flag(arr_date_end_contract_index_period,date_contract_index_start,arr_date_start_contract_index_period,end_contract)
	df_copy['FlagOftk_i Indexation (days)'] = array_days(arr_date_end_contract_index_period,arr_date_start_contract_index_period,df_copy['FlagOftk_i Indexation period'])

	df_copy['FlagOftk_t Contract start date']=df_copy['FlagOftk_t Contract start date']*df_copy['FlagOftk_t Contract period']
	df_copy['FlagOftk_t Contract end date']=df_copy['FlagOftk_t Contract end date']*df_copy['FlagOftk_t Contract period']

	df_copy['FlagOftk_i Indexation start date']=df_copy['FlagOftk_i Indexation start date']*df_copy['FlagOftk_i Indexation period']
	df_copy['FlagOftk_i Indexation end date']=df_copy['FlagOftk_i Indexation end date']*df_copy['FlagOftk_i Indexation period']



	
	return df_copy 

def calculate_production(df,request,arr_start_period,arr_end_period,seasonality):
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
	df_copy['Prod Capacity degradation factor'] = 1/(1+degradation_factor)**df_copy['FlagOp Years from COD (avg.)']
	df_copy['Prod Capacity after degradation'] = df_copy['Prod Capacity before degradation']*df_copy['Prod Capacity degradation factor']
	df_copy['Prod Production'] = production/1000*df_copy['FlagOp Seasonality']*df_copy['Prod Capacity after degradation']

	return df_copy 

def create_audit_checks(df):
	
	df_copy=df.copy()

	check_balance_sheet_balanced = abs(sum(df_copy['Audit Balance sheet balanced']))<0.001
	check_financing_plan_balanced = abs(sum(df_copy['Audit Financing plan balanced']))<0.001

	return check_balance_sheet_balanced, check_financing_plan_balanced


def determine_debt_constraint(debt_amount_DSCR,debt_amount_gearing):

	if debt_amount_DSCR>debt_amount_gearing:
		constraint = "Gearing"
	else: 
		constraint = "DSCR"

	return constraint


def create_table_uses(construction_costs,optimised_devfee,interests_during_construction,upfront_fee,commitment_fee,total_costs):

	table_table_uses = pd.DataFrame({
				"Construction costs":["{:.1f}".format(construction_costs)],
				"Development fee":["{:.1f}".format(optimised_devfee)],
				"Arrangement fee (upfront)":["{:.1f}".format(upfront_fee)],
				"Commitment fees":["{:.1f}".format(commitment_fee)],				
				"Interests during construction":["{:.1f}".format(interests_during_construction)],
				"Total":["{:.1f}".format(total_costs)],
				})
	return table_table_uses


def create_table_sources(df,debt_amount):

	equity_drawn = sum(df['arr_equity_drawn'])

	fp_sources = equity_drawn+debt_amount

	table_sources = pd.DataFrame({
				"Equity":["{:.1f}".format(equity_drawn)],
				"Debt":["{:.1f}".format(debt_amount)],
				"Total":["{:.1f}".format(fp_sources)],
				})
	return table_sources


def create_table_debt(df,debt_amount,debt_constraint,total_costs):
	
	DSCR_avg = df['arr_ratios_DSCR'].where(df['FlagFin Amortisation period']==1).mean()
	gearing_eff = (debt_amount/total_costs)


	table_debt = pd.DataFrame({
					"Debt amount":["{:.1f}".format(debt_amount)],
					"Debt constraint":[debt_constraint],
					"Effective gearing":["{:.2%}".format(gearing_eff)],
					"Average DSCR":["{:.2f}".format(DSCR_avg)+"x"],
					})
	return table_debt


def create_table_equity(df,construction_start,arr_end_period):

	irr = xirr(pd.to_datetime(arr_end_period).dt.date,df['arr_sponsors_cash_flows'])

	payback_date = find_payback_date(df)



	if isinstance(payback_date, str):
		try:
			payback_date = parser.parse(payback_date).date()
			time_difference = payback_date-construction_start
			payback_time = round(time_difference.days / 365.25, 1)
			payback_date=payback_date.strftime("%d/%m/%Y")
		except ParserError:
			payback_date = "error"
			payback_time = "error"
	else: 
			payback_date = "error"
			payback_time = "error"		



	table_equity = pd.DataFrame({
				"Equity IRR":["{:.2%}".format(irr)],
				"Payback date":[(payback_date)],
				"Payback time (from Financial Close)":[(payback_time)],

				})

	return table_equity

def create_table_projectIRR(df,arr_end_period):


	df['Project IRR cashflows pre-tax'] = -df['FP_u Total uses']+df['IS EBITDA']
	df['Project IRR cashflows post-tax'] = df['Project IRR cashflows pre-tax']+df['IS Corporate income tax']

	project_irr_pre_tax = xirr(pd.to_datetime(arr_end_period).dt.date,df['Project IRR cashflows pre-tax'])
	project_irr_post_tax = xirr(pd.to_datetime(arr_end_period).dt.date,df['Project IRR cashflows post-tax'])


	table_projectIRR = pd.DataFrame({
				"Project IRR (pre-tax)":["{:.2%}".format(project_irr_pre_tax)],
				"Project IRR (post-tax)":["{:.2%}".format(project_irr_post_tax)],
				})

	return table_projectIRR





def find_payback_date(df):
	payback_date = df.loc[df['Cumulative Equity for payback'] >= 0, 'Date Period end'].min()
	return payback_date

def find_last_debt_payment_date(df):
	last_payment_date = df.loc[df['Debt_b Senior debt balance (EoP)'] < 0.01, 'Date Period start'].min()
	return last_payment_date

def find_last_equity_payment_date(df):
	last_payment_date = df.loc[df['Eqt Share Capital (EoP)'] < 0.01, 'Date Period end'].min()
	return last_payment_date


def create_table_financing_terms(request,df,construction_start,debt_amount):

	inp_debt_gearing_max = request.POST['debt_gearing_max']+"%"
	target_DSCR = request.POST['debt_target_DSCR']+"x"

	inp_injection = request.POST['injection_choice']

	final_repayment_date_debt=find_last_debt_payment_date(df)
	if final_repayment_date_debt == "":		
		final_repayment_date_debt="Error"
		tenor_debt="Error"
	else:		
		final_repayment_date_debt=parser.parse(final_repayment_date_debt).date()- timedelta(days=1)
		time_difference_debt = final_repayment_date_debt-construction_start
		tenor_debt = round(time_difference_debt.days / 365.25, 1)
		final_repayment_date_debt=final_repayment_date_debt.strftime("%d/%m/%Y")
		
	final_repayment_date_equity=find_last_equity_payment_date(df)	


	if isinstance(final_repayment_date_equity, str):
		try:
			final_repayment_date_equity = parser.parse(final_repayment_date_equity).date()
			time_difference_equity = final_repayment_date_equity-construction_start
			tenor_equity = round(time_difference_equity.days / 365.25, 1)
			final_repayment_date_equity=final_repayment_date_equity.strftime("%d/%m/%Y")
		except ParserError:
			final_repayment_date_equity = "error"
			tenor_equity = "error"
	else:
		final_repayment_date_equity = "error"
		tenor_equity = "error"
	
	
	equity_injection_choice = {"1":"Equity first", "2":"Prorata"}


	average_debt_life = sum(x * y for x, y in zip(df['FlagMod Years in period'], df['Debt_b Senior debt balance (BoP)']))/debt_amount
	average_debt_life = round(average_debt_life,1)

	table_financing_terms = pd.DataFrame({
				"":["Share capital","Senior Debt"],
				"Equity injection":[equity_injection_choice[inp_injection],"n/a"],
				"Date of final repayment":[final_repayment_date_equity,final_repayment_date_debt],
				"Tenor (door-to-door)":[tenor_equity,tenor_debt],
				"Average life (from Financial Close)":["n/a",average_debt_life],
				"Maximum gearing":["n/a",inp_debt_gearing_max],
				"Minimum DSCR":["n/a",target_DSCR],
				})

	return table_financing_terms



def create_table_audit(df):

	check_balance_sheet_balanced,check_financing_plan_balanced = create_audit_checks(df)

	table_audit = pd.DataFrame({
		"Balance sheet":[check_balance_sheet_balanced],
		"Financing plan":[check_financing_plan_balanced],
		})

	return table_audit

def calculate_indexation(df,request):
	df_copy = df.copy()
	
	index_rate_merchant = float(request.POST['price_elec_indexation'])/100
	index_rate_contract = float(request.POST['contract_indexation'])/100
	index_rate_opex = float(request.POST['opex_indexation'])/100

	df_copy['Mkt_i Indexation'] = array_index(index_rate_merchant,df_copy['Mkt_i Years from indexation start date'])
	df_copy['FlagOftk_i Indexation'] = array_index(index_rate_contract,df_copy['FlagOftk_i Years from indexation start date'])
	df_copy['Opex Indexation'] = array_index(index_rate_opex,df_copy['Opex Years from indexation start date'])
	return df_copy 

def calculate_prices(df,request,arr_end_period_year,dic_price_elec):
	df_copy = df.copy()

	price_contract = float(request.POST['contract_price'])

	df_copy['Price Electricity market price before indexation'] = array_elec_prices(arr_end_period_year,dic_price_elec)

	df_copy['Price Electricity market price after indexation'] = df_copy['Price Electricity market price before indexation']*df_copy['Mkt_i Indexation']
	df_copy['Price Contract price before indexation'] = price_contract*df['FlagOftk_t Contract period']
	df_copy['Price Contract price after indexation'] = df_copy['Price Contract price before indexation']*df_copy['FlagOftk_i Indexation']
	return df_copy 

def calculate_revenues(df):
	df_copy = df.copy()
	df_copy['IS Contracted revenues'] = df_copy['Price Contract price after indexation']*df_copy['Prod Production']*df_copy['FlagOftk_t Percentage in contract period']/1000
	df_copy['IS Uncontracted electricity revenues'] = df_copy['Price Electricity market price after indexation']*df_copy['Prod Production']*(1-df_copy['FlagOftk_t Percentage in contract period'])/1000
	df_copy['IS Total revenues'] = df_copy['IS Contracted revenues']+df_copy['IS Uncontracted electricity revenues']
	return df_copy 

def calculate_opex(df,request):
	df_copy = df.copy()
	
	opex = float(request.POST['opex'])

	df_copy['IS Operating expenses'] = -opex*df_copy['Opex Indexation']*df_copy['FlagOp Years during operations']
	return df_copy 

def calculate_EBITDA(df):
	df_copy = df.copy()
	df_copy['IS EBITDA'] = df_copy['IS Total revenues']+df_copy['IS Operating expenses']
	df_copy['arr_EBITDA_margin'] = np.divide(df_copy['IS EBITDA'],df_copy['IS Total revenues'], out=np.zeros_like(df_copy['IS EBITDA']), where=df_copy['IS Total revenues']!=0)*100
	return df_copy 

def calculate_debt(df,request,debt_amount,total_costs,equity_amount):
	df_copy = df.copy()

	inp_debt_gearing_max = float(request.POST['debt_gearing_max'])/100
	inp_upfront_fee = float(request.POST['debt_upfront_fee'])/100
	inp_commitment_fee = float(request.POST['debt_commitment_fee'])/100

	inp_injection = int(request.POST['injection_choice'])


	inp_all_in_interest = np.array([
		float(request.POST['debt_margin']),
		float(request.POST['debt_swap_rate']),
		float(request.POST['debt_swap_margin']),
		float(request.POST['debt_reference_rate_buffer']),
		])

	inp_debt_interest_rate = np.sum(inp_all_in_interest)/100

	gearing_eff = (debt_amount/total_costs)


	if inp_injection == 2:
		df_copy['Cumulative total uses'] = df_copy['FP_u Total uses'].cumsum()
		df_copy['Cumulative senior debt drawdowns'] = (df_copy['Cumulative total uses'] * gearing_eff).clip(upper=debt_amount)
		df_copy['Debt_b Debt drawdowns'] = np.ediff1d(df_copy['Cumulative senior debt drawdowns'], to_begin=df_copy['Cumulative senior debt drawdowns'][0])
		df_copy['arr_equity_drawn'] = df_copy['FP_u Total uses'] - df_copy['Debt_b Debt drawdowns']
	elif inp_injection == 1:
		df_copy['Cumulative total uses'] = df_copy['FP_u Total uses'].cumsum()
		df_copy['Cumulative equity drawdowns'] = df_copy['Cumulative total uses'].clip(upper=equity_amount)
		df_copy['arr_equity_drawn'] = np.ediff1d(df_copy['Cumulative equity drawdowns'], to_begin=df_copy['Cumulative equity drawdowns'][0])
		df_copy['Debt_b Debt drawdowns'] = df_copy['FP_u Total uses'] - df_copy['arr_equity_drawn']
		df_copy['Cumulative senior debt drawdowns'] = df_copy['Debt_b Debt drawdowns'].cumsum() 



	df_copy['Debt_b Senior debt balance (EoP)'] = (df_copy['Cumulative senior debt drawdowns']+df_copy['Debt_b Principal repayment'].cumsum()).clip(lower=0)
	df_copy['Debt_b Senior debt balance (BoP)'] = np.roll(df_copy['Debt_b Senior debt balance (EoP)'], 1)

	df_copy['Debt_i Debt interests'] = df_copy['Debt_b Senior debt balance (BoP)']*inp_debt_interest_rate*df_copy['FlagMod Days in period']/360
	df_copy['Sizing Interests during operations'] = df_copy['Debt_i Debt interests']*df_copy['FlagFin Amortisation period']
	df_copy['Interests during construction'] = df_copy['Debt_i Debt interests']*df_copy['FlagCons Construction']
	df_copy['Debt_i Arrangement fee (upfront)'] = df_copy['FlagCons Construction start']*debt_amount*inp_upfront_fee
	df_copy['Debt_a Debt available (BoP)'] = (debt_amount-df_copy['Debt_b Senior debt balance (BoP)'])*df_copy['FlagCons Construction']
	df_copy['Debt_a Debt drawdowns'] = df_copy['Debt_b Debt drawdowns']
	df_copy['Debt_a Debt available (EoP)'] = df_copy['Debt_a Debt available (BoP)'] - df_copy['Debt_a Debt drawdowns']


	df_copy['Debt_i Commitment fees'] = df_copy['Debt_a Debt available (BoP)']*inp_commitment_fee*df_copy['FlagMod Days in period']/360

	df_copy['arr_capitalised_costs_cumul'] = df_copy['Interests during construction'].cumsum()+df_copy['Debt_i Arrangement fee (upfront)'].cumsum()+df_copy['Debt_i Commitment fees'].cumsum()

	return df_copy 

def calculate_equity(df):

	df_copy = df.copy()

	df_copy['Eqt Share Capital injections'] = df_copy['CF_fi Equity injections']
	df_copy['Eqt Share capital reimbursement'] = -df['Distr Share capital reimbursement']
	df_copy['Eqt Share Capital (EoP)'] = df_copy['Eqt Share Capital injections'].cumsum() + df_copy['Eqt Share capital reimbursement'].cumsum()
	df_copy['Eqt Share Capital (BoP)'] = np.roll(df_copy['Eqt Share Capital (EoP)'], 1)

	return df_copy 

def calculate_depreciation(df,request,construction_costs,optimised_devfee):
	df_copy = df.copy()

	length_operations = int(request.POST['operating_life'])
	
	debt_capitalised_interest = max(df_copy['arr_capitalised_costs_cumul'])
	df_copy['IS Depreciation'] = -(construction_costs+debt_capitalised_interest+optimised_devfee)*df_copy['FlagOp Years during operations']/length_operations

	return df_copy 

def calculate_financing_plan(df):
	df_copy = df.copy()


	df_copy['FP_u Interests during construction'] = df_copy['Debt_i Debt interests']*df_copy['FlagCons Construction']
	df_copy['FP_u Total uses'] = df_copy['FP_u Construction costs']+df_copy['FP_u Interests during construction']+df_copy['FP_u Development fee']+df_copy['Debt_i Arrangement fee (upfront)']+df_copy['Debt_i Commitment fees']
	df_copy['FP_u Arrangement fee (upfront)'] = df_copy['Debt_i Arrangement fee (upfront)']
	df_copy['FP_u Commitment fees'] = df_copy['Debt_i Commitment fees']
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

		irr_values.append(max(irr,0,0))

	df_copy['IRR curve'] = irr_values
	return df_copy 


def calculate_income_statement(df,request):
	df_copy = df.copy()

	income_tax_rate = float(request.POST['corporate_income_tax'])/100

	df_copy['IS EBIT'] = df_copy['IS EBITDA']+df_copy['IS Depreciation']
	df_copy['IS Interests'] = -df_copy['Sizing Interests during operations']
	df_copy['IS EBT'] = df_copy['IS EBIT']+df_copy['IS Interests']
	df_copy['IS Corporate income tax'] = -income_tax_rate*df_copy['IS EBT'].clip(lower=0)
	df_copy['IS Net income'] = df_copy['IS EBT']+df_copy['IS Corporate income tax']
	return df_copy 


def calculate_cash_flow_statement(df):
	df_copy = df.copy()
	df_copy['CF_op EBITDA'] = df_copy['IS EBITDA']
	df_copy['CF_op Corporate income tax'] = df_copy['IS Corporate income tax']
	df_copy['CF_op Cash flows from operating activities'] = df_copy['CF_op EBITDA']+df_copy['CF_op Corporate income tax']
	df_copy['CF_in Construction costs'] = -df_copy['FP_u Construction costs']
	df_copy['CF_in Development fee'] = -df_copy['FP_u Development fee']
	df_copy['CF_in Interests during construction'] = -df_copy['FP_u Interests during construction'] 
	df_copy['CF_in Cash flows from investing activities'] = df_copy['CF_in Construction costs']+df_copy['CF_in Interests during construction']+df_copy['CF_in Development fee']
	df_copy['CF_fi Senior debt drawdowns'] = df_copy['Debt_b Debt drawdowns']
	df_copy['CF_fi Equity injections'] = df_copy['arr_equity_drawn']
	df_copy['CF_fi Arrangement fee (upfront)'] = -df_copy['Debt_i Arrangement fee (upfront)']
	df_copy['CF_fi Commitment fees'] = -df_copy['Debt_i Commitment fees']	
	df_copy['CF_fi Cash flows from financing activities'] = df_copy['CF_fi Arrangement fee (upfront)']+df_copy['CF_fi Commitment fees']+df_copy['CF_fi Senior debt drawdowns']+df_copy['CF_fi Equity injections']
	df_copy['CFADS CFADS'] = df_copy['CF_op Cash flows from operating activities']+df_copy['CF_in Cash flows from investing activities']+df_copy['CF_fi Cash flows from financing activities']
	df_copy['CFADS Senior debt interests'] = -df_copy['Sizing Interests during operations'] 
	df_copy['CFADS Senior debt principal'] = df_copy['Debt_b Principal repayment']
	return df_copy 


def calculate_debt_sizing(df,request):
	df_copy = df.copy()

	target_DSCR = float(request.POST['debt_target_DSCR'])

	df_copy['Sizing CFADS'] = df_copy['CFADS CFADS']*df_copy['FlagFin Amortisation period']
	df_copy['Sizing Target DSCR'] = (target_DSCR*df_copy['FlagFin Amortisation period']).astype(float)
	df_copy['Sizing Target debt service'] = df_copy['Sizing CFADS']/target_DSCR

	df_copy['Sizing Average interest rate'] = np.divide(df_copy['Sizing Interests during operations'],df_copy['Debt_b Senior debt balance (BoP)'],out=np.zeros_like(df_copy['Sizing Interests during operations']), where=df_copy['Debt_b Senior debt balance (BoP)']!=0)/df_copy['FlagMod Days in period']*360
	df_copy['Sizing Discount factor'] = (1/(1+(df_copy['Sizing Average interest rate']*df_copy['FlagMod Days in period']/360)))*df_copy['FlagFin Amortisation period']+df_copy['FlagCons Construction']
	df_copy['Sizing Cumulative discount factor'] = df_copy['Sizing Discount factor'].cumprod()



	return df_copy 


def calculate_debt_sculpting(df):
	df_copy = df.copy()

	cumul_debt_drawn  = max(df_copy['Cumulative senior debt drawdowns'])
	npv_CFADS = npv(df_copy['Sizing CFADS'],df_copy['Sizing Cumulative discount factor'])
	DSCR_sculpting = npv_CFADS/cumul_debt_drawn
	df_copy['Sizing Debt repayment target'] = (df_copy['Sizing CFADS']/DSCR_sculpting-df_copy['Sizing Interests during operations']).clip(lower=0)
	df_copy['arr_sculpting_test'] = df_copy['Sizing Debt repayment target']+df_copy['Debt_b Principal repayment']
	return df_copy 


def calculate_distribution_account(df):
	df_copy = df.copy()

	for i in range(100):
				
		df_copy['Distr Dividends paid'] = df_copy['RE_c Cash available for dividends'].where(df_copy['RE_c Cash available for dividends'] < df_copy['RE_c Distributable profit'], df_copy['RE_c Distributable profit'])

		df_copy['Distr Transfers to the distribution account'] = df_copy['CFADS CFADS']+df_copy['CFADS Senior debt interests']+df_copy['CFADS Senior debt principal']
		df_copy['Distr Distribution account balance (EoP)'] = df_copy['Distr Transfers to the distribution account'].cumsum()-df_copy['Distr Dividends paid'].cumsum()
		df_copy['Distr Distribution account balance (BoP)'] = df_copy['Distr Distribution account balance (EoP)']+df_copy['Distr Dividends paid']-df_copy['Distr Transfers to the distribution account']
		df_copy['RE_c Cash available for dividends'] = df_copy['Distr Distribution account balance (BoP)'] + df_copy['Distr Transfers to the distribution account']
		
		df_copy['RE_b Retained earnings (EoP)'] = df_copy['IS Net income'].cumsum()-df_copy['Distr Dividends paid'].cumsum()
		df_copy['RE_b Retained earnings (BoP)'] = df_copy['RE_b Retained earnings (EoP)']+df_copy['Distr Dividends paid']-df_copy['IS Net income']
		df_copy['RE_c Distributable profit'] = (df_copy['RE_b Retained earnings (BoP)']+df_copy['IS Net income']).clip(lower=0)

	return df_copy 


def calculate_balance_sheet(df):
	df_copy = df.copy()

	df_copy['RE_b Net income'] = df_copy['IS Net income']
	df_copy['RE_b Dividends declared'] = df_copy['Distr Dividends paid']

	df_copy['BS_a Assets'] = df_copy['arr_construction_costs_cumul']+df_copy['arr_capitalised_costs_cumul']+df_copy['arr_development_fee_cumul']+df_copy['IS Depreciation'].cumsum()
	df_copy['BS_a Distribution account balance'] = df_copy['Distr Distribution account balance (EoP)']

	df_copy['BS_a Total assets'] = df_copy['BS_a Assets']+df_copy['BS_a Distribution account balance']

	df_copy['BS_l Retained earnings'] = df_copy['RE_b Retained earnings (EoP)']
	df_copy['BS_l Senior debt'] = df_copy['Debt_b Senior debt balance (EoP)']
	df_copy['BS_l Equity'] = df_copy['arr_equity_drawn'].cumsum()-df_copy['Distr Share capital reimbursement']

	df_copy['BS_l Total liabilities'] = df_copy['BS_l Equity'] + df_copy['BS_l Senior debt'] + df_copy['BS_l Retained earnings']

	df_copy['arr_debt_service_repayment'] = -df_copy['Debt_b Principal repayment']
	df_copy['Sizing Target debt service'] = (df_copy['Sizing Interests during operations']-df_copy['Debt_b Principal repayment'])
	df_copy['arr_ratios_DSCR'] = np.divide(df_copy['Sizing CFADS'],df_copy['Sizing Target debt service'], out=np.zeros_like(df_copy['Sizing CFADS']), where=df_copy['Sizing Target debt service']!=0)

	df_copy['arr_sponsors_cash_flows'] = -df_copy['arr_equity_drawn']+df_copy['Distr Dividends paid']+df_copy['Distr Share capital reimbursement']
	df_copy['Equity injections and reimbursement'] = -df_copy['arr_equity_drawn']+df_copy['Distr Share capital reimbursement']
	df_copy['Equity dividends and reimbursement'] = df_copy['Distr Dividends paid']+df_copy['Distr Share capital reimbursement']

	df_copy['Cumulative Equity for payback']=df_copy['Equity injections and reimbursement'].cumsum()+df_copy['Distr Dividends paid'].cumsum()

	df_copy['FP_s Senior debt'] = -df_copy['Debt_b Debt drawdowns']
	df_copy['FP_s Equity injections'] = -df_copy['arr_equity_drawn']
	df_copy['FP_s Total sources'] = -df_copy['FP_s Senior debt']-df_copy['FP_s Equity injections']

	df_copy['Audit Financing plan balanced'] = df_copy['FP_u Total uses']-df_copy['FP_s Total sources']
	df_copy['Audit Balance sheet balanced'] = df_copy['BS_a Total assets']-df_copy['BS_l Total liabilities']

	return df_copy 

def optimise_devfee(request,debt_amount_DSCR,construction_costs,interests_during_construction):

	dev_fee_switch = int(request.POST['devfee_choice'])
	gearing_max = float(request.POST['debt_gearing_max'])/100

	total_costs_wo_devfee = construction_costs+interests_during_construction


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

def end_date_period(period):	
	end_date_period = period.replace(day = calendar.monthrange(period.year, period.month)[1])
	return end_date_period

def first_day_month(date):
	first_day_month = date.replace(day=1)
	return first_day_month

def first_day_next_month(date,periodicity):
	first_day_next_month = date.replace(day=1) + relativedelta(months=periodicity) + datetime.timedelta(days=-1)
	return first_day_next_month






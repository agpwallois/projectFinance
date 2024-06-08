import datetime
from dateutil.relativedelta import relativedelta
import calendar
import math
import time
import pandas as pd
import numpy as np
from functools import wraps
from dateutil import parser
from dateutil.parser import ParserError
from pyxirr import xirr




def timer_decorator(method):
	@wraps(method)
	def timed(*args, **kwargs):
		start_time = time.time()
		result = method(*args, **kwargs)
		end_time = time.time()
		elapsed_time = end_time - start_time

		# Store the result in a class attribute
		cls = args[0].__class__
		if not hasattr(cls, 'execution_times'):
			cls.execution_times = {}
		cls.execution_times[method.__name__] = elapsed_time

		print(f"Execution time of {method.__name__}: {elapsed_time:.4f} seconds")
		return result

	return timed


class InitCallerMeta(type):
	# MetaClass to call all FinancialModel methods beginning with 'init_' at instanciation
	def __call__(cls, *args, **kwargs):
		# Create the instance normally
		instance = super().__call__(*args, **kwargs)

		# Iterate over all attributes of the instance
		for attr_name in dir(instance):
			# If the attribute name starts with 'init_' and is callable, call it
			if attr_name.startswith('init_'):
				attr = getattr(instance, attr_name)
				if callable(attr):
					attr()

		return instance


class FinancialModel(metaclass=InitCallerMeta): 

	def __init__(self, request):

		self.iteration = 20
		self.periodicity = int(request.POST['periodicity'])
		
		self.construction_start = datetime.datetime.strptime(request.POST['start_construction'], "%Y-%m-%d").date()
		self.construction_end = datetime.datetime.strptime(request.POST['end_construction'], "%Y-%m-%d").date()
		self.COD = self.construction_end + datetime.timedelta(days=1)

		self.operating_life = int(request.POST['operating_life'])
		self.end_of_operations = self.construction_end + relativedelta(years=self.operating_life)
		self.liquidation = int(request.POST['liquidation'])
		self.liquidation_date = self.end_of_operations + relativedelta(months=self.liquidation)
		
		self.debt_tenor = float(request.POST['debt_tenor'])
		self.debt_maturity_date = self.construction_start + relativedelta(months=+int(self.debt_tenor*12)-1)
		self.debt_maturity = self.debt_maturity_date.replace(day = calendar.monthrange(self.debt_maturity_date.year, self.debt_maturity_date.month)[1])

		self.periods = {
			'contract': {'start': request.POST['start_contract'], 'end': request.POST['end_contract']},
			'contract_indexation': {'start': request.POST['contract_indexation_start_date'], 'end': request.POST['end_contract']},
			'merchant_indexation': {'start': request.POST['price_elec_indexation_start_date'], 'end': self.end_of_operations},
			'lease_indexation': {'start': request.POST['lease_indexation_start_date'], 'end': self.end_of_operations},
			'opex_indexation': {'start': request.POST['opex_indexation_start_date'], 'end': self.end_of_operations},
			'debt_interest_construction': {'start': request.POST['start_construction'], 'end': request.POST['end_construction']},
			'debt_interest_operations': {'start': self.COD, 'end': self.debt_maturity_date},
			'operations': {'start': self.COD, 'end': self.end_of_operations},
		}

		self.seasonality = []
		for i in range(1, 13):
			self.seasonality.append(float(request.POST[f'seasonality_m{i}']))

		self.construction_costs_assumptions = []
		delta = relativedelta(self.construction_end, self.construction_start)
		months = delta.years * 12 + delta.months + 1
		for i in range(1, months+1):
			self.construction_costs_assumptions.append(float(request.POST[f'costs_m{i}']))


		self.valuation_df = float(request.POST['discount_factor_valuation'])/100


		self.SHL_margin = float(request.POST['SHL_margin']) / 100

		self.dsra = 6 if int(request.POST['DSRA_choice']) == 1 else 12

		self.price_elec_low = create_elec_price_dict(request, 'price_elec_low_y', self.construction_end, self.liquidation_date)
		self.price_elec_med = create_elec_price_dict(request, 'price_elec_med_y', self.construction_end, self.liquidation_date)
		self.price_elec_high = create_elec_price_dict(request, 'price_elec_high_y', self.construction_end, self.liquidation_date)

		self.opex = float(request.POST['opex'])
		self.lease = float(request.POST['lease'])

		self.corporate_income_tax_rate = float(request.POST['corporate_income_tax']) / 100
		
		self.dev_tax_commune = float(request.POST['dev_tax_commune_tax'])/100
		self.dev_tax_department = float(request.POST['dev_tax_department_tax'])/100
		self.development_tax_rate = self.dev_tax_commune + self.dev_tax_department

		self.payment_delay_revenues = int(request.POST['payment_delay_revenues'])
		self.payment_delay_costs = int(request.POST['payment_delay_costs'])

		inp_all_in_interest = np.array([
			float(request.POST['debt_margin']),
			float(request.POST['debt_swap_rate']),
			float(request.POST['debt_swap_margin']),
			float(request.POST['debt_reference_rate_buffer']),
		])

		self.senior_debt_interest_rate = np.sum(inp_all_in_interest) / 100

		self.senior_debt_upfront_fee = float(request.POST['debt_upfront_fee']) / 100
		self.senior_debt_commitment_fee = float(request.POST['debt_commitment_fee']) / 100


		self.injection_choice = int(request.POST['injection_choice'])
		self.subgearing = float(request.POST['subgearing']) / 100

		self.sensi_production = float(request.POST['sensi_production'])/100
		self.sensi_opex = float(request.POST['sensi_opex'])/100
		self.sensi_inflation = float(request.POST['sensi_inflation'])/100



		self.P90 = float(request.POST['p90_10y'])/1000
		self.P75 = float(request.POST['p75'])/1000
		self.P50 = float(request.POST['p50'])/1000

		self.contract = request.POST['contract']

		self.target_DSCR =  float(request.POST['debt_target_DSCR'])
		self.target_gearing =  float(request.POST['debt_gearing_max']) / 100

		self.cash_min = int(request.POST['cash_min'])

		self.index_rate_merchant = float(request.POST['price_elec_indexation']) / 100
		self.index_rate_contract = float(request.POST['contract_indexation']) / 100
		self.index_rate_opex = float(request.POST['opex_indexation']) / 100
		self.index_rate_lease = float(request.POST['lease_indexation']) / 100


		self.tfpb_rate = (float(request.POST['tfpb_commune_tax'])+float(request.POST['tfpb_department_tax'])+float(request.POST['tfpb_region_tax'])+float(request.POST['tfpb_additional_tax']))/100
		self.cfe_rate = (float(request.POST['cfe_commune_tax'])+float(request.POST['cfe_intercommunal_tax'])+float(request.POST['cfe_specific_eqp_tax'])+float(request.POST['cfe_localCCI_tax']))/100
		self.cfe_mgt_fee = float(request.POST['cfe_mgt_fee'])/100
		self.cfe_discount_tax_base= float(request.POST['cfe_discount_tax_base'])/100



	def init_001_dates_series(self):

		self.dates_series = {}
		# Create a timeline for the model
		self.dates_series['model']	= {
				'start': create_model_start_series(self.periodicity, self.construction_start, self.construction_end, self.liquidation_date),
				'end': create_model_end_series(self.periodicity, self.construction_start, self.construction_end, self.liquidation_date),
			}

		# Create a timeline for each contract
		for period_name, period_dates in self.periods.items():
			self.dates_series[period_name] = {
				'start': create_start_period_series(self.dates_series['model']['start'], period_dates['start'], period_dates['end']),
				'end': create_end_period_series(self.dates_series['model']['end'], period_dates['start'], period_dates['end']),
			}

	def init_002_flags(self):

		# Define a dictionary that maps period names to their start and end dates
		self.flag_dict = {
			'construction_start': (self.construction_start, self.construction_start),
			'construction_end': (self.construction_end, self.construction_end),
			'construction': (self.construction_start, self.construction_end),
			'operations': (self.COD, self.end_of_operations),
			'contract': (self.periods['contract']['start'], self.periods['contract']['end']),
			'operations_end': (self.end_of_operations, self.end_of_operations),
			'liquidation': (self.end_of_operations + datetime.timedelta(days=1), self.liquidation_date),
			'liquidation_end': (self.liquidation_date, self.liquidation_date),
			'debt_amo': (self.COD, self.debt_maturity),
			'contract_indexation': (self.periods['contract_indexation']['start'], self.periods['contract']['end']),
			'merchant_indexation': (self.periods['merchant_indexation']['start'], self.end_of_operations),
			'lease_indexation': (self.periods['lease_indexation']['start'], self.end_of_operations),
			'opex_indexation': (self.periods['opex_indexation']['start'], self.end_of_operations),
			}

		# Create a dictionary that contains all the flags for the financial model
		self.flags = {}
		for name, (start, end) in self.flag_dict.items():
			self.flags[name] = ((self.dates_series['model']['end'] >= pd.to_datetime(start)) * (self.dates_series['model']['start'] <= pd.to_datetime(end))).astype(int)

		self.flags['start_year'] = (pd.DatetimeIndex(self.dates_series['model']['start']).month == 1) * 1

	def init_003_days_series(self):

		self.days_series = {}

		days_series_dict = {
		'model': {'flag': 1, 'start_dates': self.dates_series['model']['start'], 'end_dates': self.dates_series['model']['end']},
		'contract': {'flag': self.flags['contract'], 'start_dates': self.dates_series['contract']['start'], 'end_dates': self.dates_series['contract']['end']},
		'contract_indexation': {'flag': self.flags['contract_indexation'], 'start_dates': self.dates_series['contract_indexation']['start'], 'end_dates': self.dates_series['contract_indexation']['end']},
		'merchant_indexation': {'flag': self.flags['merchant_indexation'], 'start_dates': self.dates_series['merchant_indexation']['start'], 'end_dates': self.dates_series['merchant_indexation']['end']},
		'opex_indexation': {'flag': self.flags['opex_indexation'], 'start_dates': self.dates_series['opex_indexation']['start'], 'end_dates': self.dates_series['opex_indexation']['end']},
		'debt_interest_construction': {'flag': self.flags['construction'], 'start_dates': self.dates_series['debt_interest_construction']['start'], 'end_dates': self.dates_series['debt_interest_construction']['end']},
		'debt_interest_operations': {'flag': self.flags['debt_amo'], 'start_dates': self.dates_series['debt_interest_operations']['start'], 'end_dates': self.dates_series['debt_interest_operations']['end']},
		'operations': {'flag': self.flags['operations'], 'start_dates': self.dates_series['operations']['start'], 'end_dates': self.dates_series['operations']['end']},
		'lease_indexation': {'flag': self.flags['lease_indexation'], 'start_dates': self.dates_series['lease_indexation']['start'], 'end_dates': self.dates_series['lease_indexation']['end']},		
		}

		for key, value in days_series_dict.items():
			self.days_series[key] = ((value['end_dates'] - value['start_dates']).dt.days + 1) * value['flag']

	def init_004_time_series(self):
		
		self.time_series = {}

		self.time_series['days_in_year'] = pd.Series(self.dates_series['model']['end']).dt.is_leap_year * 366 + (1 - pd.Series(self.dates_series['model']['end']).dt.is_leap_year) * 365
		self.time_series['years_in_period'] = self.days_series['model'] / self.time_series['days_in_year']
		self.time_series['years_during_operations'] = self.time_series['years_in_period'] * self.flags['operations']
		self.time_series['quarters'] = get_quarters(self.dates_series['model']['end'])
		self.time_series['years_from_COD_eop'] = self.time_series['years_during_operations'].cumsum()
		self.time_series['years_from_COD_bop'] = self.time_series['years_from_COD_eop'] - self.time_series['years_during_operations']
		self.time_series['years_from_COD_avg'] = (self.time_series['years_from_COD_eop'] + self.time_series['years_from_COD_bop']) / 2
		self.time_series['series_end_period_year'] = pd.Series(self.dates_series['model']['end']).dt.year
		self.time_series['pct_in_operations_period'] = pd.Series(self.days_series['operations']) / pd.Series(self.days_series['model'])
		self.time_series['pct_in_contract_period'] = np.where(pd.Series(self.days_series['operations']) > 0, pd.Series(self.days_series['contract']) / pd.Series(self.days_series['operations']),0)  
		self.time_series['years_from_base_dates'] = calc_years_from_base_dates(self.days_series, self.time_series['days_in_year'])

	
	def init_005_seasonality_series(self):
		self.seasonality = create_season_series(self.seasonality,self.dates_series)
		self.create_capacity_series()


	def init_006_production(self, sensi_production = 0):

		self.production = {}
		self.production['total'] = self.P90  * pd.Series(self.seasonality) * self.capacity['after_degradation'] * (1 + sensi_production)
		self.production['contract'] = self.production['total'] * self.time_series['pct_in_contract_period'] * self.time_series['pct_in_operations_period']
		self.production['contract_cumul_in_year'] = calc_production_cumul(self.production['contract'],self.flags['start_year'])
		self.production['capacity_factor'] = np.where(self.days_series['operations']>0,self.production['total']/((self.installed_capacity*self.days_series['operations']*24)/1000),0)

	def init_007_construction_costs_series(self):

		self.construction_costs = {}
		self.construction_costs['total'] = np.hstack([self.construction_costs_assumptions,np.zeros(len(self.flags['operations']) - len(self.construction_costs_assumptions))]) * self.flags['construction']
		self.comp_local_taxes()


	def init_008_indexation_series(self, sensi_inflation = 0):

		# Create a dictionary to store the mapping between the index names and their corresponding columns
		index_columns = {
			'merchant': 'merchant_indexation',
			'contract': 'contract_indexation',
			'opex': 'opex_indexation',
			'lease': 'lease_indexation'
		}

		self.indexation_series = {}

		# Iterate over the dictionary to create the indexation vectors
		for indice_name, column_name in index_columns.items():

			# Create the indexation vector for the current index
			indexation_rate = getattr(self, f'index_rate_{indice_name}') + sensi_inflation
			indexation_year = self.time_series['years_from_base_dates'][column_name]
			self.indexation_series[indice_name] = (1 + indexation_rate) ** indexation_year


	def init_009_price_series(self):
		
		self.price_series = {}

		self.price_series['merchant_real'] = array_elec_prices(self.time_series['series_end_period_year'], self.price_elec_low)
		self.price_series['merchant_nom'] = self.price_series['merchant_real'] * self.indexation_series['merchant']
		
		self.price_series['contract_real'] = self.contract_price * self.flags['contract']
		self.price_series['contract_nom'] = self.price_series['contract_real'] * self.indexation_series['contract']

	def init_010_revenues(self):

		self.revenues_series = {}

		self.revenues_series['contract'] = self.production['total'] * self.price_series['contract_nom'] / 1000 * self.time_series['pct_in_contract_period'] * self.time_series['pct_in_operations_period']
		self.revenues_series['merchant'] = self.production['total'] * self.price_series['merchant_nom'] / 1000 * (1-self.time_series['pct_in_contract_period']) * self.time_series['pct_in_operations_period']
		self.revenues_series['total'] = self.revenues_series['contract'] + self.revenues_series['merchant']

		
	def init_011_opex(self, sensi_opex = 0):

		self.opex_series = {}

		self.opex_series['operating_costs'] = self.opex * self.indexation_series['opex'] * self.time_series['years_during_operations'] * (1 + sensi_opex)
		self.opex_series['lease_costs'] = self.lease * self.indexation_series['lease'] * self.time_series['years_during_operations'] * (1 + sensi_opex)
		self.opex_series['total'] = self.opex_series['operating_costs'] + self.opex_series['lease_costs']
		

	def init_012_EBITDA(self):

		self.EBITDA = {}

		self.EBITDA['EBITDA'] = self.revenues_series['total'] - self.opex_series['total']
		self.EBITDA['EBITDA_margin'] = np.where(self.revenues_series['total'] > 0, np.divide(self.EBITDA['EBITDA'], self.revenues_series['total']), 0)


	def init_013_working_cap(self):

		self.working_cap = {}

		self.working_cap['revenues_in_period_paid'] = (1 - self.payment_delay_revenues / self.days_series['model']) * self.revenues_series['total']
		self.working_cap['accounts_receivable_eop'] = self.revenues_series['total'] - self.working_cap['revenues_in_period_paid']
		self.working_cap['accounts_receivable_bop'] = np.roll(self.working_cap['accounts_receivable_eop'], 1)

		self.working_cap['costs_in_period_paid'] = (1 - self.payment_delay_costs / self.days_series['model']) * self.opex_series['total']
		self.working_cap['accounts_payable_eop'] = self.opex_series['total'] - self.working_cap['costs_in_period_paid']
		self.working_cap['accounts_payable_bop'] = np.roll(self.working_cap['accounts_payable_eop'], 1)

		self.working_cap['cashflows_from_creditors'] = np.ediff1d(self.working_cap['accounts_receivable_eop'], to_begin=self.working_cap['accounts_receivable_eop'][0])
		self.working_cap['cashflows_from_debtors'] = np.ediff1d(self.working_cap['accounts_payable_eop'], to_begin=self.working_cap['accounts_payable_eop'][0])
		self.working_cap['working_cap_movement'] = self.working_cap['cashflows_from_debtors'] - self.working_cap['cashflows_from_creditors']
		


	@timer_decorator
	def init_014_create_financial_model(self):
		self.converg_variables()
		# Loop until convergence between the target debt amount / debt amount; target debt repayment schedule / debt repayment schedule
		for i in range(self.iteration):

			self.senior_debt_amount = self.debt_sizing['target_debt_amount']
			self.senior_debt['repayments'] = self.senior_debt['target_repayments']
			self.calculations_req_loop(with_debt_sizing_sculpting=True)



	def calculations_req_loop(self, with_debt_sizing_sculpting=False):
		self.calc_injections()
		self.calc_senior_debt()
		self.calc_total_uses()
		self.calc_depreciation()
		self.calc_income_statement()
		self.calc_CFS()
		if with_debt_sizing_sculpting:
			self.calc_senior_debt_size()
			self.calc_senior_debt_repayments()
		self.calc_DSRA()
		self.calc_accounts()
		self.calc_convergence_tests()


	def init_015_create_results(self):
		self.calc_balance_sheet()
		self.calc_ratios()
		self.calc_irr()
		self.calc_valuation()
		self.calc_audit()
			
		
	def apply_sensitivity(self, sensitivity_type):
		# Apply the sensitivity to the copy of the Base Case financial model
		if sensitivity_type == 'Sensi Production':
			self.init_006_production(sensi_production = self.sensi_production)
		
		elif sensitivity_type == 'Sensi Inflation':
			self.init_008_indexation_series(sensi_inflation = self.sensi_inflation)
		
		elif sensitivity_type == 'Sensi Opex':
			self.init_011_opex(sensi_opex = self.sensi_opex)
		
		elif sensitivity_type == 'Sponsor Case':
			self.production['total'] = self.P50*pd.Series(self.seasonality)*self.capacity['after_degradation']
		
		else:
			
			pass

	@timer_decorator
	def create_sensi(self):
		# Rerun the methods on which the sensititiy had an impact and recompute the financial model
		self.init_009_price_series()
		self.init_010_revenues()
		self.init_012_EBITDA()
		self.init_013_working_cap()
		self.calculations_req_loop(with_debt_sizing_sculpting=False)
		self.init_015_create_results()
		return self


	def create_dict_result(self):


		dict_total = create_financial_model_dict(self)

		return dict_total


	def converg_variables(self):

		data_length = len(self.dates_series['model']['end'])

		self.optimised_devfee = 0

		self.development_fee = np.full(data_length, 0)

		self.uses = {}
		self.IS = {}
		self.op_account = {}
		self.SHL = {}
		self.senior_debt = {}
		self.CFS = {}
		self.discount_factor = {}
		self.BS = {}
		
		self.distr_account = {}
		self.debt_sizing = {}
		self.share_capital = {}
		self.audit = {}



		self.uses['total'] = self.construction_costs['total'] 
		self.uses['total_cumul'] = self.uses['total'].cumsum()

		self.IS['distributable_profit'] = np.full(data_length, 1)
		


		self.SHL['balance_bop'] = np.full(data_length, 1)
		self.SHL['interests_construction'] = np.full(data_length, 0)
		self.SHL['interests_operations'] = np.full(data_length, 0)
		


		self.op_account['balance_eop'] = np.full(data_length, 0)
			
		
		self.DSRA = {}
		self.DSRA['dsra_bop'] = np.full(data_length, 0)
		self.DSRA['initial_funding'] = np.full(data_length, 0)
		self.DSRA['dsra_mov'] = np.full(data_length, 0)
		self.DSRA_initial_funding_max = 0



		self.debt_sizing['target_debt_amount'] = self.uses['total']  * self.target_gearing
		self.senior_debt['target_repayments'] = np.full(data_length, 0)



	@timer_decorator
	def calc_injections(self):
		
		self.injections = {}

		equity_amount = self.uses['total']  - self.senior_debt_amount
		self.gearing_eff = (self.senior_debt_amount / self.uses['total'].sum() )

		if self.injection_choice == 1:
			senior_debt_drawdowns_cumul = np.clip(self.uses['total_cumul'] * self.gearing_eff, None, self.senior_debt_amount)
			self.injections['senior_debt'] = np.ediff1d(senior_debt_drawdowns_cumul, to_begin=senior_debt_drawdowns_cumul[0])
			self.injections['equity'] = self.uses['total']  - self.injections['senior_debt']
			self.injections['share_capital'] = self.injections['equity'] * (1 - self.subgearing)
			self.injections['SHL'] = self.injections['equity'] * self.subgearing
			self.injections['total'] = self.injections['senior_debt'] + self.injections['equity']

		elif self.injection_choice == 2:
			senior_debt_drawdowns_cumul = np.clip(self.uses['total_cumul'] * self.gearing_eff, None, self.senior_debt_amount)
			self.injections['senior_debt'] = np.ediff1d(senior_debt_drawdowns_cumul, to_begin=senior_debt_drawdowns_cumul[0])
			self.injections['equity'] = self.uses['total']  - self.injections['senior_debt']
			self.injections['share_capital'] = self.injections['equity'] * (1 - self.subgearing)
			self.injections['SHL'] = self.injections['equity'] * self.subgearing

			self.injections['total'] = self.injections['senior_debt'] + self.injections['equity']


	@timer_decorator
	def calc_senior_debt(self):

		
		self.senior_debt['balance_eop'] = (self.injections['senior_debt'] - self.senior_debt['repayments']).cumsum()
		self.senior_debt['balance_bop'] = self.senior_debt['balance_eop'] + self.senior_debt['repayments'] - self.injections['senior_debt']

		self.senior_debt['interests_construction'] = self.senior_debt['balance_bop'] * self.senior_debt_interest_rate * self.days_series['debt_interest_construction'] / 360
		self.senior_debt['interests_operations'] = self.senior_debt['balance_bop'] * self.senior_debt_interest_rate * self.days_series['debt_interest_operations'] / 360

		self.senior_debt['interests'] = self.senior_debt['interests_construction'] + self.senior_debt['interests_operations']

		self.senior_debt['upfront_fee'] = self.flags['construction_start'] * self.senior_debt_amount * self.senior_debt_upfront_fee

		self.senior_debt['senior_debt_available_eop'] = (self.senior_debt_amount - self.senior_debt['balance_bop']) * self.flags['construction']
		self.senior_debt['senior_debt_available_bop'] = self.senior_debt['senior_debt_available_eop'] + self.injections['senior_debt']

		self.senior_debt['commitment_fees'] = self.senior_debt['senior_debt_available_bop'] * self.senior_debt_commitment_fee * self.days_series['model']/360

	@timer_decorator
	def calc_total_uses(self):

		"""
		self.capitalised_fees_cumul = (self.senior_debt['senior_debt_idc'] + self.senior_debt['upfront_fee'] + self.senior_debt['commitment_fees'] + self.SHL_interests_construction).cumsum()
		"""
		self.uses['construction'] = self.construction_costs['total']
		self.uses['development_fee'] = 0
		self.uses['senior_debt_idc_and_fees'] = self.senior_debt['interests_construction'] + self.senior_debt['upfront_fee'] + self.senior_debt['commitment_fees']   
		self.uses['reserves'] = self.DSRA['initial_funding']
		self.uses['local_taxes'] = self.local_taxes['total']

		self.uses['total']  = self.uses['construction'] + self.uses['development_fee'] + self.uses['senior_debt_idc_and_fees'] + self.uses['reserves'] + self.uses['local_taxes']



	def calc_depreciation(self):

		self.IS['depreciation'] = self.uses['total'].sum() * self.time_series['years_during_operations'] / self.operating_life


	@timer_decorator	
	def calc_income_statement(self):

		self.IS['EBIT'] = self.EBITDA['EBITDA'] - self.IS['depreciation']
		self.IS['EBT'] = self.IS['EBIT'] - self.senior_debt['interests_operations'] - self.SHL['interests_operations']
		self.IS['corporate_income_tax'] = np.clip(self.corporate_income_tax_rate * self.IS['EBT'], 0, None)
		self.IS['net_income'] = self.IS['EBT'] - self.IS['corporate_income_tax']
	
	@timer_decorator
	def calc_CFS(self):

		self.CFS['cash_flows_operating'] = self.EBITDA['EBITDA'] + self.working_cap['working_cap_movement'] - self.IS['corporate_income_tax']
		self.CFS['cash_flows_investing'] = - (self.uses['construction'] + self.uses['development_fee'] + self.uses['local_taxes'] + self.uses['reserves']) 
		self.CFS['cash_flows_financing'] = - (self.senior_debt['upfront_fee'] + self.senior_debt['commitment_fees'] - self.injections['senior_debt'] - self.injections['equity']) 
		self.CFS['CFADS'] = self.CFS['cash_flows_operating'] + self.CFS['cash_flows_investing'] + self.CFS['cash_flows_financing']
		self.CFS['CFADS_amo'] = self.CFS['CFADS'] * self.flags['debt_amo']
		self.CFS['CFADS_operations'] = self.CFS['CFADS'] * self.flags['operations']

	@timer_decorator
	def calc_senior_debt_size(self):
		
		self.discount_factor['avg_interest_rate'] = np.where(self.days_series['debt_interest_operations'] != 0,np.divide(self.senior_debt['interests_operations'], self.senior_debt['balance_bop'], out=np.zeros_like(self.senior_debt['interests_operations']), where=self.senior_debt['balance_bop'] != 0) / self.days_series['debt_interest_operations'] * 360,0)	
		self.discount_factor['discount_factor'] = np.where(self.flags['debt_amo'] == 1, (1 / (1 + (self.discount_factor['avg_interest_rate'] * self.days_series['debt_interest_operations'] / 360))), 1)
		self.discount_factor['discount_factor_cumul'] = self.discount_factor['discount_factor'].cumprod()

		self.debt_sizing['CFADS_amo'] = self.CFS['cash_flows_operating'] * self.flags['debt_amo']
		self.debt_sizing['target_DSCR'] = self.target_DSCR * self.flags['debt_amo']

		self.debt_sizing['target_DS'] = self.debt_sizing['CFADS_amo'] / self.target_DSCR
		self.debt_sizing['target_debt_DSCR'] = sum(self.debt_sizing['target_DS'] * self.discount_factor['discount_factor_cumul'])
		self.debt_sizing['target_debt_gearing'] = self.uses['total'].sum() * self.target_gearing
		self.debt_sizing['target_debt_amount'] = min(self.debt_sizing['target_debt_DSCR'] , self.debt_sizing['target_debt_gearing'])

	@timer_decorator
	def calc_senior_debt_repayments(self):

		senior_debt_drawdowns_sum  = sum(self.injections['senior_debt'])				
		npv_CFADS = sum(self.debt_sizing['CFADS_amo'] * self.discount_factor['discount_factor_cumul'])
		DSCR_sculpting = npv_CFADS / senior_debt_drawdowns_sum if senior_debt_drawdowns_sum > 0 else 1

		self.senior_debt['target_repayments'] = np.maximum(0, np.minimum(self.senior_debt['balance_bop'], self.debt_sizing['CFADS_amo'] / DSCR_sculpting - self.senior_debt['interests_operations']))
		
		self.DS_effective = self.senior_debt['repayments'] + self.senior_debt['interests_operations']
		

	@timer_decorator
	def calc_DSRA(self):

		self.DSRA['cash_available_for_dsra'] = np.maximum(self.CFS['CFADS_amo'] - self.DS_effective, 0)
		self.DSRA['dsra_target'] = calc_dsra_target(self.dsra, self.periodicity, self.DS_effective) * self.flags['debt_amo']
		self.DSRA['DSRA_initial_funding'] = calc_dsra_funding(self.DSRA['dsra_target']) * self.flags['construction_end']
		self.DSRA['dsra_additions_available'] = np.minimum(self.DSRA['cash_available_for_dsra'], self.DSRA['dsra_target'])
		self.DSRA['dsra_additions_required'] = np.maximum(self.DSRA['dsra_target'] - self.DSRA['dsra_bop'], 0)
		self.DSRA['dsra_additions_required_available'] = np.minimum(self.DSRA['dsra_additions_available'], self.DSRA['dsra_additions_required'])
		self.DSRA['dsra_target'] = self.DSRA['dsra_target'] + self.DSRA['DSRA_initial_funding']
		self.DSRA['dsra_eop'] = np.clip((self.DSRA['DSRA_initial_funding'] + self.DSRA['dsra_additions_required_available']).cumsum(), 0, self.DSRA['dsra_target'])
		self.DSRA['dsra_eop_mov'] = np.ediff1d(self.DSRA['dsra_eop'], to_begin=self.DSRA['dsra_eop'][0])
		self.DSRA['dsra_additions'] = np.maximum(self.DSRA['dsra_eop_mov'], 0)
		self.DSRA['dsra_release'] = np.minimum(self.DSRA['dsra_eop_mov'], 0)
		self.DSRA['dsra_bop'] = np.roll(self.DSRA['dsra_eop'], 1)
		self.DSRA['dsra_mov'] =(self.DSRA['dsra_eop'] - self.DSRA['dsra_bop'])

		self.DSRA_initial_funding_max = max(self.DSRA['DSRA_initial_funding'])


	@timer_decorator
	def calc_accounts(self):

		self.distr_account['cash_available_for_distribution'] = (self.CFS['CFADS'] - self.DS_effective - self.DSRA['dsra_mov'] - self.cash_min * self.flags['operations'])
		self.distr_account['transfers_distribution_account'] = self.distr_account['cash_available_for_distribution'].clip(lower=0)

		self.op_account['balance_eop'] = self.distr_account['cash_available_for_distribution']  - self.distr_account['transfers_distribution_account']

		"""
		+ DSRA_initial_funding 
		"""
		
		self.op_account['balance_eop'] = np.roll(self.op_account['balance_eop'], 1)


		for i in range(self.iteration):
		
			self.SHL['interests_operations'] = self.SHL['balance_bop'] * self.SHL_margin * self.days_series['model'] / 360 * self.flags['operations']
			self.SHL['interests_construction'] = self.SHL['balance_bop'] * self.SHL_margin * self.days_series['model'] / 360 * self.flags['construction']

			self.SHL['interests_paid'] = np.minimum(self.distr_account['transfers_distribution_account'], self.SHL['interests_operations'])
			self.distr_account['cash_available_for_dividends'] = self.distr_account['transfers_distribution_account'] - self.SHL['interests_paid']
			self.distr_account['dividends_paid']  = np.minimum(self.distr_account['cash_available_for_dividends'], self.IS['distributable_profit'])
			
			self.distr_account['cash_available_for_SHL_repayments']  = self.distr_account['cash_available_for_dividends'] - self.distr_account['dividends_paid']
			self.SHL['repayments']  = np.minimum(self.SHL['balance_bop'], self.distr_account['cash_available_for_SHL_repayments'])
			
			self.distr_account['cash_available_for_redemption'] = self.distr_account['cash_available_for_SHL_repayments'] - self.SHL['repayments']

			self.distr_account['balance_eop'] = (self.distr_account['transfers_distribution_account'] - self.SHL['interests_paid'] - self.distr_account['dividends_paid'] - self.SHL['repayments']).cumsum()
			self.distr_account['balance_bop'] = self.distr_account['balance_eop'] - (self.distr_account['transfers_distribution_account'] - self.SHL['interests_paid'] - self.distr_account['dividends_paid'] - self.SHL['repayments'])
			
			self.SHL['balance_eop'] = (self.injections['SHL'] + self.SHL['interests_construction'] - self.SHL['repayments']).cumsum()
			self.SHL['balance_bop'] = self.SHL['balance_eop'] - (self.injections['SHL'] + self.SHL['interests_construction'] - self.SHL['repayments'])
			
			self.IS['retained_earnings_eop'] = (self.IS['net_income'] - self.distr_account['dividends_paid']).cumsum()
			self.IS['retained_earnings_bop'] = self.IS['retained_earnings_eop'] - (self.IS['net_income'] - self.distr_account['dividends_paid'])
			self.IS['distributable_profit'] = np.clip(self.IS['retained_earnings_bop'] + self.IS['net_income'], 0, None)

			self.share_capital['repayments'] = self.distr_account['balance_bop'] * self.flags['liquidation_end']
			self.distr_account['balance_eop'] = self.distr_account['balance_eop'] - self.share_capital['repayments']

			self.share_capital['balance_eop'] = (self.injections['share_capital'] - self.share_capital['repayments']).cumsum()
			self.share_capital['balance_bop'] = self.share_capital['balance_eop'] - (self.injections['share_capital'] - self.share_capital['repayments'])



	def calc_convergence_tests(self):

		debt_amount_not_converged = abs(self.senior_debt_amount - self.debt_sizing['target_debt_amount']) > 0.1
		difference = self.senior_debt['target_repayments'] - self.senior_debt['repayments']
		debt_sculpting_not_converged = np.where(difference == 0, True, False)
		self.debt_sculpting_not_converged = np.any(np.logical_not(debt_sculpting_not_converged))
		 
		 
	def calc_balance_sheet(self):
		
		self.BS['PPE'] = ( 
			self.construction_costs['total'].cumsum() + 
			self.uses['senior_debt_idc_and_fees'].cumsum() + 
			self.local_taxes['total'].cumsum()
		)

		self.BS['total_assets'] = (
			self.BS['PPE'] + 
			self.working_cap['accounts_receivable_eop'] + 
			self.DSRA['dsra_eop'] + 
			self.distr_account['balance_eop'] + 
			self.op_account['balance_eop']
		)

		self.BS['total_equity'] = (
			self.SHL['balance_eop'] + 
			self.share_capital['balance_eop'] + 
			self.IS['retained_earnings_eop'] 
		)

		self.BS['total_liabilities'] = (
			self.senior_debt['balance_eop'] + 
			self.working_cap['accounts_payable_eop']
		)



	def calc_ratios(self):
		
		self.DSCR_effective = np.divide(self.CFS['CFADS_amo'], self.DS_effective, out = np.zeros_like(self.CFS['CFADS_amo']), where = self.DS_effective != 0)

		self.LLCR = calculate_ratio(self.discount_factor['avg_interest_rate'], self.debt_sizing['CFADS_amo'], self.senior_debt['balance_eop'], self.dates_series['model']['end'])

		self.PLCR = calculate_ratio(self.discount_factor['avg_interest_rate'], self.CFS['CFADS'], self.senior_debt['balance_eop'], self.dates_series['model']['end'])

		self.DSCR_avg = self.DSCR_effective[self.flags['debt_amo'] == 1].mean()
		self.DSCR_min = self.DSCR_effective[self.flags['debt_amo'] == 1].min()

		mask = (self.flags['debt_amo'] == 1)
		indices = np.where(mask)[0]
		indices_without_last = indices[:-1]

		self.LLCR_min = self.LLCR[indices_without_last].min()


	def calc_irr(self):

		self.IRR = {}


		share_capital_cf = -self.injections['share_capital'] + self.distr_account['dividends_paid'] + self.share_capital['repayments']
		SHL_cf = -self.injections['SHL'] + self.SHL['interests_operations'] + self.SHL['repayments']
		self.equity_cf = share_capital_cf + SHL_cf
		equity_cf_cumul = self.equity_cf.cumsum()

		self.IRR['equity'] = xirr(pd.to_datetime(self.dates_series['model']['end']).dt.date, self.equity_cf)
		self.IRR['share_capital'] = xirr(pd.to_datetime(self.dates_series['model']['end']).dt.date, share_capital_cf)
		self.IRR['SHL'] = xirr(pd.to_datetime(self.dates_series['model']['end']).dt.date, SHL_cf)
	 
		project_cf_pre_tax = -self.uses['total'] + self.EBITDA['EBITDA']
		project_cf_post_tax = project_cf_pre_tax + self.IS['corporate_income_tax']
		
		self.IRR['project_pre_tax'] = xirr(pd.to_datetime(self.dates_series['model']['end']).dt.date, project_cf_pre_tax)
		self.IRR['project_post_tax'] = xirr(pd.to_datetime(self.dates_series['model']['end']).dt.date, project_cf_post_tax)

		debt_cash_flows = -self.injections['senior_debt'] + self.senior_debt['repayments'] + self.senior_debt['interests'] + self.senior_debt['upfront_fee'] + self.senior_debt['commitment_fees']
		self.IRR['senior_debt'] = xirr(pd.to_datetime(self.dates_series['model']['end']).dt.date, debt_cash_flows)
		
		self.irr_curve = create_IRR_curve(self.equity_cf, self.dates_series['model']['end'])

		payback_date = find_payback_date(self.dates_series['model']['end'], equity_cf_cumul)

		try:
			payback_date = parser.parse(str(payback_date)).date()
			time_difference = payback_date - self.construction_start
			self.payback_time = round(time_difference.days / 365.25, 1)
			self.payback_date = payback_date.strftime("%d/%m/%Y")
		except ParserError:
			self.payback_date = "error"
			self.payback_time = "error"


		self.debt_constraint = determine_debt_constraint(self.debt_sizing['target_debt_DSCR'], self.debt_sizing['target_debt_gearing'])
		self.gearing_during_finplan = self.injections['senior_debt'].cumsum()/(self.injections['equity'].cumsum()+self.injections['senior_debt'].cumsum())



	
	def calc_audit(self):

		self.audit = {}

		self.audit['financing_plan'] = self.uses['total'] - self.injections['total']
		self.audit['balance_sheet'] = self.BS['total_assets'] - self.BS['total_liabilities']

		self.check_financing_plan = abs(sum(self.uses['total'] - self.injections['total'])) < 0.01
		self.check_balance_sheet = abs(sum(self.BS['total_assets'] - self.BS['total_liabilities'])) < 0.01

		final_repayment_date_debt = find_last_payment_date(self.dates_series['model']['end'], self.senior_debt['balance_bop'])
		final_repayment_date_debt = final_repayment_date_debt.strftime("%Y-%m-%d %H:%M:%S")
		final_repayment_date_debt = parser.parse(final_repayment_date_debt).date()	


		self.tenor_debt = calculate_tenor(final_repayment_date_debt, self.construction_start)


		if self.senior_debt_amount > 0:
			self.average_debt_life = sum(x * y for x, y in zip(self.time_series['years_in_period'], self.senior_debt['balance_bop'])) / self.senior_debt_amount
			self.average_debt_life = round(self.average_debt_life,1)
		else:
			self.average_debt_life=""	



		self.audit['debt_maturity'] = (final_repayment_date_debt == self.debt_maturity_date)

		self.check_all = 1

	def calc_valuation(self):


		end_period = pd.to_datetime(self.dates_series['model']['end'])
		current_date = pd.Timestamp(datetime.datetime.now().date())
		time_since_today = end_period.apply(lambda date: (current_date - date).days)
		time_since_today = time_since_today.clip(lower=0)

		self.eqt_discount_factor = self.valuation_df
		self.eqt_discount_factor_less_1 = self.valuation_df-0.01
		self.eqt_discount_factor_plus_1 = self.valuation_df+0.01

		discount_factor_vector = np.where(time_since_today != 0, (1 / (1 + self.eqt_discount_factor)**(time_since_today/365)), 1)
		discount_factor_less_1_vector = np.where(time_since_today != 0, (1 / (1 + self.eqt_discount_factor_less_1)**(time_since_today/365)), 1)
		discount_factor_plus_1_vector = np.where(time_since_today != 0, (1 / (1 + self.eqt_discount_factor_plus_1)**(time_since_today/365)), 1)


		self.valuation = np.sum(self.equity_cf*discount_factor_vector)
		self.valuation_less_1 = np.sum(self.equity_cf*discount_factor_less_1_vector)
		self.valuation_plus_1 = np.sum(self.equity_cf*discount_factor_plus_1_vector)













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


def calculate_tenor(final_repayment_date, construction_start):
	time_difference = final_repayment_date-construction_start
	tenor = round(time_difference.days / 365.25, 1)
	return tenor




def find_last_payment_date(series_end_period,boolean_array):
	boolean_array = boolean_array > 0.1
	new_array = [date if boolean else 0 for boolean, date in zip(boolean_array, series_end_period)]
	non_zero_dates = [date for date in new_array if date != 0]
	max_date = max(non_zero_dates)
	return max_date






def compute_npv(cfads, discount_rate, dates_series):
	npvs = []

	series_end_period = pd.to_datetime(dates_series).dt.date
	

	for i in range(len(cfads)):
		npv = 0
		if cfads[i] > 1:
			for j in range(i, len(cfads)):
				end_date = dates_series[j]
				start_date = dates_series[i-1]
				time_delta = (end_date - start_date).days/365.25
				npv += cfads[j] / ((1+discount_rate) ** (time_delta))

			npvs.append(npv)
		else: 
			npvs.append(0)

	return npvs





def calculate_ratio(avg_interest_rate, CFADS, senior_debt_balance_eop, dates_series):
	
	avg_i = avg_interest_rate[avg_interest_rate > 0].mean()

	discounted_CFADS = compute_npv(CFADS, avg_i, dates_series)

	ratio = divide_with_condition(discounted_CFADS, senior_debt_balance_eop)

	return ratio


def divide_with_condition(numerator, denominator):
	# Divide numerator by denominator, set 0 where denominator is less than or equal to 0.01
	return np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0.01)
			 

def format_date(date_series):
	return pd.to_datetime(date_series).dt.strftime('%d/%m/%Y')
		


	
def calc_dsra_target(dsra, periodicity, DS_effective):

	look_forward=int(dsra/periodicity)	

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




def array_elec_prices(series_end_period_year,dic_price_elec):
	electricity_prices = []
	
	for row in series_end_period_year:
		if str(row) in dic_price_elec.keys():
			electricity_prices.append(dic_price_elec[str(row)])
		else:
			electricity_prices.append(0)
	
	return electricity_prices



def calc_production_cumul(production, start_calendar_year):

	cumulative_production = np.zeros_like(production)
	for i in range(len(production)):
		if start_calendar_year[i] == 1:
			cumulative_production[i] = production[i]
		else:
			cumulative_production[i] = cumulative_production[i - 1] + production[i]

	return cumulative_production



def get_quarters(date_list):
	date_series = pd.Series(date_list)
	quarters = pd.to_datetime(date_series, format='%Y-%m-%d').dt.quarter
	return quarters.tolist()


def create_start_period_series(series_start_period,start,end):
	start_period_series = array_time(series_start_period,start,end)
	return start_period_series


def create_end_period_series(series_end_period,start,end):
	end_period_series = array_time(series_end_period,start,end)
	return end_period_series


def array_time(timeline,start,end):	
	timeline_result = timeline.clip(lower=pd.Timestamp(start),upper=pd.Timestamp(end))
	return timeline_result


def first_day_month(date):
	first_day_month = date.replace(day=1)
	return first_day_month


def create_model_start_series(periodicity,construction_start,construction_end,liquidation_date):

	"""test = int(periodicity/3)"""
	test = math.floor(int(periodicity) / 3)
	freq_period_start = str(periodicity)+"MS"

	first_day_month_construction_start = first_day_month(construction_start)
	last_day_construction_end = last_day_month(construction_end)
	first_operations_end_date = last_day_construction_end + datetime.timedelta(days=1) + relativedelta(months=+test) + pd.tseries.offsets.QuarterEnd()*test


	first_operations_date = last_day_construction_end + datetime.timedelta(days=1) 
	first_operations_date = pd.Timestamp(first_operations_date)
	first_operations_date = pd.Series(first_operations_date)
	second_operations_date = first_operations_end_date + datetime.timedelta(days=1)
	last_day_liquidation_end = last_day_month(liquidation_date)
	start_period_construction = pd.Series(pd.date_range(first_day_month_construction_start,last_day_construction_end, freq='MS'))
	start_period_operations = pd.Series(pd.date_range(second_operations_date, last_day_liquidation_end,freq=freq_period_start))
	series_start_period = pd.concat([start_period_construction,first_operations_date,start_period_operations], ignore_index=True)
		
	return series_start_period


def create_model_end_series(periodicity,construction_start,construction_end,liquidation_date):

	"""test = int(periodicity/3)"""
	test = math.floor(int(periodicity) / 3)

	freq_period_end = str(periodicity)+"M"

	first_day_month_construction_start = first_day_month(construction_start)
	last_day_construction_end = last_day_month(construction_end)
	first_operations_end_date = last_day_construction_end + datetime.timedelta(days=1) + relativedelta(months=+test) + pd.tseries.offsets.QuarterEnd()*test

	last_day_end_liquidation_plus_freq = first_day_next_month(liquidation_date,periodicity)	
	end_period_operations = pd.Series(pd.date_range(first_operations_end_date, last_day_end_liquidation_plus_freq,freq=freq_period_end))
	end_period_construction = pd.Series(pd.date_range(first_day_month_construction_start,last_day_construction_end, freq='M'))
	series_end_period = pd.concat([end_period_construction,end_period_operations], ignore_index=True)
	
	return series_end_period





def calc_years_from_base_dates(days_series, days_in_year):
	
	keys = ['contract_indexation', 'merchant_indexation', 'opex_indexation', 'lease_indexation']
	
	years_from_base_dates = {}
	for key in keys:
		years = (days_series[key] / days_in_year).cumsum()
		years_from_base_dates[key] = years

	return years_from_base_dates



def last_day_month(period):	
	last_day_month = period.replace(day = calendar.monthrange(period.year, period.month)[1])
	return last_day_month



def first_day_next_month(date,periodicity):
	first_day_next_month = date.replace(day=1) + relativedelta(months=int(periodicity)) + datetime.timedelta(days=-1)
	return first_day_next_month



def create_season_series(seasonality,dates_series):
	
	data = {'start':dates_series['model']['start'],
			'end':dates_series['model']['end']}

	df = pd.DataFrame(data)

	df_seasonality_result = pd.DataFrame(columns=dates_series['model']['end'])

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



def comp_contract_priceALT(contract_type, wind_turbine_installed, rotor_diameter,production_under_contract, production_under_contract_cumul,capacity_factor, days_series,time_series,flags):
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




def create_elec_price_dict(request, prefix, construction_end, liquidation_date):
	
	construction_end_year = construction_end.year
	liquidation_date_year = liquidation_date.year

	years = [str(year) for year in range(construction_end_year, liquidation_date_year+1)]

	dic_price_elec = {}

	for i, year in enumerate(years):
		key = f'{prefix}{i+1}'
		value = float(request.POST[key])
		dic_price_elec[year] = value

	return dic_price_elec



	


def determine_debt_constraint(debt_amount,debt_amount_gearing):
	if debt_amount > debt_amount_gearing:
		constraint = "Gearing"
	else: 
		constraint = "DSCR"
	return constraint




def create_financial_model_dict(self):

	dict_computation = {
		"Dates": {
			"Period start": format_date(self.dates_series['model']['start']).tolist(),
			"Period end":format_date(self.dates_series['model']['end']).tolist(),
		},
	    "FlagsC": {
	        "Construction": self.flags['construction'].tolist(),
	        "Construction start": self.flags['construction_start'].tolist(),
	        "Construction end": self.flags['construction_end'].tolist()
	    },
	    "FlagsM": {
	        "Year": self.time_series['series_end_period_year'].tolist(),
	        "Days in period": self.days_series['model'].tolist(),
	        "Days in year": self.time_series['days_in_year'].tolist(),
	        "Years in period": self.time_series['years_in_period'].tolist(),
	        "Quarter": self.time_series['quarters'],
	        "Start of calendar year": self.flags['start_year'].tolist()
    	},
	    "FlagOftk_i": {
	        "Indexation period": self.flags['contract_indexation'].tolist(),
	        "Indexation start date": format_date(self.dates_series['contract_indexation']['start']).tolist(),
	        "Indexation end date": format_date(self.dates_series['contract_indexation']['end']).tolist(),
	        "Indexation (days)": self.days_series['contract_indexation'].tolist(),
	        "Indexation": self.indexation_series['contract'].tolist()
	    },
		 "FlagOp": {
	        'Operations': self.flags['operations'].tolist(),
	        'Years from COD (BoP)': self.time_series['years_from_COD_bop'].tolist(),
	        'Years from COD (EoP)': self.time_series['years_from_COD_eop'].tolist(),
	        'Years from COD (avg.)': self.time_series['years_from_COD_avg'].tolist(),
	        'Years during operations': self.time_series['years_during_operations'].tolist(),
	        'Liquidation': self.flags['liquidation'].tolist(),
	        'Liquidation end': self.flags['liquidation_end'].tolist(),
	        'Seasonality': self.seasonality,
	        'Days in operations': self.days_series['operations'].tolist(),
	        'Percentage in operations period': self.time_series['pct_in_operations_period'].tolist()
		    },
	    "FlagFin": {
	        "Amortisation period": self.flags["debt_amo"].tolist(),
	        "Days during construction": self.days_series["debt_interest_construction"].tolist(),
	        "Days during operations": self.days_series["debt_interest_operations"].tolist()
		    },
	    "IS": {
	        "Contract revenues": self.revenues_series["contract"].tolist(),
	        "Merchant revenues": self.revenues_series["merchant"].tolist(),
	        "Total revenues": self.revenues_series["total"].tolist(),
	        "Operating expenses": (-1 * self.opex_series["operating_costs"]).tolist(),
	        "Lease": (-1 * self.opex_series["lease_costs"]).tolist(),
	        "EBITDA": self.EBITDA['EBITDA'].tolist(),
	        "Depreciation": (-1 * self.IS['depreciation']).tolist(),
	        "EBIT": self.IS["EBIT"].tolist(),
	        "Senior debt interests": (-1 * self.senior_debt['interests_operations']).tolist(),
	        "Shareholder loan interests": (-1 * self.SHL['interests_operations']).tolist(),
	        "EBT": self.IS["EBT"].tolist(),
	        "Corporate income tax": (-1 * self.IS["corporate_income_tax"]).tolist(),
	        "Net income": self.IS["net_income"].tolist()
		    },
	    "Mkt_i": {
	        "Indexation": self.indexation_series["merchant"].tolist(),
	        "Indexation (days)": self.days_series["merchant_indexation"].tolist(),
	        "Indexation end date": format_date(self.dates_series['merchant_indexation']['end']).tolist(),
	        "Indexation period": self.flags["merchant_indexation"].tolist(),
	        "Indexation start date": format_date(self.dates_series['merchant_indexation']['start']).tolist(),
	    },
	    "Opex": {
	        "Indexation": self.indexation_series["opex"].tolist(),
	        "Indexation (days)": self.days_series["opex_indexation"].tolist(),
	        "Indexation end date": format_date(self.dates_series['opex_indexation']['end']).tolist(),
	        "Indexation period": self.flags["opex_indexation"].tolist(),
	        "Indexation start date": format_date(self.dates_series['opex_indexation']['start']).tolist(),
	        "Years from indexation start date": self.time_series['years_from_base_dates']['opex_indexation'].tolist()
	    },
	    "Lease": {
	        "Indexation": self.indexation_series["lease"].tolist(),
	        "Indexation (days)": self.days_series["lease_indexation"].tolist(),
	        "Indexation end date": format_date(self.dates_series["lease_indexation"]['end']).tolist(),
	        "Indexation period": self.flags["lease_indexation"].tolist(),
	        "Indexation start date": format_date(self.dates_series['lease_indexation']['start']).tolist(),
	        "Years from indexation start date": self.time_series['years_from_base_dates']['lease_indexation'].tolist()
	    },
	    "Price": {
	        "Contract price (unindexed)": self.price_series['contract_real'].tolist(),
	        "Contract price (indexed)": self.price_series["contract_nom"].tolist(),
	        "Electricity market price (unindexed)": self.price_series["merchant_real"],
	        "Electricity market price (indexed)": self.price_series["merchant_nom"].tolist()
	    },
	    "Prod": {
	        "Capacity after degradation": self.capacity["after_degradation"].tolist(),
	        "Capacity before degradation": self.capacity["before_degradation"].tolist(),
	        "Capacity degradation factor": self.capacity["degradation_factor"].tolist(),
	        "Production": self.production['total'].tolist(),
	        "Capacity factor": self.production['capacity_factor'].tolist(),
	        "Contracted production in calendar year to date": self.production['contract'].tolist(),
	    },
	    "WCRec": {
	        "Accounts receivables (BoP)": self.working_cap["accounts_receivable_bop"].tolist(),
	        "Revenue accrued in period": self.revenues_series["total"].tolist(),
	        "Payment received in period": ((-1 * self.working_cap["revenues_in_period_paid"]) + (-1 * self.working_cap["accounts_receivable_bop"])).tolist(),
	        "Accounts receivables (EoP)": self.working_cap["accounts_receivable_eop"].tolist()
	    },
	    "WCPay": {
	        "Accounts payables (BoP)": self.working_cap["accounts_payable_bop"].tolist(),
	        "Costs accrued in period": self.opex_series['total'].tolist(),
	        "Payment made in period": ((-1 * self.working_cap["costs_in_period_paid"]) + (-1 * self.working_cap["accounts_payable_bop"])).tolist(),
	        "Accounts payables (EoP)": self.working_cap["accounts_payable_eop"].tolist()
	    },
	    "CF_op": {
	        "EBITDA": self.EBITDA['EBITDA'].tolist(),
	        "Net movement in working capital": self.working_cap["working_cap_movement"].tolist(),
	        "Corporate income tax": (-1 * self.IS["corporate_income_tax"]).tolist(),
	        "Cash flows from operating activities": self.CFS["cash_flows_operating"].tolist()
	    },
	    "CF_in": {
	        "Construction costs": (-1 * self.uses['construction']).tolist(),
	        "Development tax": (-1 * self.local_taxes['development_tax']).tolist(),
	        "Archaeological tax": (-1 * self.local_taxes['archeological_tax']).tolist(),
	        "Cash flows from investing activities": self.CFS["cash_flows_investing"].tolist()
	    },
	    "CF_fi": {
	        "Arrangement fee (upfront)": (-1 * self.senior_debt['upfront_fee']).tolist(),
	        "Commitment fees": (-1 * self.senior_debt["commitment_fees"]).tolist(),
	        "Capitalised IDC": (-1 * self.senior_debt['interests_construction']).tolist(),       
	        "Senior debt drawdowns": self.injections["senior_debt"].tolist(),
	        "Equity injections": self.injections["equity"].tolist(),
	        "Cash flows from financing activities": self.CFS["cash_flows_financing"].tolist()
	    },
	    "WCMov": {
	        "Cash flow from (to) creditors": (-1 * self.working_cap["cashflows_from_creditors"]).tolist(),
	        "Cash flow from (to) debtors": self.working_cap["cashflows_from_debtors"].tolist(),
	        "Net movement in working capital": self.working_cap["working_cap_movement"].tolist()
	    },
	    "CFADS": {
	        "CFADS": self.CFS['CFADS'].tolist(),
	        "Senior debt interests": (-1 * self.senior_debt['interests_operations']).tolist(),
	        "Senior debt principal": (-1 * self.senior_debt['repayments']).tolist()
	    },
	    "CFDSRA": {
	        "Additions to DSRA": (-1 * self.DSRA["dsra_additions"]).tolist(),
	        "Release of excess funds": (-1 * self.DSRA["dsra_release"]).tolist()
	    },
	    "CFDistr": {
	        "Cash available for distribution": self.distr_account['cash_available_for_distribution'].tolist(),
	        "Transfers to distribution account": (-1 * self.distr_account['transfers_distribution_account']).tolist()
	    },
	    "OpAcc": {
	    },
	    "FP_u": {
	        "Construction costs": self.uses['construction'].tolist(),
	        "Development tax": self.local_taxes['development_tax'].tolist(),
	        "Development fee": self.local_taxes['development_tax'].tolist(),
	        "Archaeological tax": self.local_taxes['archeological_tax'].tolist(),
	        "Interests during construction": self.senior_debt['interests_construction'].tolist(),
	        "Arrangement fee (upfront)": self.senior_debt['upfront_fee'].tolist(),
	        "Commitment fees": self.senior_debt["commitment_fees"].tolist(),
	        "Initial DSRA funding": self.DSRA['DSRA_initial_funding'].tolist(),
	        "Total uses": self.uses['total'].tolist()
	    },
	    "FP_s": {
	        "Senior debt drawdowns": self.injections['senior_debt'].tolist(),
	        "Share capital injections": self.injections['share_capital'].tolist(),
	        "Shareholder loan injections": self.injections['SHL'].tolist(),
	        "Total sources": self.injections['total'].tolist(),
	    },
	    "Debt_a": {
	        "Amount available (BoP)": self.senior_debt["senior_debt_available_bop"].tolist(),
	        "Drawdowns": (-1 * self.injections['senior_debt']).tolist(),
	        "Amount available (EoP)": self.senior_debt["senior_debt_available_eop"].tolist()
	    },
	    "Debt_b": {
	        "Opening balance": self.senior_debt["balance_bop"].tolist(),
	        "Drawdowns": self.injections['senior_debt'].tolist(),
	        "Scheduled repayments": (-1 * self.senior_debt["repayments"]).tolist(),
	        "Closing balance": self.senior_debt["balance_eop"].tolist()
	    },
	    "Debt_i": {
	        "Arrangement fee (upfront)": self.senior_debt["upfront_fee"].tolist(),
	        "Commitment fees": self.senior_debt["commitment_fees"].tolist(),
	        "Debt interests": self.senior_debt["interests"].tolist()
	    },
	    "Sizing": {
	        "CFADS": self.debt_sizing['CFADS_amo'].tolist(),
	        "Target DSCR": self.debt_sizing["target_DSCR"].tolist(),
	        "Target DS": self.debt_sizing["target_DS"].tolist(),
	        "Average interest rate": self.discount_factor["avg_interest_rate"].tolist(),
	        "Discount factor": self.discount_factor["discount_factor"].tolist(),
	        "Cumulative discount factor": self.discount_factor["discount_factor_cumul"].tolist(),
	        "Interests during operations": self.senior_debt["interests_operations"].tolist(),
	        "Debt repayment target": self.senior_debt['target_repayments'].tolist()
	    },
	    "DSRA": {
	        "Cash available for DSRA": self.DSRA["cash_available_for_dsra"].tolist(),
	        "DSRA target liquidity": self.DSRA["dsra_target"].tolist(),
	        "DSRA target additions": self.DSRA["dsra_additions_required"].tolist(),
	        "DSRA (BoP)": self.DSRA["dsra_bop"].tolist(),
	        "Additions to DSRA": self.DSRA["dsra_additions"].tolist(),
	        "Release of excess funds": self.DSRA["dsra_release"].tolist(),
	        "DSRA (EoP)": self.DSRA["dsra_eop"].tolist()
	    },
	    "Distrib_BOP": {
	        "Balance brought forward": self.distr_account["balance_bop"].tolist(),
	        "Transfers to distribution account": self.distr_account["transfers_distribution_account"].tolist()
	    },
	    "Distrib_SHLi": {
	        "Cash available for interests": self.distr_account["cash_available_for_distribution"].tolist(),
	        "Shareholder loan interests paid": (-1 * self.SHL["interests_paid"]).tolist()
	    },
	    "Distrib_Div": {
	        "Cash available for dividends": self.distr_account["cash_available_for_dividends"].tolist(),
	        "Dividends paid": (-1 * self.distr_account["dividends_paid"]).tolist()
	    },
	    "Distrib_SHLp": {
	        "Cash available for repayment": self.distr_account["cash_available_for_SHL_repayments"].tolist(),
	        "Shareholder loan repayment": (-1 * self.SHL["repayments"]).tolist()
	    },
	    "Distrib_SC": {
	        "Cash available for reductions": self.distr_account["cash_available_for_redemption"].tolist(),
	    },
	    "Distrib_EOP": {
	        "Distribution account balance": self.distr_account["balance_eop"].tolist(),
	    },
	    "DevTax": {
	        "Development tax": self.local_taxes['development_tax'].tolist(),
	    },
	    "ArchTax": {
	        "Archaeological tax": self.local_taxes['archeological_tax'].tolist(),
	    },

	    "SHL": {
	        "Opening balance": self.SHL['balance_bop'].tolist(),
	        "Drawdowns": self.injections['SHL'].tolist(),
	        "Capitalised interest": self.SHL['interests_construction'].tolist(),
	        "Repayment": (-1 * self.SHL['repayments']).tolist(),
	        "Closing balance": self.SHL['balance_eop'].tolist()
	    },
	    "iSHL": {
	        "Interests (construction)": self.SHL['interests_construction'].tolist(),
	        "Interests (operations)": self.SHL['interests_operations'].tolist()
	    },
	    "RE_b": {
	        "Distributable profit": self.IS['distributable_profit'].tolist(),
	        "Balance brought forward": self.IS['retained_earnings_bop'].tolist(),
	        "Net income": self.IS['net_income'].tolist(),
	        "Dividends declared": (-1 * self.distr_account['dividends_paid']).tolist(),
	        "Retained earnings": self.IS['retained_earnings_eop'].tolist()
	    },

		"Eqt": {
			"Opening balance": self.share_capital['balance_bop'].tolist(),
			"Contributions": self.injections['share_capital'].tolist(),
			"Capital reductions": (-1 * self.share_capital['repayments']).tolist(),
			"Closing balance": self.share_capital['balance_eop'].tolist(),
        },

	    "BS_a": {
	        "Property, Plant, and Equipment": self.BS['PPE'].tolist(),
	        "Accounts receivables": self.working_cap['accounts_receivable_eop'].tolist(),
	        "Operating account balance": self.op_account['balance_eop'].tolist(),
	        "DSRA balance": self.DSRA['dsra_eop'].tolist(),
	        "Distribution account balance": self.distr_account['balance_eop'].tolist(),
	        "Total assets": self.BS['total_assets'].tolist()
	    },
	    "BS_l": {
	        "Share capital (EoP)": self.share_capital['balance_eop'].tolist(),
	        "Retained earnings": self.IS['retained_earnings_eop'].tolist(),
	        "Shareholder loan (EoP)": self.SHL['balance_eop'].tolist(),
	        "Senior debt (EoP)": self.senior_debt['balance_eop'].tolist(),
	        "Accounts payables (EoP)": self.working_cap['accounts_payable_eop'].tolist(),
	        "Total liabilities": self.BS['total_liabilities'].tolist()
	    },
	    "Ratio": {
	        "DSCR": self.DSCR_effective.tolist(),
	        "LLCR": self.LLCR.tolist(),
	        "PLCR": self.PLCR.tolist()
	    },

	    "Audit": {
	        "Balance sheet balanced": self.audit['balance_sheet'].tolist(),
	        "Financing plan balanced": self.audit['financing_plan'].tolist()
	    },
	    "Graphs": {
	        "Cumulative total uses": self.uses['total_cumul'].tolist(),
	        "Senior debt drawdowns neg": (-1 * self.injections['senior_debt']).tolist(),
	        "Share capital injections neg": (-1 * self.injections['share_capital']).tolist(),
	        "Shareholder loan injections neg": (-1 * self.injections['SHL']).tolist(),
	        "Dividends paid pos": self.distr_account['dividends_paid'].tolist(),
	        "Lease pos": self.opex_series['lease_costs'].tolist(),
	        "Operating expenses pos": (self.opex_series['total']).tolist(),
	        "Senior debt repayments": self.senior_debt['repayments'].tolist(),
	        "EBITDA margin": self.EBITDA['EBITDA_margin'].tolist(),
	        "arr_construction_costs_cumul": self.construction_costs['total'].cumsum().tolist(),
	        "Share capital injections and repayment": (-1 * self.injections['share_capital'] + self.share_capital['repayments']).tolist(),
	        "Shareholder loan injections and repayment": (-1 * self.injections['SHL'] + self.SHL['repayments']).tolist(),
	        "Share capital repayment pos": self.share_capital['repayments'].tolist(),
	        "Debt service": self.DS_effective.tolist(),
	        "IRR curve": self.irr_curve,
	        "Gearing during financing plan": self.gearing_during_finplan.tolist(),
	        "Debt fees": self.uses['senior_debt_idc_and_fees'].tolist(),
	        "Local taxes": self.local_taxes['total'].tolist(),
		    }
	    }

	dict_uses_sources = {
		"Uses": {
			"Construction costs": sum(self.construction_costs['total']),
			"Development fee": 0,
			"Debt interests & fees": sum(self.uses['senior_debt_idc_and_fees']),
			"Upfront fee": sum(self.senior_debt['upfront_fee']),
			"Commitment fees": sum(self.senior_debt['commitment_fees']),
			"IDC": sum(self.senior_debt['interests_construction']),
			"Local taxes": sum(self.local_taxes['total']),
			"Development tax": sum(self.local_taxes['development_tax']),
			"Archeological tax": sum(self.local_taxes['archeological_tax']),
			"Initial DSRA funding": sum(self.DSRA['initial_funding']),
			"Total": sum(self.uses['total']),
		},
		"Sources": {
			"Equity": sum(self.injections['equity']),
			"Share capital": sum(self.injections['share_capital']),
			"Shareholder loan": sum(self.injections['SHL']),
			"Senior debt": sum(self.injections['senior_debt']),
			"Total": sum(self.injections['total']),
		},
	}

	dict_results = {
		"Equity metrics": {
			"Share capital IRR": self.IRR['share_capital'],
			"Shareholder loan IRR": self.IRR['SHL'],
			"Equity IRR": self.IRR['equity'],
			"Payback date": self.payback_date, 
			"Payback time": self.payback_time, 
		},
		"Sensi": {
			"Min DSCR": self.DSCR_min,
			"Avg. DSCR": self.DSCR_avg,
			"Min LLCR": self.LLCR_min ,
			"Equity IRR": self.IRR['equity'],
			"Audit": self.check_all,
		},
		"Project IRR": {
			"Project IRR (pre-tax)": self.IRR['project_pre_tax'],
			"Project IRR (post-tax)": self.IRR['project_post_tax'],
		},
		"Debt metrics": {
			"Debt amount": self.senior_debt_amount,
			"Constraint": self.debt_constraint,
			"Effective gearing": self.gearing_eff,
			"Tenor (door-to-door)": self.tenor_debt,
			"Average life": self.average_debt_life,
			"Average DSCR": self.DSCR_avg,
			"Debt IRR": self.IRR['senior_debt'],
		},
		"Audit": {
			"Financing plan": self.check_financing_plan,
			"Balance sheet": self.check_balance_sheet,
			"Debt maturity": self.check_all,
		},



		}

	dict_valuation_results = {
		'normal': {
			'discount_factor': self.eqt_discount_factor,
			'valuation': self.valuation
		},
		'less_1': {
			'discount_factor': self.eqt_discount_factor_less_1,
			'valuation': self.valuation_less_1
		},
		'plus_1': {
			'discount_factor': self.eqt_discount_factor_plus_1,
			'valuation': self.valuation_plus_1
		},
	}


	dict_total = {
		'dict_computation': dict_computation,
		'dict_uses_sources': dict_uses_sources,
		'dict_results': dict_results,
		'dict_valuation_results': dict_valuation_results,

	}


	return dict_total






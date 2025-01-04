import pandas as pd
import numpy as np
from pyxirr import xirr
from dateutil.parser import ParserError
from dateutil import parser
import datetime


class FinancialModelIRR:
	def __init__(self, instance):
		self.instance = instance
		self.instance.valuation_df = float(self.instance.project.discount_factor_valuation)/100

	def initialize(self):
		self.instance.financial_model['IRR'] = {}

		share_capital_cf = -self.instance.financial_model['injections']['share_capital'] + \
			self.instance.financial_model['distr_account']['dividends_paid'] + \
			self.instance.financial_model['share_capital']['repayments']

		SHL_cf = -self.instance.financial_model['injections']['SHL'] + \
			self.instance.financial_model['SHL']['interests_operations'] + \
			self.instance.financial_model['SHL']['repayments']

		self.instance.equity_cf = share_capital_cf + SHL_cf
		equity_cf_cumul = self.instance.equity_cf.cumsum()

		dates_end = pd.Series(
			pd.to_datetime(self.instance.financial_model['dates']['model']['end'], dayfirst=True)).dt.date

		self.instance.financial_model['IRR']['equity'] = xirr(dates_end, self.instance.equity_cf)
		self.instance.IRR = self.instance.financial_model['IRR']['equity'] * 100

		self.instance.financial_model['IRR']['share_capital'] = xirr(dates_end, share_capital_cf)
		self.instance.financial_model['IRR']['SHL'] = xirr(dates_end, SHL_cf)

		project_cf_pre_tax = -self.instance.financial_model['uses']['total'] + \
			self.instance.financial_model['EBITDA']['EBITDA']

		project_cf_post_tax = project_cf_pre_tax + \
			self.instance.financial_model['IS']['corporate_income_tax']

		self.instance.financial_model['IRR']['project_pre_tax'] = xirr(dates_end, project_cf_pre_tax)
		self.instance.financial_model['IRR']['project_post_tax'] = xirr(dates_end, project_cf_post_tax)

		debt_cash_flows = -self.instance.financial_model['injections']['senior_debt'] + \
			self.instance.financial_model['senior_debt']['repayments'] + \
			self.instance.financial_model['senior_debt']['interests'] + \
			self.instance.financial_model['senior_debt']['upfront_fee'] + \
			self.instance.financial_model['senior_debt']['commitment_fees']

		self.instance.financial_model['IRR']['senior_debt'] = xirr(dates_end, debt_cash_flows)
		self.instance.financial_model['IRR']['irr_curve'] = create_IRR_curve(
			self.instance.equity_cf, self.instance.financial_model['dates']['model']['end'])

		payback_date = find_payback_date(
			pd.Series(self.instance.financial_model['dates']['model']['end']), equity_cf_cumul)

		try:
			payback_date = parser.parse(str(payback_date)).date()
			time_difference = payback_date - self.instance.project.start_construction
			self.instance.financial_model['IRR']['payback_time'] = round(time_difference.days / 365.25, 1)
			self.instance.financial_model['IRR']['payback_date'] = payback_date.strftime("%d/%m/%Y")
		except ParserError:
			self.instance.financial_model['IRR']['payback_date'] = "error"
			self.instance.financial_model['IRR']['payback_time'] = "error"

		self.instance.financial_model['senior_debt']['debt_constraint'] = determine_debt_constraint(
			self.instance.financial_model['debt_sizing']['target_debt_DSCR'],
			self.instance.financial_model['debt_sizing']['target_debt_gearing']
		)
		
		self.instance.financial_model['gearing_during_finplan'] = self.instance.financial_model['injections']['senior_debt'].cumsum() / \
			(self.instance.financial_model['injections']['equity'].cumsum() +
			 self.instance.financial_model['injections']['senior_debt'].cumsum())


		end_period = pd.Series(pd.to_datetime(self.instance.financial_model['dates']['model']['end'], dayfirst=True))
		current_date = pd.Timestamp(datetime.datetime.now().date())
		time_since_today = end_period.apply(lambda date: (current_date - date).days)
		time_since_today = time_since_today.clip(lower=0)


		self.instance.financial_model['IRR']['eqt_discount_factor'] = self.instance.valuation_df
		self.instance.financial_model['IRR']['eqt_discount_factor_less_1'] = self.instance.valuation_df-0.01
		self.instance.financial_model['IRR']['eqt_discount_factor_plus_1'] = self.instance.valuation_df+0.01

		discount_factor_vector = np.where(time_since_today != 0, (1 / (1 + self.instance.financial_model['IRR']['eqt_discount_factor'])**(time_since_today/365)), 1)
		discount_factor_less_1_vector = np.where(time_since_today != 0, (1 / (1 + self.instance.financial_model['IRR']['eqt_discount_factor_less_1'])**(time_since_today/365)), 1)
		discount_factor_plus_1_vector = np.where(time_since_today != 0, (1 / (1 + self.instance.financial_model['IRR']['eqt_discount_factor_plus_1'])**(time_since_today/365)), 1)

		self.instance.financial_model['IRR']['valuation'] = np.sum(self.instance.equity_cf*discount_factor_vector)
		self.instance.financial_model['IRR']['valuation_less_1'] = np.sum(self.instance.equity_cf*discount_factor_less_1_vector)
		self.instance.financial_model['IRR']['valuation_plus_1'] = np.sum(self.instance.equity_cf*discount_factor_plus_1_vector)



def create_IRR_curve(equity_cash_flows,series_end_period):

	irr_values = []

	# Iterate through each period and calculate the IRR up to that period
	for i in range(1, len(equity_cash_flows)+1):
		subset_cash_flows = equity_cash_flows.iloc[:i]
		subset_dates = pd.to_datetime(pd.Series(series_end_period).iloc[:i], dayfirst=True).dt.date

		try:
			irr = xirr(subset_dates, subset_cash_flows)*100
		except:
			irr = 0.0

		irr_values.append(max(irr,0,0))

	return irr_values 
			 

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





def determine_debt_constraint(debt_amount,debt_amount_gearing):
	if debt_amount > debt_amount_gearing:
		constraint = "Gearing"
	else: 
		constraint = "DSCR"
	return constraint
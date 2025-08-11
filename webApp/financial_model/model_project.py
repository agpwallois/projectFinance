from django.db import models
from datetime import date
from django.conf import settings
from authentication.models import Company, User

class Project(models.Model):

	def __str__(self):
		return f'{self.name}'
	
	COUNTRY_CHOICES = (
		('France', 'France'),
		('Spain', 'Spain'),
	)

	TECHNOLOGY_CHOICES = (
		('Solar - ground-mounted', 'Solar - ground-mounted'),
		('Solar - rooftop', 'Solar - rooftop'),
		('Wind', 'Wind'),
	)


	CONTRACT_CHOICES = (
		('FiT', 'FiT'),
		('CfD - E16', 'CfD - E16'),
		('CfD - E17', 'CfD - E17'),
		('CfD - AO', 'CfD - AO'),
		('Corporate PPA', 'Corporate PPA'),
	)

	PROJECT_STATUS = (
		('Development', 'Development'),
		('Operational', 'Operational'),
	)



	company = models.ForeignKey(Company, on_delete=models.CASCADE, default=1)
	creator = models.ForeignKey(User, on_delete=models.CASCADE, default=1)

	created_date = models.DateTimeField(auto_now_add=True)
	updated_date = models.DateTimeField(auto_now=True)
	
	name = models.fields.CharField(max_length=100)
	country = models.fields.CharField(choices=COUNTRY_CHOICES,max_length=100,default="France")
	technology = models.fields.CharField(choices=TECHNOLOGY_CHOICES,max_length=100,default="Solar")

	#Timing
	start_construction = models.fields.DateField(default=date(2022, 1, 1), blank=True, null=True)
	end_construction = models.fields.DateField(default=date(2022, 12, 31), blank=True, null=True)
	operating_life = models.fields.IntegerField(default="25")
	liquidation = models.fields.IntegerField(default="6")

	periodicity = models.fields.IntegerField(default="6")

	panels_capacity = models.fields.IntegerField(default="2500", blank=True, null=True)
	annual_degradation = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.4, blank=True, null=True)
	p50 = models.fields.IntegerField(default="1800")
	p75 = models.fields.IntegerField(default="1750")
	p90_10y = models.fields.IntegerField(default="1700")


	production_choice = models.fields.IntegerField(default="1")

	seasonality_m1 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.03)
	seasonality_m2 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.05)
	seasonality_m3 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.09)
	seasonality_m4 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.11)
	seasonality_m5 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.13)
	seasonality_m6 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.13)
	seasonality_m7 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.13)
	seasonality_m8 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.12)
	seasonality_m9 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.10)
	seasonality_m10 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.06)
	seasonality_m11 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.03)
	seasonality_m12 = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.02)

	costs_m1 = models.fields.IntegerField(default="200")
	costs_m2 = models.fields.IntegerField(default="0")
	costs_m3 = models.fields.IntegerField(default="500")
	costs_m4 = models.fields.IntegerField(default="300")
	costs_m5 = models.fields.IntegerField(default="0")
	costs_m6 = models.fields.IntegerField(default="1000")
	costs_m7 = models.fields.IntegerField(default="700")
	costs_m8 = models.fields.IntegerField(default="600")
	costs_m9 = models.fields.IntegerField(default="200")
	costs_m10 = models.fields.IntegerField(default="300")
	costs_m11 = models.fields.IntegerField(default="0")
	costs_m12 = models.fields.IntegerField(default="500")
	costs_m13 = models.fields.IntegerField(default="0")
	costs_m14 = models.fields.IntegerField(default="0")
	costs_m15 = models.fields.IntegerField(default="0")
	costs_m16 = models.fields.IntegerField(default="0")
	costs_m17 = models.fields.IntegerField(default="0")
	costs_m18 = models.fields.IntegerField(default="0")
	costs_m19 = models.fields.IntegerField(default="0")
	costs_m20 = models.fields.IntegerField(default="0")
	costs_m21 = models.fields.IntegerField(default="0")
	costs_m22 = models.fields.IntegerField(default="0")
	costs_m23 = models.fields.IntegerField(default="0")
	costs_m24 = models.fields.IntegerField(default="0")


	start_contract = models.fields.DateField(default=date(2023, 1, 1), blank=True, null=True)
	end_contract = models.fields.DateField(default=date(2042, 12, 31), blank=True, null=True)
	contract_price = models.fields.DecimalField(max_digits=6, decimal_places=2, default=130)
	contract_indexation_start_date = models.fields.DateField(default=date(2023, 1, 1), blank=True, null=True)
	index_rate_contract = models.fields.DecimalField(max_digits=4, decimal_places=2, default=2)

	price_elec_indexation_start_date = models.fields.DateField(default=date(2022, 1, 1), blank=True, null=True)
	index_rate_merchant = models.fields.DecimalField(max_digits=4, decimal_places=2, default=2)
	price_elec_choice = models.fields.IntegerField(default="1")


	price_elec_low_y1 = models.fields.IntegerField(default="50")
	price_elec_low_y2 = models.fields.IntegerField(default="50")
	price_elec_low_y3 = models.fields.IntegerField(default="50")
	price_elec_low_y4 = models.fields.IntegerField(default="50")
	price_elec_low_y5 = models.fields.IntegerField(default="50")
	price_elec_low_y6 = models.fields.IntegerField(default="50")
	price_elec_low_y7 = models.fields.IntegerField(default="50")
	price_elec_low_y8 = models.fields.IntegerField(default="50")
	price_elec_low_y9 = models.fields.IntegerField(default="50")
	price_elec_low_y10 = models.fields.IntegerField(default="50")
	price_elec_low_y11 = models.fields.IntegerField(default="50")
	price_elec_low_y12 = models.fields.IntegerField(default="50")
	price_elec_low_y13 = models.fields.IntegerField(default="50")
	price_elec_low_y14 = models.fields.IntegerField(default="50")
	price_elec_low_y15 = models.fields.IntegerField(default="50")
	price_elec_low_y16 = models.fields.IntegerField(default="50")
	price_elec_low_y17 = models.fields.IntegerField(default="50")
	price_elec_low_y18 = models.fields.IntegerField(default="50")
	price_elec_low_y19 = models.fields.IntegerField(default="50")
	price_elec_low_y20 = models.fields.IntegerField(default="50")
	price_elec_low_y21 = models.fields.IntegerField(default="50")
	price_elec_low_y22 = models.fields.IntegerField(default="50")
	price_elec_low_y23 = models.fields.IntegerField(default="50")
	price_elec_low_y24 = models.fields.IntegerField(default="50")
	price_elec_low_y25 = models.fields.IntegerField(default="50")
	price_elec_low_y26 = models.fields.IntegerField(default="50")
	price_elec_low_y27 = models.fields.IntegerField(default="50")
	price_elec_low_y28 = models.fields.IntegerField(default="50")
	price_elec_low_y29 = models.fields.IntegerField(default="50")
	price_elec_low_y30 = models.fields.IntegerField(default="50")
	price_elec_low_y31 = models.fields.IntegerField(default="50")
	price_elec_low_y32 = models.fields.IntegerField(default="50")
	price_elec_low_y33 = models.fields.IntegerField(default="50")
	price_elec_low_y34 = models.fields.IntegerField(default="50")
	price_elec_low_y35 = models.fields.IntegerField(default="50")
	price_elec_low_y36 = models.fields.IntegerField(default="50")
	price_elec_low_y37 = models.fields.IntegerField(default="50")
	price_elec_low_y38 = models.fields.IntegerField(default="50")
	price_elec_low_y39 = models.fields.IntegerField(default="50")
	price_elec_low_y40 = models.fields.IntegerField(default="50")
	price_elec_low_y41 = models.fields.IntegerField(default="50")
	price_elec_low_y42 = models.fields.IntegerField(default="50")

	price_elec_med_y1 = models.fields.IntegerField(default="100")
	price_elec_med_y2 = models.fields.IntegerField(default="100")
	price_elec_med_y3 = models.fields.IntegerField(default="100")
	price_elec_med_y4 = models.fields.IntegerField(default="100")
	price_elec_med_y5 = models.fields.IntegerField(default="100")
	price_elec_med_y6 = models.fields.IntegerField(default="100")
	price_elec_med_y7 = models.fields.IntegerField(default="100")
	price_elec_med_y8 = models.fields.IntegerField(default="100")
	price_elec_med_y9 = models.fields.IntegerField(default="100")
	price_elec_med_y10 = models.fields.IntegerField(default="100")
	price_elec_med_y11 = models.fields.IntegerField(default="100")
	price_elec_med_y12 = models.fields.IntegerField(default="100")
	price_elec_med_y13 = models.fields.IntegerField(default="100")
	price_elec_med_y14 = models.fields.IntegerField(default="100")
	price_elec_med_y15 = models.fields.IntegerField(default="100")
	price_elec_med_y16 = models.fields.IntegerField(default="100")
	price_elec_med_y17 = models.fields.IntegerField(default="100")
	price_elec_med_y18 = models.fields.IntegerField(default="100")
	price_elec_med_y19 = models.fields.IntegerField(default="100")
	price_elec_med_y20 = models.fields.IntegerField(default="100")
	price_elec_med_y21 = models.fields.IntegerField(default="100")
	price_elec_med_y22 = models.fields.IntegerField(default="100")
	price_elec_med_y23 = models.fields.IntegerField(default="100")
	price_elec_med_y24 = models.fields.IntegerField(default="100")
	price_elec_med_y25 = models.fields.IntegerField(default="100")
	price_elec_med_y26 = models.fields.IntegerField(default="100")
	price_elec_med_y27 = models.fields.IntegerField(default="100")
	price_elec_med_y28 = models.fields.IntegerField(default="100")
	price_elec_med_y29 = models.fields.IntegerField(default="100")
	price_elec_med_y30 = models.fields.IntegerField(default="100")
	price_elec_med_y31 = models.fields.IntegerField(default="100")
	price_elec_med_y32 = models.fields.IntegerField(default="100")
	price_elec_med_y33 = models.fields.IntegerField(default="100")
	price_elec_med_y34 = models.fields.IntegerField(default="100")
	price_elec_med_y35 = models.fields.IntegerField(default="100")
	price_elec_med_y36 = models.fields.IntegerField(default="100")
	price_elec_med_y37 = models.fields.IntegerField(default="100")
	price_elec_med_y38 = models.fields.IntegerField(default="100")
	price_elec_med_y39 = models.fields.IntegerField(default="100")
	price_elec_med_y40 = models.fields.IntegerField(default="100")
	price_elec_med_y41 = models.fields.IntegerField(default="100")
	price_elec_med_y42 = models.fields.IntegerField(default="100")


	price_elec_high_y1 = models.fields.IntegerField(default="150")
	price_elec_high_y2 = models.fields.IntegerField(default="150")
	price_elec_high_y3 = models.fields.IntegerField(default="150")
	price_elec_high_y4 = models.fields.IntegerField(default="150")
	price_elec_high_y5 = models.fields.IntegerField(default="150")
	price_elec_high_y6 = models.fields.IntegerField(default="150")
	price_elec_high_y7 = models.fields.IntegerField(default="150")
	price_elec_high_y8 = models.fields.IntegerField(default="150")
	price_elec_high_y9 = models.fields.IntegerField(default="150")
	price_elec_high_y10 = models.fields.IntegerField(default="150")
	price_elec_high_y11 = models.fields.IntegerField(default="150")
	price_elec_high_y12 = models.fields.IntegerField(default="150")
	price_elec_high_y13 = models.fields.IntegerField(default="150")
	price_elec_high_y14 = models.fields.IntegerField(default="150")
	price_elec_high_y15 = models.fields.IntegerField(default="150")
	price_elec_high_y16 = models.fields.IntegerField(default="150")
	price_elec_high_y17 = models.fields.IntegerField(default="150")
	price_elec_high_y18 = models.fields.IntegerField(default="150")
	price_elec_high_y19 = models.fields.IntegerField(default="150")
	price_elec_high_y20 = models.fields.IntegerField(default="150")
	price_elec_high_y21 = models.fields.IntegerField(default="150")
	price_elec_high_y22 = models.fields.IntegerField(default="150")
	price_elec_high_y23 = models.fields.IntegerField(default="150")
	price_elec_high_y24 = models.fields.IntegerField(default="150")
	price_elec_high_y25 = models.fields.IntegerField(default="150")
	price_elec_high_y26 = models.fields.IntegerField(default="150")
	price_elec_high_y27 = models.fields.IntegerField(default="150")
	price_elec_high_y28 = models.fields.IntegerField(default="150")
	price_elec_high_y29 = models.fields.IntegerField(default="150")
	price_elec_high_y30 = models.fields.IntegerField(default="150")
	price_elec_high_y31 = models.fields.IntegerField(default="150")
	price_elec_high_y32 = models.fields.IntegerField(default="150")
	price_elec_high_y33 = models.fields.IntegerField(default="150")
	price_elec_high_y34 = models.fields.IntegerField(default="150")
	price_elec_high_y35 = models.fields.IntegerField(default="150")
	price_elec_high_y36 = models.fields.IntegerField(default="150")
	price_elec_high_y37 = models.fields.IntegerField(default="150")
	price_elec_high_y38 = models.fields.IntegerField(default="150")
	price_elec_high_y39 = models.fields.IntegerField(default="150")
	price_elec_high_y40 = models.fields.IntegerField(default="150")
	price_elec_high_y41 = models.fields.IntegerField(default="150")
	price_elec_high_y42 = models.fields.IntegerField(default="150")

	opex = models.fields.IntegerField(default="50")
	opex_indexation_start_date = models.fields.DateField(default=date(2024, 1, 1), blank=True, null=True)
	index_rate_opex = models.fields.DecimalField(max_digits=4, decimal_places=2, default=2)

	debt_margin = models.fields.DecimalField(max_digits=4, decimal_places=2, default=5)
	"""debt_swap_rate = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	debt_swap_margin = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	debt_reference_rate_buffer = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	"""
	
	debt_upfront_fee = models.fields.DecimalField(max_digits=4, decimal_places=2, default=1.5)
	debt_commitment_fee = models.fields.DecimalField(max_digits=4, decimal_places=2, default=1)
	
	debt_target_DSCR = models.fields.DecimalField(max_digits=4, decimal_places=2, default=1.15)
	debt_gearing_max = models.fields.DecimalField(max_digits=4, decimal_places=2, default=90)
	"""debt_negative_tail = models.fields.IntegerField(default="0")"""

	debt_tenor = models.fields.IntegerField(default="20")

	corporate_income_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=30) 

	devfee_choice = models.fields.IntegerField(default="2")
	devfee_paid_FC = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	devfee_paid_COD = models.fields.DecimalField(max_digits=4, decimal_places=2, default=1)


	injection_choice = models.fields.IntegerField(default="1")
	subgearing = models.fields.DecimalField(max_digits=4, decimal_places=2, default=90)
	SHL_margin = models.fields.DecimalField(max_digits=4, decimal_places=2, default=3)


	"""calculation_detail = models.fields.IntegerField(default="2")
	"""
	payment_delay_revenues = models.fields.IntegerField(default="30")
	payment_delay_costs = models.fields.IntegerField(default="30")

	DSRA_choice = models.fields.IntegerField(default="1")
	"""initial_wc = models.fields.IntegerField(default="0")"""
	cash_min = models.fields.IntegerField(default="0")

	sensi_production = models.fields.DecimalField(max_digits=3, decimal_places=0, default=0)
	sensi_opex = models.fields.DecimalField(max_digits=3, decimal_places=0, default=10)
	sensi_inflation = models.fields.DecimalField(max_digits=3, decimal_places=0, default=1)

	sensi_production_sponsor = models.fields.DecimalField(max_digits=3, decimal_places=0, default=0)
	sensi_opex_sponsor = models.fields.DecimalField(max_digits=3, decimal_places=0, default=10)
	sensi_inflation_sponsor = models.fields.DecimalField(max_digits=3, decimal_places=0, default=1)

	sponsor_production_choice = models.fields.IntegerField(default="3")
	sponsor_price_elec_choice = models.fields.IntegerField(default="2")

	wind_turbine_installed = models.fields.IntegerField(default="3", blank=True, null=True)
	capacity_per_turbine = models.fields.IntegerField(default="2", blank=True, null=True)
	
	"""timeline_quarters_ceiling = models.BooleanField(default=False, null=True)
	"""

	panels_surface = models.fields.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
	dev_tax_taxable_base_solar = models.fields.DecimalField(max_digits=6, decimal_places=2, default=10, blank=True, null=True)
	dev_tax_taxable_base_wind = models.fields.DecimalField(max_digits=6, decimal_places=2, default=3000, blank=True, null=True)
	dev_tax_commune_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	dev_tax_department_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	

	archeological_tax_base_solar = models.fields.DecimalField(max_digits=8, decimal_places=2, default=10, blank=True, null=True)
	archeological_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0.4, blank=True, null=True)


	lease = models.fields.IntegerField(default="50")
	lease_indexation_start_date = models.fields.DateField(default=date(2024, 1, 1), blank=True, null=True)
	index_rate_lease = models.fields.DecimalField(max_digits=4, decimal_places=2, default=2)


	""" 
	tfpb_commune_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	tfpb_department_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	tfpb_additional_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	tfpb_region_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)

	cfe_discount_tax_base_y1 = models.fields.DecimalField(max_digits=4, decimal_places=2, default=50)
	cfe_discount_tax_base = models.fields.DecimalField(max_digits=4, decimal_places=2, default=30)
	cfe_mgt_fee = models.fields.DecimalField(max_digits=4, decimal_places=2, default=3)
	cfe_instal_q1= models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	cfe_instal_q2= models.fields.DecimalField(max_digits=4, decimal_places=2, default=50)
	cfe_instal_q3= models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	cfe_instal_q4= models.fields.DecimalField(max_digits=4, decimal_places=2, default=50)
	cfe_commune_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	cfe_intercommunal_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	cfe_specific_eqp_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	cfe_localCCI_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0)
	"""

	project_status = models.fields.CharField(choices=PROJECT_STATUS,max_length=100,default="Development")
	discount_factor_valuation = models.fields.DecimalField(max_digits=4, decimal_places=2, default=7)

	"""contract = models.fields.CharField(choices=CONTRACT_CHOICES,max_length=100,default="CfD - AO")
	rotor_diameter = models.fields.DecimalField(max_digits=4, decimal_places=2, default=92)
	"""

	sponsor_irr = models.fields.DecimalField(max_digits=10, decimal_places=2, default=0)
	valuation = models.fields.DecimalField(max_digits=10, decimal_places=0, default=0)




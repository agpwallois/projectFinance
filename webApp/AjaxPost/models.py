from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
import datetime
from django.core.exceptions import ValidationError



  

class Project(models.Model):

	def __str__(self):
		return f'{self.name}'

	class Production(models.TextChoices):
		P50 = 'P50'
		P90 = 'P90'
		P99 = 'P99'

	class ElecPrice(models.TextChoices):
		Low = 'Low'
		Medium = 'Medium'
		High = 'High'


	name = models.fields.CharField(max_length=100)

	start_construction = models.fields.DateField(default=datetime.date.today, blank=True, null=True)
	end_construction = models.fields.DateField(default=datetime.date.today, blank=True, null=True)
	operating_life = models.fields.IntegerField(default="20")
	periodicity = models.fields.IntegerField(default="6")

	panels_capacity = models.fields.IntegerField(default="2000")
	annual_degradation = models.fields.DecimalField(max_digits=5, decimal_places=3, default=0.04)
	p50 = models.fields.IntegerField(default="2000")
	p90_10y = models.fields.IntegerField(default="2000")
	P99_10y = models.fields.IntegerField(default="2000")
	production_choice = models.fields.IntegerField(default="2")

	availability = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0.99)
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

	costs_m1 = models.fields.IntegerField(default="0")
	costs_m2 = models.fields.IntegerField(default="0")
	costs_m3 = models.fields.IntegerField(default="0")
	costs_m4 = models.fields.IntegerField(default="0")
	costs_m5 = models.fields.IntegerField(default="0")
	costs_m6 = models.fields.IntegerField(default="0")
	costs_m7 = models.fields.IntegerField(default="0")
	costs_m8 = models.fields.IntegerField(default="0")
	costs_m9 = models.fields.IntegerField(default="0")
	costs_m10 = models.fields.IntegerField(default="0")
	costs_m11 = models.fields.IntegerField(default="0")
	costs_m12 = models.fields.IntegerField(default="0")

	start_contract = models.fields.DateField(default=datetime.date.today, blank=True, null=True)
	end_contract = models.fields.DateField(default=datetime.date.today, blank=True, null=True)
	contract_price = models.fields.DecimalField(max_digits=6, decimal_places=2, default=58)
	contract_indexation_start_date = models.fields.DateField(default=datetime.date.today, blank=True, null=True)
	contract_indexation = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0.05)

	price_elec_indexation_start_date = models.fields.DateField(default=datetime.date.today, blank=True, null=True)
	price_elec_indexation = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0.05)
	price_elec_choice = models.fields.IntegerField(default="2")


	price_elec_low_y1 = models.fields.IntegerField(default="0")
	price_elec_low_y2 = models.fields.IntegerField(default="0")
	price_elec_low_y3 = models.fields.IntegerField(default="0")
	price_elec_low_y4 = models.fields.IntegerField(default="0")
	price_elec_low_y5 = models.fields.IntegerField(default="0")
	price_elec_low_y6 = models.fields.IntegerField(default="0")
	price_elec_low_y7 = models.fields.IntegerField(default="0")
	price_elec_low_y8 = models.fields.IntegerField(default="0")
	price_elec_low_y9 = models.fields.IntegerField(default="0")
	price_elec_low_y10 = models.fields.IntegerField(default="0")
	price_elec_low_y11 = models.fields.IntegerField(default="0")
	price_elec_low_y12 = models.fields.IntegerField(default="0")
	price_elec_low_y13 = models.fields.IntegerField(default="0")
	price_elec_low_y14 = models.fields.IntegerField(default="0")
	price_elec_low_y15 = models.fields.IntegerField(default="0")
	price_elec_low_y16 = models.fields.IntegerField(default="0")
	price_elec_low_y17 = models.fields.IntegerField(default="0")
	price_elec_low_y18 = models.fields.IntegerField(default="0")
	price_elec_low_y19 = models.fields.IntegerField(default="0")
	price_elec_low_y20 = models.fields.IntegerField(default="0")
	price_elec_low_y21 = models.fields.IntegerField(default="0")
	price_elec_low_y22 = models.fields.IntegerField(default="0")
	price_elec_low_y23 = models.fields.IntegerField(default="0")
	price_elec_low_y24 = models.fields.IntegerField(default="0")
	price_elec_low_y25 = models.fields.IntegerField(default="0")
	price_elec_low_y26 = models.fields.IntegerField(default="0")
	price_elec_low_y27 = models.fields.IntegerField(default="0")
	price_elec_low_y28 = models.fields.IntegerField(default="0")
	price_elec_low_y29 = models.fields.IntegerField(default="0")
	price_elec_low_y30 = models.fields.IntegerField(default="0")

	price_elec_med_y1 = models.fields.IntegerField(default="0")
	price_elec_med_y2 = models.fields.IntegerField(default="0")
	price_elec_med_y3 = models.fields.IntegerField(default="0")
	price_elec_med_y4 = models.fields.IntegerField(default="0")
	price_elec_med_y5 = models.fields.IntegerField(default="0")
	price_elec_med_y6 = models.fields.IntegerField(default="0")
	price_elec_med_y7 = models.fields.IntegerField(default="0")
	price_elec_med_y8 = models.fields.IntegerField(default="0")
	price_elec_med_y9 = models.fields.IntegerField(default="0")
	price_elec_med_y10 = models.fields.IntegerField(default="0")
	price_elec_med_y11 = models.fields.IntegerField(default="0")
	price_elec_med_y12 = models.fields.IntegerField(default="0")
	price_elec_med_y13 = models.fields.IntegerField(default="0")
	price_elec_med_y14 = models.fields.IntegerField(default="0")
	price_elec_med_y15 = models.fields.IntegerField(default="0")
	price_elec_med_y16 = models.fields.IntegerField(default="0")
	price_elec_med_y17 = models.fields.IntegerField(default="0")
	price_elec_med_y18 = models.fields.IntegerField(default="0")
	price_elec_med_y19 = models.fields.IntegerField(default="0")
	price_elec_med_y20 = models.fields.IntegerField(default="0")
	price_elec_med_y21 = models.fields.IntegerField(default="0")
	price_elec_med_y22 = models.fields.IntegerField(default="0")
	price_elec_med_y23 = models.fields.IntegerField(default="0")
	price_elec_med_y24 = models.fields.IntegerField(default="0")
	price_elec_med_y25 = models.fields.IntegerField(default="0")
	price_elec_med_y26 = models.fields.IntegerField(default="0")
	price_elec_med_y27 = models.fields.IntegerField(default="0")
	price_elec_med_y28 = models.fields.IntegerField(default="0")
	price_elec_med_y29 = models.fields.IntegerField(default="0")
	price_elec_med_y30 = models.fields.IntegerField(default="0")

	price_elec_high_y1 = models.fields.IntegerField(default="0")
	price_elec_high_y2 = models.fields.IntegerField(default="0")
	price_elec_high_y3 = models.fields.IntegerField(default="0")
	price_elec_high_y4 = models.fields.IntegerField(default="0")
	price_elec_high_y5 = models.fields.IntegerField(default="0")
	price_elec_high_y6 = models.fields.IntegerField(default="0")
	price_elec_high_y7 = models.fields.IntegerField(default="0")
	price_elec_high_y8 = models.fields.IntegerField(default="0")
	price_elec_high_y9 = models.fields.IntegerField(default="0")
	price_elec_high_y10 = models.fields.IntegerField(default="0")
	price_elec_high_y11 = models.fields.IntegerField(default="0")
	price_elec_high_y12 = models.fields.IntegerField(default="0")
	price_elec_high_y13 = models.fields.IntegerField(default="0")
	price_elec_high_y14 = models.fields.IntegerField(default="0")
	price_elec_high_y15 = models.fields.IntegerField(default="0")
	price_elec_high_y16 = models.fields.IntegerField(default="0")
	price_elec_high_y17 = models.fields.IntegerField(default="0")
	price_elec_high_y18 = models.fields.IntegerField(default="0")
	price_elec_high_y19 = models.fields.IntegerField(default="0")
	price_elec_high_y20 = models.fields.IntegerField(default="0")
	price_elec_high_y21 = models.fields.IntegerField(default="0")
	price_elec_high_y22 = models.fields.IntegerField(default="0")
	price_elec_high_y23 = models.fields.IntegerField(default="0")
	price_elec_high_y24 = models.fields.IntegerField(default="0")
	price_elec_high_y25 = models.fields.IntegerField(default="0")
	price_elec_high_y26 = models.fields.IntegerField(default="0")
	price_elec_high_y27 = models.fields.IntegerField(default="0")
	price_elec_high_y28 = models.fields.IntegerField(default="0")
	price_elec_high_y29 = models.fields.IntegerField(default="0")
	price_elec_high_y30 = models.fields.IntegerField(default="0")

	opex = models.fields.IntegerField()
	opex_indexation_start_date = models.fields.DateField(default=datetime.date.today, blank=True, null=True)
	opex_indexation = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0.05)

	debt_margin = models.fields.DecimalField(max_digits=4, decimal_places=2, default=5)
	debt_swap_rate = models.fields.DecimalField(max_digits=4, decimal_places=2, default=2)
	debt_swap_margin = models.fields.DecimalField(max_digits=4, decimal_places=2, default=0.5)
	debt_reference_rate_buffer = models.fields.DecimalField(max_digits=4, decimal_places=2, default=1)
	
	debt_upfront_fee = models.fields.DecimalField(max_digits=4, decimal_places=2, default=5)
	debt_commitment_fee = models.fields.DecimalField(max_digits=4, decimal_places=2, default=5)
	
	debt_target_DSCR = models.fields.DecimalField(max_digits=4, decimal_places=2, default=1.15)
	debt_gearing_max = models.fields.DecimalField(max_digits=4, decimal_places=2, default=90)
	debt_negative_tail = models.fields.IntegerField(default="0")

	debt_tenor = models.fields.IntegerField(default="20")

	corporate_income_tax = models.fields.DecimalField(max_digits=4, decimal_places=2, default=30) 


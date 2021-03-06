from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
import datetime
  

class SProject(models.Model):

	def __str__(self):
		return f'{self.name}'

	class Type(models.TextChoices):
		Wind = 'Wind'
		Solar = 'Solar'
		Road = 'Road'

	name = models.fields.CharField(max_length=100)
	genre = models.fields.CharField(choices=Type.choices, max_length=5)
	country = models.fields.CharField(max_length=20)

	start_construction = models.fields.DateField(default=datetime.date.today, blank=True, null=True)
	end_construction = models.fields.DateField(default=datetime.date.today, blank=True, null=True)
	operating_life = models.fields.IntegerField(default="20")
	periodicity = models.fields.IntegerField(default="3")


	panels_capacity = models.fields.IntegerField(default="2000")
	annual_degradation = models.fields.DecimalField(max_digits=4, decimal_places=0, default=2)
	p50 = models.fields.IntegerField(default="2000")
	p90_10y = models.fields.IntegerField(default="2000")
	P99_10y = models.fields.IntegerField(default="2000")
	availability = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m1 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m2 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m3 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m4 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m5 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m6 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m7 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m8 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m9 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m10 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m11 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)
	seasonality_m12 = models.fields.DecimalField(max_digits=4, decimal_places=0, default=0)


	costs_at_NTP = models.fields.IntegerField(default="0")
	costs_at_FC = models.fields.IntegerField(default="0")
	costs_at_COD = models.fields.IntegerField(default="0")
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

	revenues = models.fields.IntegerField()
	inflation = models.fields.FloatField()
	opex = models.fields.IntegerField()
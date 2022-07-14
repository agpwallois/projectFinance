from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from datetime import date
from datetime import datetime    

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

	start_construction = models.fields.DateTimeField(null=True, blank=True)
	end_construction = models.fields.DateTimeField(null=True, blank=True)
	operating_life = models.fields.IntegerField(default="20")
	costs_at_NTP = models.fields.IntegerField(default="0")
	costs_at_FC = models.fields.IntegerField(default="0")
	costs_month_1 = models.fields.IntegerField(default="0")
	costs_month_2 = models.fields.IntegerField(default="0")
	costs_month_3 = models.fields.IntegerField(default="0")
	costs_month_4 = models.fields.IntegerField(default="0")
	costs_month_5 = models.fields.IntegerField(default="0")
	costs_month_6 = models.fields.IntegerField(default="0")
	costs_month_7 = models.fields.IntegerField(default="0")
	costs_month_8 = models.fields.IntegerField(default="0")
	costs_month_9 = models.fields.IntegerField(default="0")
	costs_month_10 = models.fields.IntegerField(default="0")
	costs_month_11 = models.fields.IntegerField(default="0")
	costs_month_12 = models.fields.IntegerField(default="0")

	start_year = models.fields.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(3000)])
	length = models.fields.IntegerField()
	periodicity = models.fields.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
	revenues = models.fields.IntegerField()
	inflation = models.fields.FloatField()
	opex = models.fields.IntegerField()
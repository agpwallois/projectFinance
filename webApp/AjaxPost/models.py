from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from datetime import date

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
	start_year = models.fields.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(3000)])
	length = models.fields.IntegerField()
	periodicity = models.fields.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
	revenues = models.fields.IntegerField()
	inflation = models.fields.FloatField()
	opex = models.fields.IntegerField()
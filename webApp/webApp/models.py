from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.http import JsonResponse
from tabulate import tabulate
import numpy as np
from django.views.generic.list import ListView
from datetime import date

# Create your models here.

class Project(models.Model):

    def __str__(self):
     return f'{self.name}'

    class Type(models.TextChoices):
        Wind = 'Wind'
        Solar = 'Solar'
        Road = 'Road'

    name = models.fields.CharField(max_length=100)
    genre = models.fields.CharField(choices=Type.choices, max_length=5)
    start_year = models.fields.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(3000)])
    length = models.fields.IntegerField()
    periodicity = models.fields.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    revenues = models.fields.IntegerField()
    inflation = models.fields.FloatField()
    opex = models.fields.IntegerField()


    def income_statement(self):
        year = np.array([])
        date = np.array([])
        revenues_real = np.array([])
        inflation = np.array([])
        opex = np.array([])

        for i in range(1,int(self.length)): 
            year = np.append(year,i)
            date = np.append(date,int(self.start_year)+i-1)
            revenues_real = np.append(revenues_real,self.revenues)
            inflation = np.append(inflation,(1+int(self.inflation)/100)**i)
            opex = np.append(opex,self.opex)

        revenues_nominal = np.multiply(revenues_real, inflation)
        EBITDA = np.subtract(revenues_nominal, opex)

        m=[
        year,
        date,
        inflation,
        revenues_real,
        revenues_nominal,
        opex, 
        EBITDA
        ]

        return m

    def financing_plan(self):
        year = np.array([])
        date = np.array([])
        revenues_real = np.array([])
        inflation = np.array([])
        opex = np.array([])

        for i in range(1,int(self.length)): 
            year = np.append(year,i)
            date = np.append(date,int(self.start_year)+i-1)
            revenues_real = np.append(revenues_real,self.revenues)
            inflation = np.append(inflation,(1+int(self.inflation)/100)**i)
            opex = np.append(opex,self.opex)

        revenues_nominal = np.multiply(revenues_real, inflation)
        EBITDA = np.subtract(revenues_nominal, opex)

        m=[
        year,
        date,
        inflation,
        revenues_real,
        revenues_nominal,
        opex, 
        EBITDA
        ]

        return m



class webApp(models.Model):
    title = models.fields.CharField(max_length=100)
    project = models.ForeignKey(Project, null=True, on_delete=models.SET_NULL)
    
    def __str__(self):
     return f'{self.name}'

from django.test import TestCase, Client

from .models import FinancialModel

class BasicTests(TestCase):
	def test_1(self):
		self.assertTrue(1==1) 


	def test_2(self):
		try:
			raise Exception('failure in test_2')
		except Exception as e:
			self.fail(e)

class TestModels(TestCase):
	def test_financial_model(self):
		financial_model = FinancialModel(
			

			)
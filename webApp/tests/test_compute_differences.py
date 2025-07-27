import unittest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
import sys
import os
import django
from django.test import TestCase
from django.conf import settings

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webApp.settings')
django.setup()

from financial_model.views import FinancialModelView


class TestComputeDifferences(TestCase):
    """Unit tests for the _compute_differences method"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.financial_model_view = FinancialModelView()
        
    def test_basic_percentage_differences(self):
        """Test basic functionality with percentage values"""
        table_sensi = {
            '': ['Min DSCR', 'Avg. DSCR', 'Min LLCR', 'Audit'],
            'lender_base_case': ['3.23x', '3.31x', '3.35x', False],
            'lender_sensi_prod': ['2.57x', '2.98x', '2.50x', False],
            'lender_sensi_inf': ['2.80x', '3.10x', '3.00x', False],
            'lender_sensi_opex': ['2.57x', '2.98x', '2.50x', False],
        }
        
        result = self.financial_model_view._compute_differences(table_sensi)
        
        # Check that result is a dictionary with row keys
        self.assertIsInstance(result, dict)
        self.assertIn('lender_base_case', result)
        self.assertIn('lender_sensi_prod', result)
        self.assertIn('lender_sensi_inf', result)
        self.assertIn('lender_sensi_opex', result)
               
        # Check production sensitivity differences
        prod_row = result['lender_sensi_prod']
        self.assertEqual(prod_row['Min DSCR'], '-0.66x')  # 2.57x - 3.23x = -0.66x
        self.assertEqual(prod_row['Avg. DSCR'], '-0.33x')  # 2.98x - 3.31x = -0.33x
        self.assertEqual(prod_row['Min LLCR'], '-0.85x')   # 2.50x - 3.35x = -0.85x
        
        # Check inflation sensitivity differences
        inf_row = result['lender_sensi_inf']
        self.assertEqual(inf_row['Min DSCR'], '-0.43x')  # 2.80x - 3.23x = -0.43x
        self.assertEqual(inf_row['Avg. DSCR'], '-0.21x')  # 3.10x - 3.31x = -0.21x
        self.assertEqual(inf_row['Min LLCR'], '-0.35x')   # 3.00x - 3.35x = -0.35x

        # Check opex sensitivity differences
        opex_row = result['lender_sensi_opex']
        self.assertEqual(opex_row['Min DSCR'], '-0.66x')  
        self.assertEqual(opex_row['Avg. DSCR'], '-0.33x')  
        self.assertEqual(opex_row['Min LLCR'], '-0.85x')   


def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
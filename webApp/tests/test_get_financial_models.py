import unittest
import sys
import os
import django
from unittest.mock import MagicMock, patch
from django.test import TestCase

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webApp.settings')
django.setup()

from financial_model.views import FinancialModelView
from financial_model.model_project import Project
from financial_model.model_solar_financial_model import SolarFinancialModel


class TestGetFinancialModels(TestCase):
    """Simple test for _get_financial_models method"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.view = FinancialModelView()
        self.mock_project = MagicMock(spec=Project)
    
    @patch('financial_model.views.SolarFinancialModel.objects.get')
    def test_get_financial_models_retrieves_8_models(self, mock_get):
        """Test that _get_financial_models retrieves all 8 financial models"""
        # Create 8 mock models
        mock_models = {}
        for scenario_id in self.view.FINANCIAL_MODEL_SCENARIOS.keys():
            mock_model = MagicMock(spec=SolarFinancialModel)
            mock_model.identifier = scenario_id
            mock_models[scenario_id] = mock_model
        
        # Configure mock to return the appropriate model for each scenario
        mock_get.side_effect = lambda project, identifier: mock_models[identifier]
        
        # Call the method
        result = self.view._get_financial_models(self.mock_project)
        
        # Verify 8 models are returned
        self.assertEqual(len(result), 8)
        
        # Verify all expected scenarios are present
        expected_scenarios = [
            'lender_base_case', 'lender_sensi_prod', 'lender_sensi_inf', 'lender_sensi_opex',
            'sponsor_base_case', 'sponsor_sensi_prod', 'sponsor_sensi_inf', 'sponsor_sensi_opex'
        ]
        
        for scenario_id in expected_scenarios:
            self.assertIn(scenario_id, result)
            self.assertEqual(result[scenario_id].identifier, scenario_id)


if __name__ == '__main__':
    unittest.main(verbosity=2)
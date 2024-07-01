from .FinancialModel import FinancialModel


class SensitivityAnalysis:
    def __init__(self, FinancialModel):
        self.financial_model = FinancialModel

    def apply_sensitivity(self, revenue_change=0, opex_change=0, capex_change=0):
        original_revenue = self.financial_model.revenue
        original_opex = self.financial_model.opex
        original_capex = self.financial_model.capex

        self.financial_model.revenue *= (1 + revenue_change)
        self.financial_model.opex *= (1 + opex_change)
        self.financial_model.capex *= (1 + capex_change)

        result = self.financial_model.build_financial_model()
	
        # Restore original values
        self.financial_model.revenue = original_revenue
        self.financial_model.opex = original_opex
        self.financial_model.capex = original_capex

        return result
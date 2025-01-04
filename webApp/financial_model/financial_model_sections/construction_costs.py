import numpy as np

class FinancialModelConstructionCosts:
    def __init__(self, instance):
        self.instance = instance


    def initialize(self):
        """
        Initialize the construction costs series in the financial model.
        """

        self.instance.comp_local_taxes()

        self.instance.financial_model['construction_costs'] = {}
        self.instance.financial_model['construction_costs']['total'] = (
            np.hstack([
                self.instance.construction_costs_assumptions,
                np.zeros(len(self.instance.financial_model['flags']['operations']) - len(self.instance.construction_costs_assumptions))
            ]) * self.instance.financial_model['flags']['construction']
        )
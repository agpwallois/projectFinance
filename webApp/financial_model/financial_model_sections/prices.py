from dataclasses import dataclass
import pandas as pd
from typing import Dict, Any, List, Union

@dataclass
class Prices:
	"""
	Handles price calculations for financial models, including merchant and contract prices
	in both real and nominal terms.
	"""
	instance: Any  # Type hint for the instance object

	def initialize(self, model_type: str) -> None:
		"""
		Initialize price calculations based on the model type.
		
		Args:
			model_type (str): Type of model ('lender' or other)
		"""
		self._set_merchant_prices(model_type)
		self._set_contract_prices()
		
	def _get_electricity_price_choice(self, model_type: str) -> int:
		"""
		Determine the electricity price choice based on model type.
		
		Args:
			model_type (str): Type of model ('lender' or other)
			
		Returns:
			int: Selected price choice
		"""
		return (self.instance.project.price_elec_choice 
				if model_type not in {'sponsor', 'sensi_production_sponsor', 'sensi_inflation_sponsor', 'sensi_opex_sponsor'} 
				else self.instance.project.sponsor_price_elec_choice)

	def _get_selected_prices(self, model_type: str) -> Dict[str, float]:
		"""
		Get the selected electricity prices based on the price choice.
		
		Args:
			model_type (str): Type of model ('lender' or other)
			
		Returns:
			Dict[str, float]: Selected electricity prices dictionary
		"""
		prices_mapping = {
			1: self.instance.price_elec_low,
			2: self.instance.price_elec_med,
			3: self.instance.price_elec_high
		}
		choice = self._get_electricity_price_choice(model_type)
		return prices_mapping.get(choice, self.instance.price_elec_low)

	def _create_electricity_price_series(self, years: List[int], prices: Dict[str, float]) -> List[float]:
		"""
		Create a series of electricity prices based on years and price dictionary.
		
		Args:
			years (List[int]): List of years
			prices (Dict[str, float]): Dictionary of prices by year
			
		Returns:
			List[float]: List of electricity prices
		"""
		return [prices.get(str(year), 0) for year in years]

	def _set_merchant_prices(self, model_type: str) -> None:
		"""
		Calculate and set merchant prices in both real and nominal terms.
		
		Args:
			model_type (str): Type of model ('lender' or other)
		"""
		selected_prices = self._get_selected_prices(model_type)
		years = self.instance.financial_model['time_series']['series_end_period_year']
		
		# Initialize price dictionary if it doesn't exist
		self.instance.financial_model['price'] = self.instance.financial_model.get('price', {})
		
		# Calculate merchant prices
		merchant_real = pd.Series(self._create_electricity_price_series(years, selected_prices))
		self.instance.financial_model['price']['merchant_real'] = merchant_real
		self.instance.financial_model['price']['merchant_nom'] = (
			merchant_real * self.instance.financial_model['indexation']['merchant']
		)

	def _set_contract_prices(self) -> None:
		"""Calculate and set contract prices in both real and nominal terms."""
		contract_flags = pd.Series(self.instance.financial_model['flags']['contract'])
		contract_real = pd.Series(self.instance.contract_price * contract_flags).astype(float)
		
		self.instance.financial_model['price']['contract_real'] = contract_real
		self.instance.financial_model['price']['contract_nom'] = (
			contract_real * self.instance.financial_model['indexation']['contract']
		)
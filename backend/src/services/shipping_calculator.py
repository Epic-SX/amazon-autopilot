"""
International Shipping Cost Calculator
Integrates with Mad Beast and Import Com for shipping cost calculation
"""
from typing import Dict, Optional, Any
import requests
import os
from dotenv import load_dotenv

load_dotenv()

class ShippingCalculator:
    """
    Calculates international shipping costs using Mad Beast or Import Com
    """
    
    def __init__(self):
        self.mad_beast_api_key = os.getenv('MAD_BEAST_API_KEY', '')
        self.mad_beast_api_url = os.getenv('MAD_BEAST_API_URL', 'https://api.madbeast.com')
        self.import_com_api_key = os.getenv('IMPORT_COM_API_KEY', '')
        self.import_com_api_url = os.getenv('IMPORT_COM_API_URL', 'https://api.import-com.com')
        self.preferred_provider = os.getenv('SHIPPING_PROVIDER', 'mad_beast')  # 'mad_beast' or 'import_com'
    
    def calculate_shipping(
        self,
        weight_kg: float,
        dimensions_cm: Dict[str, float],
        destination_country: str = 'JP',
        source_country: str = 'US',
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate international shipping cost
        
        Args:
            weight_kg: Weight in kilograms
            dimensions_cm: Dict with 'length', 'width', 'height' in cm
            destination_country: Destination country code (default: JP)
            source_country: Source country code (default: US)
            provider: 'mad_beast' or 'import_com' (optional, uses preferred if not specified)
        
        Returns:
            Dict with shipping_cost, provider, and details
        """
        provider = provider or self.preferred_provider
        
        if provider == 'mad_beast':
            return self._calculate_mad_beast(weight_kg, dimensions_cm, destination_country, source_country)
        elif provider == 'import_com':
            return self._calculate_import_com(weight_kg, dimensions_cm, destination_country, source_country)
        else:
            # Fallback to estimation
            return self._estimate_shipping(weight_kg, dimensions_cm)
    
    def _calculate_mad_beast(
        self,
        weight_kg: float,
        dimensions_cm: Dict[str, float],
        destination_country: str,
        source_country: str
    ) -> Dict[str, Any]:
        """
        Calculate shipping using Mad Beast API
        """
        if not self.mad_beast_api_key:
            # Fallback to estimation if API key not configured
            return self._estimate_shipping(weight_kg, dimensions_cm)
        
        try:
            # Calculate volumetric weight
            length = dimensions_cm.get('length', 0)
            width = dimensions_cm.get('width', 0)
            height = dimensions_cm.get('height', 0)
            volumetric_weight = (length * width * height) / 5000
            chargeable_weight = max(weight_kg, volumetric_weight)
            
            # API call to Mad Beast (placeholder - adjust based on actual API)
            # This is a simplified example
            payload = {
                'weight': chargeable_weight,
                'length': length,
                'width': width,
                'height': height,
                'from': source_country,
                'to': destination_country
            }
            
            headers = {
                'Authorization': f'Bearer {self.mad_beast_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Uncomment when API is available
            # response = requests.post(
            #     f'{self.mad_beast_api_url}/calculate',
            #     json=payload,
            #     headers=headers,
            #     timeout=10
            # )
            # response.raise_for_status()
            # data = response.json()
            # 
            # return {
            #     'shipping_cost': data.get('cost', 0),
            #     'provider': 'mad_beast',
            #     'estimated_days': data.get('estimated_days', 7),
            #     'service_type': data.get('service_type', 'standard')
            # }
            
            # Fallback to estimation for now
            return self._estimate_shipping(weight_kg, dimensions_cm)
            
        except Exception as e:
            print(f"Error calculating Mad Beast shipping: {e}")
            return self._estimate_shipping(weight_kg, dimensions_cm)
    
    def _calculate_import_com(
        self,
        weight_kg: float,
        dimensions_cm: Dict[str, float],
        destination_country: str,
        source_country: str
    ) -> Dict[str, Any]:
        """
        Calculate shipping using Import Com API
        """
        if not self.import_com_api_key:
            return self._estimate_shipping(weight_kg, dimensions_cm)
        
        try:
            # Similar structure to Mad Beast
            length = dimensions_cm.get('length', 0)
            width = dimensions_cm.get('width', 0)
            height = dimensions_cm.get('height', 0)
            volumetric_weight = (length * width * height) / 5000
            chargeable_weight = max(weight_kg, volumetric_weight)
            
            # API call to Import Com (placeholder)
            # response = requests.post(...)
            
            # Fallback to estimation for now
            return self._estimate_shipping(weight_kg, dimensions_cm)
            
        except Exception as e:
            print(f"Error calculating Import Com shipping: {e}")
            return self._estimate_shipping(weight_kg, dimensions_cm)
    
    def _estimate_shipping(
        self,
        weight_kg: float,
        dimensions_cm: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Estimate shipping cost when API is not available
        Uses standard shipping rate tables
        """
        length = dimensions_cm.get('length', 0)
        width = dimensions_cm.get('width', 0)
        height = dimensions_cm.get('height', 0)
        
        # Calculate volumetric weight
        volumetric_weight_kg = (length * width * height) / 5000
        chargeable_weight_kg = max(weight_kg, volumetric_weight_kg)
        
        # Standard estimation rates (yen per kg, minimum charge)
        base_rate_per_kg = 1000.0
        minimum_charge = 2000.0
        
        estimated_cost = max(minimum_charge, chargeable_weight_kg * base_rate_per_kg)
        
        return {
            'shipping_cost': estimated_cost,
            'provider': 'estimated',
            'estimated_days': 7,
            'service_type': 'standard',
            'chargeable_weight_kg': chargeable_weight_kg,
            'volumetric_weight_kg': volumetric_weight_kg,
            'actual_weight_kg': weight_kg
        }



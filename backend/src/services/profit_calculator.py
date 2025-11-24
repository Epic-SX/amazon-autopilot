"""
Profit Calculator Service
Calculates profit including all costs: international shipping, customs, transfer fees, Amazon fees, etc.
"""
from typing import Dict, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
import os
from dotenv import load_dotenv

load_dotenv()

class ProfitCalculator:
    """
    Calculates profit for Amazon dropshipping products
    Considers all costs: purchase price, international shipping, customs, transfer fees, Amazon fees, etc.
    """
    
    def __init__(self):
        # Default exchange rate (USD to JPY) - should be updated from API
        self.default_usd_to_jpy_rate = float(os.getenv('USD_TO_JPY_RATE', '150.0'))
        
        # Default fees (can be configured)
        self.default_transfer_fee = float(os.getenv('DEFAULT_TRANSFER_FEE', '500.0'))  # 転送手数料
        self.default_customs_clearance_fee = float(os.getenv('DEFAULT_CUSTOMS_CLEARANCE_FEE', '2000.0'))  # 通関手数料
        self.default_amazon_referral_fee_rate = float(os.getenv('AMAZON_REFERRAL_FEE_RATE', '0.15'))  # 15% referral fee
        self.default_amazon_variable_closing_fee = float(os.getenv('AMAZON_VARIABLE_CLOSING_FEE', '0.0'))  # Variable closing fee
        
        # Consumption tax rate (10% in Japan)
        self.consumption_tax_rate = 0.10
        
    def calculate_profit(
        self,
        us_price: float,
        jp_listing_price: float,
        weight_kg: Optional[float] = None,
        dimensions_cm: Optional[Dict[str, float]] = None,
        international_shipping_cost: Optional[float] = None,
        domestic_shipping_cost: Optional[float] = None,
        customs_fee: Optional[float] = None,
        transfer_fee: Optional[float] = None,
        customs_clearance_fee: Optional[float] = None,
        exchange_rate: Optional[float] = None,
        amazon_fee_override: Optional[float] = None,
        calculate_shipping: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate profit with all costs considered
        
        Args:
            us_price: Price in USD from US Amazon
            jp_listing_price: Listing price in JPY on Japan Amazon
            weight_kg: Weight in kilograms
            dimensions_cm: Dict with 'length', 'width', 'height' in cm
            international_shipping_cost: Pre-calculated international shipping cost (optional)
            domestic_shipping_cost: Pre-calculated domestic shipping cost (optional)
            customs_fee: Pre-calculated customs fee (optional)
            transfer_fee: Transfer service fee (optional, uses default if not provided)
            customs_clearance_fee: Customs clearance fee (optional, uses default if not provided)
            exchange_rate: USD to JPY exchange rate (optional, uses default if not provided)
            amazon_fee_override: Override Amazon fee calculation (optional)
            calculate_shipping: Whether to calculate shipping costs if not provided
        
        Returns:
            Dict with profit_amount, profit_rate, and breakdown of all costs
        """
        # Use provided exchange rate or default
        rate = exchange_rate or self.default_usd_to_jpy_rate
        
        # Convert US price to JPY
        us_price_jpy = us_price * rate
        
        # Calculate international shipping if not provided and calculation is enabled
        if international_shipping_cost is None and calculate_shipping:
            if weight_kg and dimensions_cm:
                international_shipping_cost = self._estimate_international_shipping(
                    weight_kg, dimensions_cm
                )
            else:
                international_shipping_cost = 0.0
        
        # Calculate domestic shipping if not provided
        if domestic_shipping_cost is None:
            domestic_shipping_cost = 0.0  # Usually included in Amazon FBA or customer pays
        
        # Calculate customs fee if not provided
        if customs_fee is None:
            customs_fee = self._calculate_customs_fee(us_price_jpy)
        
        # Use provided fees or defaults
        transfer_fee = transfer_fee or self.default_transfer_fee
        customs_clearance_fee = customs_clearance_fee or self.default_customs_clearance_fee
        
        # Calculate consumption tax (on purchase price + shipping + customs)
        taxable_amount = us_price_jpy + international_shipping_cost + customs_fee
        consumption_tax = taxable_amount * self.consumption_tax_rate
        
        # Calculate Amazon fees
        if amazon_fee_override is not None:
            amazon_fee = amazon_fee_override
        else:
            amazon_fee = self._calculate_amazon_fees(jp_listing_price)
        
        # Total cost
        total_cost = (
            us_price_jpy +
            international_shipping_cost +
            domestic_shipping_cost +
            customs_fee +
            consumption_tax +
            transfer_fee +
            customs_clearance_fee
        )
        
        # Profit calculation
        profit_amount = jp_listing_price - total_cost - amazon_fee
        profit_rate = (profit_amount / jp_listing_price * 100) if jp_listing_price > 0 else 0.0
        
        # Round to 2 decimal places
        profit_amount = float(Decimal(str(profit_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        profit_rate = float(Decimal(str(profit_rate)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        
        return {
            'profit_amount': profit_amount,
            'profit_rate': profit_rate,
            'total_cost': float(Decimal(str(total_cost)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'jp_listing_price': jp_listing_price,
            'cost_breakdown': {
                'us_price_jpy': float(Decimal(str(us_price_jpy)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'international_shipping_cost': float(Decimal(str(international_shipping_cost)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'domestic_shipping_cost': float(Decimal(str(domestic_shipping_cost)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'customs_fee': float(Decimal(str(customs_fee)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'consumption_tax': float(Decimal(str(consumption_tax)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'transfer_fee': float(Decimal(str(transfer_fee)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'customs_clearance_fee': float(Decimal(str(customs_clearance_fee)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'amazon_fee': float(Decimal(str(amazon_fee)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            },
            'exchange_rate_used': rate
        }
    
    def _estimate_international_shipping(
        self,
        weight_kg: float,
        dimensions_cm: Dict[str, float]
    ) -> float:
        """
        Estimate international shipping cost based on weight and dimensions
        This is a placeholder - should integrate with Mad Beast or Import Com API
        """
        # Calculate volumetric weight
        length = dimensions_cm.get('length', 0)
        width = dimensions_cm.get('width', 0)
        height = dimensions_cm.get('height', 0)
        
        volumetric_weight_kg = (length * width * height) / 5000  # Standard formula
        chargeable_weight_kg = max(weight_kg, volumetric_weight_kg)
        
        # Simple estimation (should be replaced with actual API call)
        # Base rate: 1000 yen per kg, minimum 2000 yen
        estimated_cost = max(2000.0, chargeable_weight_kg * 1000.0)
        
        return estimated_cost
    
    def _calculate_customs_fee(self, value_jpy: float) -> float:
        """
        Calculate customs duty (関税)
        Simplified calculation - actual rates vary by product category
        """
        # For most consumer goods, customs duty is 0-10% depending on category
        # Using average of 5% for estimation
        customs_rate = 0.05
        customs_fee = value_jpy * customs_rate
        
        return customs_fee
    
    def _calculate_amazon_fees(self, listing_price: float) -> float:
        """
        Calculate Amazon seller fees
        Includes referral fee (typically 15%) and variable closing fee
        """
        referral_fee = listing_price * self.default_amazon_referral_fee_rate
        variable_closing_fee = self.default_amazon_variable_closing_fee
        
        total_fee = referral_fee + variable_closing_fee
        
        return total_fee
    
    def is_profitable(
        self,
        profit_amount: float,
        minimum_profit_threshold: float = 3000.0
    ) -> bool:
        """
        Check if profit meets minimum threshold
        """
        return profit_amount >= minimum_profit_threshold



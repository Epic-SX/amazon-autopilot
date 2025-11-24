"""
Product Listing Model for Amazon Dropshipping Management
"""
from datetime import datetime
from typing import Optional, Dict, Any
import json

class ProductListing:
    """
    Represents a product listing on Amazon
    """
    def __init__(
        self,
        listing_id: str,
        asin: str,
        jp_asin: Optional[str] = None,
        us_asin: Optional[str] = None,
        title: str = "",
        jp_price: float = 0.0,
        us_price: float = 0.0,
        listing_price: float = 0.0,
        profit_amount: float = 0.0,
        profit_rate: float = 0.0,
        status: str = "draft",  # draft, active, paused, stopped, error
        stock_status: str = "unknown",  # in_stock, out_of_stock, unavailable
        shipping_available: bool = False,
        last_checked: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        risk_score: float = 0.0,
        category: Optional[str] = None,
        manufacturer: Optional[str] = None,
        weight: Optional[float] = None,  # in grams
        dimensions: Optional[Dict[str, float]] = None,  # length, width, height in cm
        international_shipping_cost: float = 0.0,
        domestic_shipping_cost: float = 0.0,
        customs_fee: float = 0.0,
        transfer_fee: float = 0.0,
        amazon_fee: float = 0.0,
        minimum_profit_threshold: float = 3000.0,
        source_url: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.listing_id = listing_id
        self.asin = asin
        self.jp_asin = jp_asin or asin
        self.us_asin = us_asin
        self.title = title
        self.jp_price = jp_price
        self.us_price = us_price
        self.listing_price = listing_price
        self.profit_amount = profit_amount
        self.profit_rate = profit_rate
        self.status = status
        self.stock_status = stock_status
        self.shipping_available = shipping_available
        self.last_checked = last_checked or datetime.now()
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.risk_score = risk_score
        self.category = category
        self.manufacturer = manufacturer
        self.weight = weight
        self.dimensions = dimensions or {}
        self.international_shipping_cost = international_shipping_cost
        self.domestic_shipping_cost = domestic_shipping_cost
        self.customs_fee = customs_fee
        self.transfer_fee = transfer_fee
        self.amazon_fee = amazon_fee
        self.minimum_profit_threshold = minimum_profit_threshold
        self.source_url = source_url
        self.notes = notes
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'listing_id': self.listing_id,
            'asin': self.asin,
            'jp_asin': self.jp_asin,
            'us_asin': self.us_asin,
            'title': self.title,
            'jp_price': self.jp_price,
            'us_price': self.us_price,
            'listing_price': self.listing_price,
            'profit_amount': self.profit_amount,
            'profit_rate': self.profit_rate,
            'status': self.status,
            'stock_status': self.stock_status,
            'shipping_available': self.shipping_available,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'risk_score': self.risk_score,
            'category': self.category,
            'manufacturer': self.manufacturer,
            'weight': self.weight,
            'dimensions': self.dimensions,
            'international_shipping_cost': self.international_shipping_cost,
            'domestic_shipping_cost': self.domestic_shipping_cost,
            'customs_fee': self.customs_fee,
            'transfer_fee': self.transfer_fee,
            'amazon_fee': self.amazon_fee,
            'minimum_profit_threshold': self.minimum_profit_threshold,
            'source_url': self.source_url,
            'notes': self.notes,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductListing':
        """Create from dictionary"""
        # Parse datetime strings
        last_checked = None
        created_at = None
        updated_at = None
        
        if data.get('last_checked'):
            last_checked = datetime.fromisoformat(data['last_checked']) if isinstance(data['last_checked'], str) else data['last_checked']
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at']) if isinstance(data['updated_at'], str) else data['updated_at']
        
        return cls(
            listing_id=data['listing_id'],
            asin=data['asin'],
            jp_asin=data.get('jp_asin'),
            us_asin=data.get('us_asin'),
            title=data.get('title', ''),
            jp_price=data.get('jp_price', 0.0),
            us_price=data.get('us_price', 0.0),
            listing_price=data.get('listing_price', 0.0),
            profit_amount=data.get('profit_amount', 0.0),
            profit_rate=data.get('profit_rate', 0.0),
            status=data.get('status', 'draft'),
            stock_status=data.get('stock_status', 'unknown'),
            shipping_available=data.get('shipping_available', False),
            last_checked=last_checked,
            created_at=created_at,
            updated_at=updated_at,
            risk_score=data.get('risk_score', 0.0),
            category=data.get('category'),
            manufacturer=data.get('manufacturer'),
            weight=data.get('weight'),
            dimensions=data.get('dimensions'),
            international_shipping_cost=data.get('international_shipping_cost', 0.0),
            domestic_shipping_cost=data.get('domestic_shipping_cost', 0.0),
            customs_fee=data.get('customs_fee', 0.0),
            transfer_fee=data.get('transfer_fee', 0.0),
            amazon_fee=data.get('amazon_fee', 0.0),
            minimum_profit_threshold=data.get('minimum_profit_threshold', 3000.0),
            source_url=data.get('source_url'),
            notes=data.get('notes'),
            metadata=data.get('metadata', {})
        )


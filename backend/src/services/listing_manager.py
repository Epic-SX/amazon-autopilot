"""
Listing Management Service
Manages product listings with CRUD operations and validation
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
from pathlib import Path
from src.models.listing import ProductListing
from src.models.blacklist import BlacklistManager
from src.services.duplicate_detector import DuplicateDetector
from src.database.db import get_db

class ListingManager:
    """
    Manages product listings with persistence and validation using SQLite
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db = get_db()
        self.blacklist_manager = BlacklistManager()
        self.duplicate_detector = DuplicateDetector()
    
    def _listing_from_row(self, row: Dict[str, Any]) -> ProductListing:
        """Convert database row to ProductListing object"""
        # Parse JSON fields
        dimensions = {}
        if row.get('dimensions'):
            try:
                dimensions = json.loads(row['dimensions'])
            except:
                dimensions = {}
        
        metadata = {}
        if row.get('metadata'):
            try:
                metadata = json.loads(row['metadata'])
            except:
                metadata = {}
        
        # Parse datetime strings
        last_checked = None
        if row.get('last_checked'):
            try:
                last_checked = datetime.fromisoformat(row['last_checked'])
            except:
                pass
        
        created_at = datetime.now()
        if row.get('created_at'):
            try:
                created_at = datetime.fromisoformat(row['created_at'])
            except:
                pass
        
        updated_at = datetime.now()
        if row.get('updated_at'):
            try:
                updated_at = datetime.fromisoformat(row['updated_at'])
            except:
                pass
        
        return ProductListing(
            listing_id=row['listing_id'],
            asin=row['asin'],
            jp_asin=row.get('jp_asin'),
            us_asin=row.get('us_asin'),
            title=row.get('title', ''),
            jp_price=row.get('jp_price', 0.0),
            us_price=row.get('us_price', 0.0),
            listing_price=row.get('listing_price', 0.0),
            profit_amount=row.get('profit_amount', 0.0),
            profit_rate=row.get('profit_rate', 0.0),
            status=row.get('status', 'draft'),
            stock_status=row.get('stock_status', 'unknown'),
            shipping_available=bool(row.get('shipping_available', 0)),
            last_checked=last_checked,
            created_at=created_at,
            updated_at=updated_at,
            risk_score=row.get('risk_score', 0.0),
            category=row.get('category'),
            manufacturer=row.get('manufacturer'),
            weight=row.get('weight'),
            dimensions=dimensions,
            international_shipping_cost=row.get('international_shipping_cost', 0.0),
            domestic_shipping_cost=row.get('domestic_shipping_cost', 0.0),
            customs_fee=row.get('customs_fee', 0.0),
            transfer_fee=row.get('transfer_fee', 0.0),
            amazon_fee=row.get('amazon_fee', 0.0),
            minimum_profit_threshold=row.get('minimum_profit_threshold', 3000.0),
            source_url=row.get('source_url'),
            notes=row.get('notes'),
            metadata=metadata
        )
    
    def _listing_to_row(self, listing: ProductListing) -> Dict[str, Any]:
        """Convert ProductListing object to database row"""
        return {
            'listing_id': listing.listing_id,
            'asin': listing.asin,
            'jp_asin': listing.jp_asin,
            'us_asin': listing.us_asin,
            'title': listing.title,
            'jp_price': listing.jp_price,
            'us_price': listing.us_price,
            'listing_price': listing.listing_price,
            'profit_amount': listing.profit_amount,
            'profit_rate': listing.profit_rate,
            'status': listing.status,
            'stock_status': listing.stock_status,
            'shipping_available': 1 if listing.shipping_available else 0,
            'last_checked': listing.last_checked.isoformat() if listing.last_checked else None,
            'created_at': listing.created_at.isoformat() if listing.created_at else datetime.now().isoformat(),
            'updated_at': listing.updated_at.isoformat() if listing.updated_at else datetime.now().isoformat(),
            'risk_score': listing.risk_score,
            'category': listing.category,
            'manufacturer': listing.manufacturer,
            'weight': listing.weight,
            'dimensions': json.dumps(listing.dimensions) if listing.dimensions else None,
            'international_shipping_cost': listing.international_shipping_cost,
            'domestic_shipping_cost': listing.domestic_shipping_cost,
            'customs_fee': listing.customs_fee,
            'transfer_fee': listing.transfer_fee,
            'amazon_fee': listing.amazon_fee,
            'minimum_profit_threshold': listing.minimum_profit_threshold,
            'source_url': listing.source_url,
            'notes': listing.notes,
            'metadata': json.dumps(listing.metadata) if listing.metadata else None
        }
    
    def create_listing(
        self,
        asin: str,
        jp_asin: Optional[str] = None,
        us_asin: Optional[str] = None,
        title: str = "",
        jp_price: float = 0.0,
        us_price: float = 0.0,
        listing_price: float = 0.0,
        category: Optional[str] = None,
        manufacturer: Optional[str] = None,
        weight: Optional[float] = None,
        dimensions: Optional[Dict[str, float]] = None,
        source_url: Optional[str] = None,
        minimum_profit_threshold: float = 3000.0,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new listing with validation
        
        Returns:
            Dict with 'success', 'listing' (if successful), and 'errors' (if failed)
        """
        errors = []
        
        # Generate listing ID
        listing_id = str(uuid.uuid4())
        
        # Validate ASIN
        if not asin:
            errors.append("ASIN is required")
        
        # Check blacklist
        if validate:
            blacklist_check = self.blacklist_manager.check_product(
                asin=asin,
                title=title,
                manufacturer=manufacturer or '',
                category=category or ''
            )
            
            if blacklist_check['is_blocked']:
                errors.append(f"Product blocked: {', '.join(blacklist_check['reasons'])}")
        
        # Check for duplicates
        if validate:
            existing_listings = self.get_all_listings()
            duplicate_check = self.duplicate_detector.check_duplicate(
                asin=asin,
                source_url=source_url,
                title=title,
                existing_listings=existing_listings
            )
            
            if duplicate_check['is_duplicate']:
                errors.append(f"Duplicate detected: {duplicate_check['reason']}")
        
        if errors:
            return {
                'success': False,
                'errors': errors
            }
        
        # Create listing
        listing = ProductListing(
            listing_id=listing_id,
            asin=asin,
            jp_asin=jp_asin or asin,
            us_asin=us_asin,
            title=title,
            jp_price=jp_price,
            us_price=us_price,
            listing_price=listing_price,
            category=category,
            manufacturer=manufacturer,
            weight=weight,
            dimensions=dimensions or {},
            source_url=source_url,
            minimum_profit_threshold=minimum_profit_threshold,
            status='draft'
        )
        
        # Save to database
        row = self._listing_to_row(listing)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO listings (
                    listing_id, asin, jp_asin, us_asin, title,
                    jp_price, us_price, listing_price, profit_amount, profit_rate,
                    status, stock_status, shipping_available, last_checked,
                    created_at, updated_at, risk_score, category, manufacturer,
                    weight, dimensions, international_shipping_cost, domestic_shipping_cost,
                    customs_fee, transfer_fee, amazon_fee, minimum_profit_threshold,
                    source_url, notes, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['listing_id'], row['asin'], row['jp_asin'], row['us_asin'], row['title'],
                row['jp_price'], row['us_price'], row['listing_price'], row['profit_amount'], row['profit_rate'],
                row['status'], row['stock_status'], row['shipping_available'], row['last_checked'],
                row['created_at'], row['updated_at'], row['risk_score'], row['category'], row['manufacturer'],
                row['weight'], row['dimensions'], row['international_shipping_cost'], row['domestic_shipping_cost'],
                row['customs_fee'], row['transfer_fee'], row['amazon_fee'], row['minimum_profit_threshold'],
                row['source_url'], row['notes'], row['metadata']
            ))
            conn.commit()
        
        return {
            'success': True,
            'listing': listing.to_dict()
        }
    
    def get_listing(self, listing_id: str) -> Optional[ProductListing]:
        """Get listing by ID"""
        row = self.db.fetch_one(
            "SELECT * FROM listings WHERE listing_id = ?",
            (listing_id,)
        )
        if row:
            return self._listing_from_row(row)
        return None
    
    def get_all_listings(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[ProductListing]:
        """Get all listings, optionally filtered by status or category"""
        query = "SELECT * FROM listings WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY created_at DESC"
        
        rows = self.db.fetch_all(query, tuple(params))
        return [self._listing_from_row(row) for row in rows]
    
    def update_listing(
        self,
        listing_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Update listing fields"""
        listing = self.get_listing(listing_id)
        if not listing:
            return {
                'success': False,
                'error': 'Listing not found'
            }
        
        # Update allowed fields
        allowed_fields = [
            'title', 'jp_price', 'us_price', 'listing_price',
            'profit_amount', 'profit_rate', 'status', 'stock_status',
            'shipping_available', 'category', 'manufacturer',
            'weight', 'dimensions', 'international_shipping_cost',
            'domestic_shipping_cost', 'customs_fee', 'transfer_fee',
            'amazon_fee', 'minimum_profit_threshold', 'source_url',
            'notes', 'metadata', 'risk_score'
        ]
        
        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(listing, field):
                setattr(listing, field, value)
        
        listing.updated_at = datetime.now()
        
        # Update in database
        row = self._listing_to_row(listing)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE listings SET
                    asin = ?, jp_asin = ?, us_asin = ?, title = ?,
                    jp_price = ?, us_price = ?, listing_price = ?, profit_amount = ?, profit_rate = ?,
                    status = ?, stock_status = ?, shipping_available = ?, last_checked = ?,
                    updated_at = ?, risk_score = ?, category = ?, manufacturer = ?,
                    weight = ?, dimensions = ?, international_shipping_cost = ?, domestic_shipping_cost = ?,
                    customs_fee = ?, transfer_fee = ?, amazon_fee = ?, minimum_profit_threshold = ?,
                    source_url = ?, notes = ?, metadata = ?
                WHERE listing_id = ?
            """, (
                row['asin'], row['jp_asin'], row['us_asin'], row['title'],
                row['jp_price'], row['us_price'], row['listing_price'], row['profit_amount'], row['profit_rate'],
                row['status'], row['stock_status'], row['shipping_available'], row['last_checked'],
                row['updated_at'], row['risk_score'], row['category'], row['manufacturer'],
                row['weight'], row['dimensions'], row['international_shipping_cost'], row['domestic_shipping_cost'],
                row['customs_fee'], row['transfer_fee'], row['amazon_fee'], row['minimum_profit_threshold'],
                row['source_url'], row['notes'], row['metadata'], listing_id
            ))
            conn.commit()
        
        return {
            'success': True,
            'listing': listing.to_dict()
        }
    
    def delete_listing(self, listing_id: str) -> Dict[str, Any]:
        """Delete a listing"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM listings WHERE listing_id = ?", (listing_id,))
            if cursor.rowcount == 0:
                return {
                    'success': False,
                    'error': 'Listing not found'
                }
            conn.commit()
        
        return {
            'success': True
        }
    
    def bulk_update_status(
        self,
        listing_ids: List[str],
        status: str
    ) -> Dict[str, Any]:
        """Bulk update listing status"""
        valid_statuses = ['draft', 'active', 'paused', 'stopped', 'error']
        if status not in valid_statuses:
            return {
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }
        
        updated_at = datetime.now().isoformat()
        placeholders = ','.join(['?'] * len(listing_ids))
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE listings SET status = ?, updated_at = ? WHERE listing_id IN ({placeholders})",
                (status, updated_at, *listing_ids)
            )
            updated = cursor.rowcount
            conn.commit()
        
        return {
            'success': True,
            'updated_count': updated
        }
    
    def bulk_delete(self, listing_ids: List[str]) -> Dict[str, Any]:
        """Bulk delete listings"""
        placeholders = ','.join(['?'] * len(listing_ids))
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"DELETE FROM listings WHERE listing_id IN ({placeholders})",
                listing_ids
            )
            deleted = cursor.rowcount
            conn.commit()
        
        return {
            'success': True,
            'deleted_count': deleted
        }


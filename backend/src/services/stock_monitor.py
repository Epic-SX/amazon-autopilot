"""
Stock Monitoring Service
24-hour automatic stock monitoring for product listings
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import time
import threading
from src.models.listing import ProductListing
from src.api.amazon_api import amazon_api
from src.api.us_amazon_api import us_amazon_api
from src.services.listing_manager import ListingManager
from src.services.profit_calculator import ProfitCalculator

class StockMonitor:
    """
    Monitors stock status and prices for product listings
    Runs automatic checks every 24 hours (configurable)
    """
    
    def __init__(
        self,
        listing_manager: ListingManager,
        check_interval_hours: int = 24,
        auto_stop_on_out_of_stock: bool = True,
        auto_update_prices: bool = True,
        auto_stop_low_profit: bool = True
    ):
        self.listing_manager = listing_manager
        self.check_interval_hours = check_interval_hours
        self.auto_stop_on_out_of_stock = auto_stop_on_out_of_stock
        self.auto_update_prices = auto_update_prices
        self.auto_stop_low_profit = auto_stop_low_profit
        self.profit_calculator = ProfitCalculator()
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_check_time: Dict[str, datetime] = {}
    
    def start_monitoring(self):
        """Start automatic monitoring in background thread"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        print("Stock monitoring started")
    
    def stop_monitoring(self):
        """Stop automatic monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("Stock monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                # Get all active listings
                active_listings = self.listing_manager.get_all_listings(status='active')
                
                print(f"Monitoring {len(active_listings)} active listings...")
                
                # Check each listing
                for listing in active_listings:
                    try:
                        self.check_listing(listing.listing_id)
                    except Exception as e:
                        print(f"Error checking listing {listing.listing_id}: {e}")
                
                # Wait for next check interval
                time.sleep(self.check_interval_hours * 3600)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def check_listing(self, listing_id: str) -> Dict[str, Any]:
        """
        Check a single listing for stock and price updates
        
        Returns:
            Dict with check results
        """
        listing = self.listing_manager.get_listing(listing_id)
        if not listing:
            return {
                'success': False,
                'error': 'Listing not found'
            }
        
        updates = {}
        
        # Check Japan Amazon stock and price
        jp_stock_status, jp_price = self._check_jp_amazon(listing.jp_asin)
        if jp_stock_status:
            updates['stock_status'] = jp_stock_status
            listing.stock_status = jp_stock_status
        
        if jp_price and jp_price > 0:
            updates['jp_price'] = jp_price
            listing.jp_price = jp_price
        
        # Check US Amazon stock and price
        if listing.us_asin:
            us_stock_status, us_price = self._check_us_amazon(listing.us_asin)
            if us_stock_status:
                updates['us_stock_status'] = us_stock_status
            
            if us_price and us_price > 0:
                updates['us_price'] = us_price
                listing.us_price = us_price
        
        # Recalculate profit if prices changed
        if 'jp_price' in updates or 'us_price' in updates:
            profit_result = self._recalculate_profit(listing)
            if profit_result:
                updates['profit_amount'] = profit_result['profit_amount']
                updates['profit_rate'] = profit_result['profit_rate']
                listing.profit_amount = profit_result['profit_amount']
                listing.profit_rate = profit_result['profit_rate']
        
        # Auto-stop if out of stock
        if self.auto_stop_on_out_of_stock and listing.stock_status == 'out_of_stock':
            updates['status'] = 'paused'
            listing.status = 'paused'
            updates['auto_stopped_reason'] = 'Out of stock'
        
        # Auto-stop if profit too low
        if self.auto_stop_low_profit:
            if listing.profit_amount < listing.minimum_profit_threshold:
                updates['status'] = 'paused'
                listing.status = 'paused'
                updates['auto_stopped_reason'] = f'Profit below threshold ({listing.profit_amount} < {listing.minimum_profit_threshold})'
        
        # Update last checked time
        listing.last_checked = datetime.now()
        listing.updated_at = datetime.now()
        
        # Save updates
        if updates:
            self.listing_manager.update_listing(listing_id, **updates)
        
        return {
            'success': True,
            'updates': updates,
            'listing_id': listing_id
        }
    
    def _check_jp_amazon(self, asin: str) -> Tuple[Optional[str], Optional[float]]:
        """
        Check Japan Amazon stock status and price
        
        Returns:
            Tuple of (stock_status, price)
        """
        try:
            # Use existing Amazon API
            products = amazon_api.search_items(asin, limit=1)
            
            if not products:
                return ('unavailable', None)
            
            product = products[0]
            
            # Extract stock status
            availability = getattr(product, 'availability', True) if hasattr(product, 'availability') else product.get('availability', True)
            stock_status = 'in_stock' if availability else 'out_of_stock'
            
            # Extract price
            price = None
            if hasattr(product, 'price'):
                price = product.price
            elif isinstance(product, dict):
                price = product.get('price')
            
            return (stock_status, price)
        except Exception as e:
            print(f"Error checking JP Amazon for ASIN {asin}: {e}")
            return (None, None)
    
    def _check_us_amazon(self, asin: str) -> Tuple[Optional[str], Optional[float]]:
        """
        Check US Amazon stock status and price
        
        Returns:
            Tuple of (stock_status, price)
        """
        try:
            product = us_amazon_api.get_product_by_asin(asin)
            
            if not product:
                return ('unavailable', None)
            
            stock_status = 'in_stock' if product.availability else 'out_of_stock'
            price = product.price
            
            return (stock_status, price)
        except Exception as e:
            print(f"Error checking US Amazon for ASIN {asin}: {e}")
            return (None, None)
    
    def _recalculate_profit(self, listing: ProductListing) -> Optional[Dict[str, Any]]:
        """
        Recalculate profit for a listing
        """
        try:
            if not listing.us_price or not listing.listing_price:
                return None
            
            profit_result = self.profit_calculator.calculate_profit(
                us_price=listing.us_price,
                jp_listing_price=listing.listing_price,
                weight_kg=listing.weight / 1000 if listing.weight else None,
                dimensions_cm=listing.dimensions,
                international_shipping_cost=listing.international_shipping_cost,
                domestic_shipping_cost=listing.domestic_shipping_cost,
                customs_fee=listing.customs_fee,
                transfer_fee=listing.transfer_fee,
                calculate_shipping=False  # Use existing shipping costs
            )
            
            return profit_result
        except Exception as e:
            print(f"Error recalculating profit: {e}")
            return None
    
    def check_all_listings(self) -> Dict[str, Any]:
        """
        Manually trigger check for all active listings
        
        Returns:
            Summary of check results
        """
        active_listings = self.listing_manager.get_all_listings(status='active')
        results = {
            'total': len(active_listings),
            'checked': 0,
            'updated': 0,
            'auto_stopped': 0,
            'errors': 0
        }
        
        for listing in active_listings:
            try:
                check_result = self.check_listing(listing.listing_id)
                results['checked'] += 1
                
                if check_result.get('success'):
                    if check_result.get('updates'):
                        results['updated'] += 1
                    
                    if 'auto_stopped_reason' in check_result.get('updates', {}):
                        results['auto_stopped'] += 1
                else:
                    results['errors'] += 1
            except Exception as e:
                print(f"Error checking listing {listing.listing_id}: {e}")
                results['errors'] += 1
        
        return results


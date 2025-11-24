import requests
import urllib.parse
import hashlib
from src.models.product import ProductDetail
import json
import time
from datetime import datetime
import hmac
import base64
import os
from src.config.settings import AMAZON_PARTNER_TAG, AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_REGION, AMAZON_API_ENDPOINT
import random
from amazon_paapi import AmazonApi
from bs4 import BeautifulSoup
import logging
import re
import pickle
import os.path
from pathlib import Path

# Import the Amazon Product Advertising API SDK
try:
    from amazon_paapi.models.condition import Condition
    from amazon_paapi.models.merchant import Merchant
    from amazon_paapi.models.sort_by import SortBy
    from amazon_paapi.errors.exceptions import ItemsNotFound
    AMAZON_SDK_AVAILABLE = True
except ImportError:
    print("Amazon PAAPI SDK not available, using fallback implementation")
    AMAZON_SDK_AVAILABLE = False
    ItemsNotFound = Exception  # Fallback exception class

# Constants for retry logic
MAX_RETRIES = 2
RETRY_DELAY_BASE = 1.0  # Base delay in seconds
RETRY_DELAY_MAX = 5.0  # Maximum delay in seconds

# List of rotating User-Agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
]

class AmazonAPI:
    def __init__(self):
        """
        Initialize the Amazon API client
        """
        self.session = requests.Session()
        self.default_image = "https://placehold.co/300x300/eee/999?text=No+Image"
        
        # Initialize cache
        self.cache_dir = Path("cache/amazon")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_expiry = 3600 * 24  # 24 hours in seconds
        self.load_cache()
        
        # Initialize Amazon PAAPI client
        try:
            # Check if the amazon_paapi library is available
            from amazon_paapi.api import AmazonApi
            
            # Check if we have all the required credentials
            if not AMAZON_ACCESS_KEY or not AMAZON_SECRET_KEY or not AMAZON_PARTNER_TAG:
                print("Missing Amazon API credentials. PAAPI client will not be initialized.")
                self.client = None
            else:
                # Create the API client
                print(f"Initializing Amazon PAAPI client with: Access Key: {AMAZON_ACCESS_KEY[:4]}..., Partner Tag: {AMAZON_PARTNER_TAG}, Region: {AMAZON_REGION}")
                self.client = AmazonApi(
                    key=AMAZON_ACCESS_KEY,
                    secret=AMAZON_SECRET_KEY,
                    tag=AMAZON_PARTNER_TAG,
                    country='JP',  # Country code for Japan
                    throttling=1.0  # Add a throttling parameter to avoid hitting rate limits
                )
                print(f"Successfully initialized Amazon PAAPI client")
        except Exception as e:
            print(f"Failed to initialize Amazon PAAPI client: {e}")
            print(f"Error details: {str(e)}")
            import traceback
            traceback.print_exc()
            self.client = None
    
    def load_cache(self):
        """Load the search cache from disk"""
        self.search_cache = {}
        cache_file = self.cache_dir / "search_cache.pkl"
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    # Only keep cache entries that haven't expired
                    current_time = time.time()
                    self.search_cache = {
                        k: v for k, v in cached_data.items() 
                        if current_time - v['timestamp'] < self.cache_expiry
                    }
                print(f"Loaded {len(self.search_cache)} items from Amazon search cache")
            except Exception as e:
                print(f"Error loading Amazon search cache: {e}")
                # Start with a fresh cache if there was an error
                self.search_cache = {}
    
    def save_cache(self):
        """Save the search cache to disk"""
        cache_file = self.cache_dir / "search_cache.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(self.search_cache, f)
        except Exception as e:
            print(f"Error saving Amazon search cache: {e}")
    
    def get_cached_search(self, keywords):
        """Get cached search results if available"""
        cache_key = keywords.lower().strip()
        if cache_key in self.search_cache:
            cache_entry = self.search_cache[cache_key]
            # Check if the cache entry has expired
            if time.time() - cache_entry['timestamp'] < self.cache_expiry:
                print(f"Using cached Amazon search results for '{keywords}'")
                return cache_entry['results']
        return None
    
    def cache_search_results(self, keywords, results):
        """Cache search results"""
        cache_key = keywords.lower().strip()
        self.search_cache[cache_key] = {
            'results': results,
            'timestamp': time.time()
        }
        # Save cache periodically (every 10 new entries)
        if len(self.search_cache) % 10 == 0:
            self.save_cache()

    def get_price(self, product_info, direct_search=True):
        """
        Amazonから商品価格情報を取得
        
        Args:
            product_info (str): The product information (model number, keywords, etc.)
            direct_search (bool): If True, use exact model number matching for model numbers
        """
        try:
            # Check if this is a model number
            is_model_number = re.match(r'^[A-Za-z0-9\-]+$', product_info)
            
            # Use the Amazon Product Advertising API to get real product data
            amazon_results = self._search_amazon_products(product_info, limit=5, direct_search=direct_search and is_model_number)
            
            if amazon_results and len(amazon_results) > 0:
                product = amazon_results[0]
                
                # If product is a ProductDetail object
                if isinstance(product, ProductDetail):
                    return {
                        'price': product.price,
                        'url': product.url,
                        'availability': True,
                        'title': product.title,
                        'shop': "Amazon.co.jp",
                        'image_url': product.image_url
                    }
                # If product is a dictionary
                elif isinstance(product, dict):
                    return {
                        'price': self._extract_price(product.get('price', '0')),
                        'url': product.get('url', ''),
                        'availability': True,
                        'title': product.get('title', f"{product_info} (Amazon)"),
                        'shop': "Amazon.co.jp",
                        'image_url': product.get('image_url', '')
                    }
            else:
                # Create a better search URL for the fallback
                # For product codes, try to create a direct product URL first
                fallback_url = ""
                if re.match(r'^[A-Za-z0-9\-]+$', product_info):
                    # Try direct product URL with clean code (no hyphens)
                    clean_code = product_info.replace('-', '')
                    if len(clean_code) == 10:  # ASIN length
                        fallback_url = f"https://www.amazon.co.jp/dp/{clean_code}"
                    else:
                        # Try both with and without hyphens in the search
                        fallback_url = f"https://www.amazon.co.jp/s?k={urllib.parse.quote(product_info)}+OR+{urllib.parse.quote(clean_code)}"
                else:
                    # Regular search URL
                    fallback_url = f"https://www.amazon.co.jp/s?k={urllib.parse.quote(product_info)}"
                
                # Add affiliate tag if available
                if AMAZON_PARTNER_TAG and '&tag=' not in fallback_url and '?tag=' not in fallback_url:
                    separator = '&' if '?' in fallback_url else '?'
                    fallback_url = f"{fallback_url}{separator}tag={AMAZON_PARTNER_TAG}"
                
                # Return a placeholder with the improved URL
                return {
                    'price': 0,
                    'url': fallback_url,
                    'availability': False,
                    'title': f"{product_info} (Amazon)",
                    'shop': "Amazon.co.jp",
                    'image_url': self.default_image
                }
        except Exception as e:
            print(f"Error in Amazon get_price: {e}")
            # Return a fallback response
            return {
                'price': 0,
                'url': f"https://www.amazon.co.jp/s?k={urllib.parse.quote(product_info)}",
                'availability': False,
                'title': f"{product_info} (Amazon)",
                'shop': "Amazon.co.jp",
                'image_url': self.default_image
            }
            
    def get_product_details(self, product_info, direct_search=True):
        """
        Amazonから商品詳細情報を取得
        
        Args:
            product_info (str): The product information (model number, keywords, etc.)
            direct_search (bool): If True, use exact model number matching for model numbers
        """
        try:
            print(f"DEBUG: Fetching Amazon product details for: {product_info}")
            
            # Check if this is a model number
            is_model_number = re.match(r'^[A-Za-z0-9\-]+$', product_info)
            
            # Search for products on Amazon
            amazon_results = self._search_amazon_products(product_info, limit=5, direct_search=direct_search and is_model_number)
            
            if not amazon_results:
                print(f"DEBUG: No products found from Amazon for '{product_info}'")
                return self._get_fallback_products(product_info)
            
            # Convert to ProductDetail objects if they aren't already
            products = []
            for item in amazon_results:
                if isinstance(item, ProductDetail):
                    # Already a ProductDetail object
                    products.append(item)
                elif isinstance(item, dict):
                    # Convert dict to ProductDetail
                    try:
                        # Extract necessary information
                        title = item.get('title', f"{product_info} (Amazon)")
                        price = self._extract_price(item.get('price', '0'))
                        image_url = item.get('image_url', self.default_image)
                        url = item.get('url', '')
                        asin = item.get('asin', '')
                        
                        # Create ProductDetail object
                        product = ProductDetail(
                            title=title,
                            price=price,
                            image_url=image_url,
                            url=url,
                            source="Amazon",
                            shop="Amazon.co.jp",
                            asin=asin,
                            shipping_fee=0,  # Assume free shipping
                            additional_info={"asin": asin}
                        )
                        products.append(product)
                    except Exception as e:
                        print(f"Error converting Amazon result to ProductDetail: {e}")
            
            print(f"DEBUG: Returning {len(products)} products from Amazon")
            return products
        except Exception as e:
            print(f"Error in Amazon get_product_details: {e}")
            return self._get_fallback_products(product_info)
    
    def get_multiple_prices(self, product_info, direct_search=True):
        """
        Get multiple price listings from Amazon
        
        Args:
            product_info (str): The product information (model number, keywords, etc.)
            direct_search (bool): If True, use exact model number matching for model numbers
        """
        try:
            # Check if this is a model number
            is_model_number = re.match(r'^[A-Za-z0-9\-]+$', product_info)
            
            # Search for products on Amazon
            amazon_results = self._search_amazon_products(product_info, limit=5, direct_search=direct_search and is_model_number)
            
            # Format the results for price comparison
            price_results = []
            for product in amazon_results:
                try:
                    if isinstance(product, ProductDetail):
                        # If it's a ProductDetail object
                        if product.price is not None:
                            price_results.append({
                                'store': "Amazon.co.jp",
                                'title': product.title,
                                'price': product.price,
                                'url': product.url,
                                'image_url': product.image_url,
                                'rating': product.rating if hasattr(product, 'rating') else None,
                                'review_count': product.review_count if hasattr(product, 'review_count') else None
                            })
                    elif isinstance(product, dict):
                        # If it's a dictionary
                        if 'price' in product and product['price']:
                            price_results.append({
                                'store': "Amazon.co.jp",
                                'title': product.get('title', ''),
                                'price': self._extract_price(product['price']),
                                'url': product.get('url', ''),
                                'image_url': product.get('image_url', ''),
                                'rating': product.get('rating', None),
                                'review_count': product.get('review_count', None)
                            })
                except Exception as e:
                    print(f"Error processing Amazon product for price comparison: {e}")
            
            return price_results
        except Exception as e:
            print(f"Error getting Amazon prices: {e}")
            return []
    
    def get_items_by_asin(self, asin: str) -> dict:
        """
        Get product details by ASIN using Amazon Product Advertising API
        
        Args:
            asin (str): Product ASIN (10 characters, alphanumeric)
        
        Returns:
            dict: Product dictionary or None if not found
        """
        try:
            # Validate ASIN format (10 characters, alphanumeric)
            if not re.match(r'^[A-Z0-9]{10}$', asin.upper()):
                print(f"Invalid ASIN format: {asin}")
                return None
            
            asin = asin.upper()
            print(f"Getting product by ASIN via PA-API: {asin}")
            
            # Check if we have a valid PAAPI client
            if not self.client:
                print("Amazon PAAPI client not initialized, cannot get product by ASIN")
                return None
            
            # Strategy 1: Try get_items with include_unavailable=True first
            # This helps when products exist but are currently unavailable
            for attempt in range(MAX_RETRIES):
                try:
                    if attempt > 0:
                        delay = min(RETRY_DELAY_MAX, RETRY_DELAY_BASE * (2 ** attempt))
                        delay = delay * (0.5 + random.random() * 1.5)
                        print(f"Waiting {delay:.2f} seconds before retry {attempt + 1}/{MAX_RETRIES}")
                        time.sleep(delay)
                    
                    # Try with include_unavailable=True on first attempt, False on retry
                    include_unavailable = (attempt == 0)
                    print(f"Fetching product via PA-API get_items (attempt {attempt + 1}/{MAX_RETRIES}, include_unavailable={include_unavailable})")
                    items_result = self.client.get_items([asin], include_unavailable=include_unavailable)
                    
                    if not items_result:
                        print(f"No items found in PA-API response for ASIN {asin}")
                        continue
                    
                    # Handle both list and single item responses
                    items_list = items_result if isinstance(items_result, list) else (items_result.items if hasattr(items_result, 'items') else [])
                    if not items_list:
                        print(f"No items found in PA-API response for ASIN {asin}")
                        continue
                    
                    item = items_list[0]
                    
                    # Skip items with None ASIN (unavailable items when include_unavailable=True)
                    if not hasattr(item, 'asin') or item.asin is None:
                        print(f"Item found but ASIN is None (unavailable item), continuing search...")
                        continue
                    
                    # Extract product information
                    product_asin = item.asin
                    
                    # Extract title
                    title = "Amazon Product"
                    if hasattr(item, 'item_info') and hasattr(item.item_info, 'title') and hasattr(item.item_info.title, 'display_value'):
                        title = item.item_info.title.display_value
                    
                    # Extract price
                    price = 0
                    if hasattr(item, 'offers') and hasattr(item.offers, 'listings') and item.offers.listings:
                        listing = item.offers.listings[0]
                        if hasattr(listing, 'price') and hasattr(listing.price, 'amount'):
                            price = int(float(listing.price.amount))
                    
                    # Extract image URL
                    image_url = self.default_image
                    if hasattr(item, 'images') and hasattr(item.images, 'primary') and hasattr(item.images.primary, 'large'):
                        image_url = item.images.primary.large.url
                    
                    # Extract product URL
                    detail_page_url = f"https://www.amazon.co.jp/dp/{product_asin}?tag={AMAZON_PARTNER_TAG}"
                    if hasattr(item, 'detail_page_url'):
                        detail_page_url = item.detail_page_url
                    
                    # Add affiliate tag if not present
                    if '&tag=' not in detail_page_url and '?tag=' not in detail_page_url:
                        separator = '&' if '?' in detail_page_url else '?'
                        detail_page_url = f"{detail_page_url}{separator}tag={AMAZON_PARTNER_TAG}"
                    
                    # Extract availability
                    availability = False
                    if hasattr(item, 'offers') and hasattr(item.offers, 'listings') and item.offers.listings:
                        listing = item.offers.listings[0]
                        if hasattr(listing, 'availability') and hasattr(listing.availability, 'type'):
                            availability = listing.availability.type == 'Now'
                    
                    # Extract features/description
                    description = None
                    features = []
                    if hasattr(item, 'item_info') and hasattr(item.item_info, 'features'):
                        if hasattr(item.item_info.features, 'display_values'):
                            features = item.item_info.features.display_values
                        elif hasattr(item.item_info.features, 'values'):
                            features = item.item_info.features.values
                        if features:
                            description = ' '.join(features[:5])  # Join first 5 features as description
                    
                    product_data = {
                        "asin": product_asin,
                        "title": title,
                        "price": price,
                        "url": detail_page_url,
                        "image_url": image_url,
                        "source": "amazon",
                        "availability": availability,
                        "description": description,
                        "features": features
                    }
                    
                    print(f"Successfully fetched product via PA-API: {title[:50]}...")
                    return product_data
                
                except ItemsNotFound as e:
                    # ItemsNotFound on last attempt - try search_items as fallback
                    if attempt == MAX_RETRIES - 1:
                        print(f"ASIN {asin} not found via get_items, trying search_items as fallback")
                        # Try using search_items with the ASIN as keyword
                        # Pass use_paapi_for_asin=False to prevent infinite loop
                        search_results = self.search_items(
                            asin, 
                            limit=10, 
                            use_paapi_for_asin=False,
                            skip_paapi_retry=True
                        )
                        
                        if search_results:
                            # Find exact ASIN match in search results
                            for result in search_results:
                                result_asin = result.get('asin') if isinstance(result, dict) else getattr(result, 'asin', None)
                                if result_asin and result_asin.upper() == asin:
                                    print(f"Found ASIN {asin} via search_items fallback")
                                    # Convert to dict if needed
                                    if isinstance(result, dict):
                                        return result
                                    else:
                                        # Convert object to dict
                                        return {
                                            "asin": getattr(result, 'asin', None),
                                            "title": getattr(result, 'title', None) or (result.get('title') if isinstance(result, dict) else None),
                                            "price": getattr(result, 'price', 0) or (result.get('price', 0) if isinstance(result, dict) else 0),
                                            "url": getattr(result, 'url', None) or (result.get('url', None) if isinstance(result, dict) else None),
                                            "image_url": getattr(result, 'image_url', None) or (result.get('image_url', None) if isinstance(result, dict) else None),
                                            "source": "amazon",
                                            "availability": getattr(result, 'availability', False) or (result.get('availability', False) if isinstance(result, dict) else False)
                                        }
                        
                        print(f"ASIN {asin} not found in Japan marketplace (ItemsNotFound): {e}")
                        return None
                    else:
                        # Continue to next retry attempt
                        print(f"ASIN {asin} not found (attempt {attempt + 1}/{MAX_RETRIES}), retrying...")
                        continue
                
                except Exception as e:
                    # For other errors, retry
                    print(f"Error fetching product by ASIN via PA-API (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                    import traceback
                    traceback.print_exc()
            
            print(f"All PA-API attempts failed for ASIN {asin}")
            return None
            
        except Exception as e:
            print(f"Error in get_items_by_asin: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def search_items(self, keywords, limit=5, **kwargs):
        """
        Search for items using the Amazon Product Advertising API
        
        Args:
            keywords (str): The search keywords or ASIN
            limit (int): Maximum number of results to return
            **kwargs: Additional search parameters
                - sort_by (str): Sort order (e.g., 'Relevance', 'Price:HighToLow', etc.)
                - min_price (int): Minimum price in yen
                - max_price (int): Maximum price in yen
                - condition (str): Product condition ('New', 'Used', 'Collectible', 'Refurbished')
                - merchant (str): Merchant type ('Amazon', 'All')
                - category (str): Browse node ID or category name
                - direct_search (bool): If True, only use the exact model number without variations
                - use_paapi_for_asin (bool): If True, use PA-API get_items for ASINs instead of scraping
        
        Returns:
            list: List of product dictionaries
        """
        try:
            print(f"Searching Amazon for: {keywords} (limit: {limit})")
            
            # Check if this is an ASIN (10 characters, alphanumeric)
            is_asin = bool(re.match(r'^[A-Z0-9]{10}$', str(keywords).upper()))
            use_paapi_for_asin = kwargs.get('use_paapi_for_asin', True)
            skip_paapi_retry = kwargs.get('skip_paapi_retry', False)
            
            # If it's an ASIN and we should use PA-API, use get_items_by_asin
            if is_asin and use_paapi_for_asin and self.client and not skip_paapi_retry:
                print(f"Detected ASIN '{keywords}', using PA-API get_items")
                product = self.get_items_by_asin(keywords.upper())
                if product:
                    print(f"Found product via PA-API: {product.get('title', 'N/A')[:50]}...")
                    return [product]
                else:
                    print(f"PA-API get_items failed for ASIN {keywords}, falling back to scraping/search")
                    # Skip PA-API search to avoid infinite loop, go straight to scraping
                    skip_paapi_retry = True
            
            # Check if we have cached results
            cached_results = self.get_cached_search(keywords)
            if cached_results:
                print(f"Found {len(cached_results)} cached results for {keywords}")
                return cached_results[:limit]
            
            # Check if this is a direct search or looks like a model number
            direct_search = kwargs.get('direct_search', False)
            
            # Check if the keywords look like a model number (contains alphanumeric with dashes)
            is_model_number = bool(re.match(r'^[A-Za-z0-9]+-?[A-Za-z0-9]+', str(keywords)))
            
            # For model numbers (but not ASINs), prioritize scraping as PAAPI often fails for these
            if is_model_number and not is_asin:
                print(f"Detected model number pattern in '{keywords}', prioritizing scraping")
                # Try scraping first for model numbers
                scraped_results = self._scrape_amazon_search(keywords, limit)
                if scraped_results and len(scraped_results) > 0:
                    print(f"Found {len(scraped_results)} products via scraping")
                    # Cache the results
                    self.cache_search_results(keywords, scraped_results)
                    return scraped_results[:limit]
            
            # If we already tried get_items_by_asin and it failed, skip PA-API search to avoid infinite loop
            if skip_paapi_retry:
                print(f"Skipping PA-API search for ASIN {keywords} (already tried get_items), going to scraping")
            # Check if we have a valid PAAPI client
            elif not self.client:
                print("Amazon PAAPI client not initialized, using fallback implementation")
                return self._search_amazon_products(keywords, limit)
            else:
                # Expand search keywords for better results
                expanded_keywords = self._expand_search_keywords(keywords, direct_search)
                print(f"Expanded search keywords: {expanded_keywords}")
                
                # Set up search parameters
                search_params = {
                    'keywords': expanded_keywords,
                    'search_index': 'All',  # Search all categories
                    'item_count': min(10, limit)  # API allows max 10 items per request
                }
                
                # Add optional parameters
                if 'sort_by' in kwargs:
                    sort_mapping = {
                        'relevance': 'Relevance',
                        'price_high_to_low': 'Price:HighToLow',
                        'price_low_to_high': 'Price:LowToHigh',
                        'newest': 'NewestArrivals'
                    }
                    sort_value = sort_mapping.get(kwargs['sort_by'].lower(), 'Relevance')
                    search_params['sort_by'] = sort_value
                
                if 'min_price' in kwargs and kwargs['min_price']:
                    search_params['min_price'] = kwargs['min_price']
                
                if 'max_price' in kwargs and kwargs['max_price']:
                    search_params['max_price'] = kwargs['max_price']
                
                if 'category' in kwargs and kwargs['category']:
                    search_params['browse_node_id'] = kwargs['category']
                
                # Execute the search request
                for attempt in range(MAX_RETRIES):
                    try:
                        # Add a random delay between attempts with exponential backoff
                        if attempt > 0:
                            delay = min(RETRY_DELAY_MAX, RETRY_DELAY_BASE * (2 ** attempt))
                            # Add jitter to appear more human-like
                            delay = delay * (0.5 + random.random() * 1.5)
                            print(f"Waiting {delay:.2f} seconds before retry {attempt + 1}/{MAX_RETRIES}")
                            time.sleep(delay)
                        
                        # Execute the search
                        print(f"Executing Amazon PAAPI search (attempt {attempt + 1}/{MAX_RETRIES})")
                        search_result = self.client.search_items(**search_params)
                        
                        # Check if we have search results
                        if not search_result or not hasattr(search_result, 'items') or not search_result.items:
                            print(f"No items found in Amazon PAAPI response (attempt {attempt + 1}/{MAX_RETRIES})")
                            continue
                        
                        # Process the search results
                        results = []
                        for item in search_result.items:
                            try:
                                # Extract ASIN
                                asin = item.asin
                                
                                # Extract title
                                title = "Amazon Product"
                                if hasattr(item, 'item_info') and hasattr(item.item_info, 'title') and hasattr(item.item_info.title, 'display_value'):
                                    title = item.item_info.title.display_value
                                
                                # Extract price
                                price = 0
                                if hasattr(item, 'offers') and hasattr(item.offers, 'listings') and item.offers.listings:
                                    listing = item.offers.listings[0]
                                    if hasattr(listing, 'price') and hasattr(listing.price, 'amount'):
                                        price = int(float(listing.price.amount))
                                
                                # Extract image URL
                                image_url = self.default_image
                                if hasattr(item, 'images') and hasattr(item.images, 'primary') and hasattr(item.images.primary, 'large'):
                                    image_url = item.images.primary.large.url
                                
                                # Extract product URL
                                detail_page_url = f"https://www.amazon.co.jp/dp/{asin}?tag={AMAZON_PARTNER_TAG}"
                                if hasattr(item, 'detail_page_url'):
                                    detail_page_url = item.detail_page_url
                                
                                # Add affiliate tag if not present
                                if '&tag=' not in detail_page_url and '?tag=' not in detail_page_url:
                                    separator = '&' if '?' in detail_page_url else '?'
                                    detail_page_url = f"{detail_page_url}{separator}tag={AMAZON_PARTNER_TAG}"
                                
                                # Extract availability
                                availability = False
                                if hasattr(item, 'offers') and hasattr(item.offers, 'listings') and item.offers.listings:
                                    listing = item.offers.listings[0]
                                    if hasattr(listing, 'availability') and hasattr(listing.availability, 'type'):
                                        availability = listing.availability.type == 'Now'
                                
                                # Create product data dictionary
                                product_data = {
                                    "asin": asin,
                                    "title": title,
                                    "price": price,
                                    "url": detail_page_url,
                                    "image_url": image_url,
                                    "source": "amazon",
                                    "availability": availability
                                }
                                
                                results.append(product_data)
                            except Exception as e:
                                print(f"Error processing Amazon PAAPI search result: {e}")
                        
                        # If we found products, cache and return them
                        if results:
                            print(f"Found {len(results)} products via Amazon PAAPI")
                            self.cache_search_results(keywords, results)
                            return results[:limit]
                    
                    except Exception as e:
                        print(f"Error in Amazon PAAPI search (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            
            # If we get here, all PAAPI attempts failed, try scraping
            print("All Amazon PAAPI search attempts failed, trying scraping")
            scrape_results = self._scrape_amazon_search(keywords, limit)
            
            # If scraping worked, cache and return the results
            if scrape_results:
                self.cache_search_results(keywords, scrape_results)
                return scrape_results[:limit]
            
            # If all else fails, use fallback
            print("All Amazon search methods failed, using fallback results")
            return self._get_fallback_products(keywords, limit)
        
        except Exception as e:
            print(f"Error in Amazon search_items: {e}")
            return self._get_fallback_products(keywords, limit)

    def _search_amazon_products(self, keywords, limit=5, direct_search=False):
        """
        Search for products on Amazon using the Product Advertising API
        This is a legacy method that now uses the search_items method
        
        Args:
            keywords (str): The search keywords
            limit (int): Maximum number of results to return
            direct_search (bool): If True, only use the exact model number without variations
        """
        try:
            print(f"Searching Amazon for products matching: {keywords}")
            
            # Check if we have cached results
            cached_results = self.get_cached_search(keywords)
            if cached_results:
                print(f"Using cached results for '{keywords}'")
                return cached_results[:limit]
            
            # Try to use the PAAPI client first
            if self.client:
                try:
                    # Use the new search_items method
                    results = self.search_items(keywords, limit, direct_search=direct_search)
                    if results:
                        return results
                except Exception as e:
                    print(f"Error using PAAPI search: {e}")
            
            # If PAAPI failed or is not available, try direct product access for product codes
            if re.match(r'^[A-Za-z0-9\-]+$', keywords):
                print(f"Trying direct product access for product code: {keywords}")
                direct_results = self._try_direct_product_access(keywords)
                if direct_results:
                    self.cache_search_results(keywords, direct_results)
                    return direct_results[:limit]
            
            # If direct access failed or not applicable, try scraping
            print(f"Trying to scrape Amazon search results for: {keywords}")
            scrape_results = self._scrape_amazon_search(keywords, limit)
            if scrape_results:
                self.cache_search_results(keywords, scrape_results)
                return scrape_results[:limit]
            
            # If all else fails, return fallback products
            print(f"All Amazon search methods failed for '{keywords}', using fallback")
            return self._get_fallback_products(keywords, limit)
            
        except Exception as e:
            print(f"Error in _search_amazon_products: {e}")
            return self._get_fallback_products(keywords, limit)
            
    def _try_direct_product_access(self, product_code):
        """
        Try to access a product directly using its ASIN or model number
        """
        try:
            print(f"Trying direct product access for: {product_code}")
            
            # Clean the product code (remove hyphens)
            clean_code = product_code.replace('-', '')
            
            # If the clean code is 10 characters (ASIN length), try direct access
            if len(clean_code) == 10 and re.match(r'^[A-Z0-9]{10}$', clean_code, re.IGNORECASE):
                print(f"Product code {product_code} appears to be an ASIN, trying direct access")
                
                # Try to use the PAAPI client first
                if self.client:
                    try:
                        # Get item information using the ASIN
                        response = self.client.get_items([clean_code])
                        
                        # Check if we have results
                        if response and hasattr(response, 'items') and response.items:
                            print(f"Successfully retrieved product {clean_code} via PAAPI")
                            
                            # Process the results
                            results = []
                            for item in response.items:
                                try:
                                    # Extract ASIN
                                    asin = item.asin
                                    
                                    # Extract title
                                    title = "Amazon Product"
                                    if hasattr(item, 'item_info') and hasattr(item.item_info, 'title') and hasattr(item.item_info.title, 'display_value'):
                                        title = item.item_info.title.display_value
                                    
                                    # Extract price
                                    price = 0
                                    if hasattr(item, 'offers') and hasattr(item.offers, 'listings') and item.offers.listings:
                                        listing = item.offers.listings[0]
                                        if hasattr(listing, 'price') and hasattr(listing.price, 'amount'):
                                            price = int(float(listing.price.amount))
                                    
                                    # Extract image URL
                                    image_url = self.default_image
                                    if hasattr(item, 'images') and hasattr(item.images, 'primary') and hasattr(item.images.primary, 'large'):
                                        image_url = item.images.primary.large.url
                                    
                                    # Extract product URL
                                    detail_page_url = f"https://www.amazon.co.jp/dp/{asin}?tag={AMAZON_PARTNER_TAG}"
                                    if hasattr(item, 'detail_page_url'):
                                        detail_page_url = item.detail_page_url
                                    
                                    # Add affiliate tag if not present
                                    if '&tag=' not in detail_page_url and '?tag=' not in detail_page_url:
                                        separator = '&' if '?' in detail_page_url else '?'
                                        detail_page_url = f"{detail_page_url}{separator}tag={AMAZON_PARTNER_TAG}"
                                    
                                    # Extract availability
                                    availability = False
                                    if hasattr(item, 'offers') and hasattr(item.offers, 'listings') and item.offers.listings:
                                        listing = item.offers.listings[0]
                                        if hasattr(listing, 'availability') and hasattr(listing.availability, 'type'):
                                            availability = listing.availability.type == 'Now'
                                    
                                    # Create product data dictionary
                                    product_data = {
                                        "asin": asin,
                                        "title": title,
                                        "price": price,
                                        "url": detail_page_url,
                                        "image_url": image_url,
                                        "source": "amazon",
                                        "availability": availability
                                    }
                                    
                                    results.append(product_data)
                                except Exception as e:
                                    print(f"Error processing Amazon PAAPI direct product result: {e}")
                            
                            # Return the results
                            if results:
                                return results
                    except ItemsNotFound as e:
                        # ASIN doesn't exist in this marketplace, skip to scraping
                        print(f"ASIN {clean_code} not found in Japan marketplace (ItemsNotFound), trying scraping")
                    except Exception as e:
                        print(f"Error in PAAPI direct product access: {e}")
                
                # If PAAPI failed or is not available, try scraping
                try:
                    # Create the product URL
                    product_url = f"https://www.amazon.co.jp/dp/{clean_code}"
                    
                    # Add a random delay to appear more human-like
                    delay = RETRY_DELAY_BASE * (0.5 + random.random())
                    print(f"Waiting {delay:.2f} seconds before scraping product page")
                    time.sleep(delay)
                    
                    # Create a more realistic browser fingerprint
                    user_agent = random.choice(USER_AGENTS)
                    
                    # Add realistic headers
                    headers = {
                        'User-Agent': user_agent,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0'
                    }
                    
                    # Make the request
                    response = requests.get(product_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        # Parse the HTML
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Check for CAPTCHA
                        if 'api-services-support@amazon.com' in response.text or 'Type the characters you see in this image' in response.text:
                            print(f"CAPTCHA detected when accessing product {clean_code}")
                            return None
                        
                        # Extract the title
                        title = None
                        title_elem = soup.select_one('#productTitle')
                        if title_elem:
                            title = title_elem.text.strip()
                        
                        if not title:
                            title_elem = soup.select_one('h1.a-size-large')
                            if title_elem:
                                title = title_elem.text.strip()
                        
                        if not title:
                            title = f"Amazon Product {clean_code}"
                        
                        # Extract the price
                        price = 0
                        price_elem = soup.select_one('.a-price .a-offscreen')
                        if price_elem:
                            price_text = price_elem.text.strip()
                            # Remove currency symbols and commas
                            price_digits = ''.join(filter(str.isdigit, price_text))
                            if price_digits:
                                price = int(price_digits)
                        
                        # Extract the image URL
                        image_url = None
                        img_elem = soup.select_one('#landingImage')
                        if img_elem and img_elem.has_attr('src'):
                            image_url = img_elem['src']
                        
                        if not image_url:
                            img_elem = soup.select_one('#imgBlkFront')
                            if img_elem and img_elem.has_attr('src'):
                                image_url = img_elem['src']
                        
                        if not image_url:
                            img_elem = soup.select_one('.a-dynamic-image')
                            if img_elem and img_elem.has_attr('src'):
                                image_url = img_elem['src']
                        
                        if not image_url:
                            image_url = self.default_image
                        
                        # Create the product URL with affiliate tag
                        product_url = f"https://www.amazon.co.jp/dp/{clean_code}?tag={AMAZON_PARTNER_TAG}"
                        
                        # Create a product data dictionary
                        product_data = {
                            "asin": clean_code,
                            "title": title,
                            "price": price,
                            "url": product_url,
                            "image_url": image_url,
                            "source": "amazon",
                            "availability": True
                        }
                        
                        print(f"Successfully scraped product {clean_code}")
                        return [product_data]
                    else:
                        print(f"Failed to scrape product {clean_code}: {response.status_code}")
                except Exception as e:
                    print(f"Error scraping product {clean_code}: {e}")
            
            # If we get here, direct product access failed
            print(f"Direct product access failed for {product_code}")
            return None
        
        except Exception as e:
            print(f"Error in _try_direct_product_access: {e}")
            return None

    def _get_fallback_products(self, keywords, limit=5):
        """
        Generate fallback product results when all other methods fail
        """
        print(f"Generating fallback products for '{keywords}'")
        
        # Create a better search URL for the fallback
        # For product codes, try to create a direct product URL first
        fallback_url = ""
        if re.match(r'^[A-Za-z0-9\-]+$', keywords):
            # Try direct product URL with clean code (no hyphens)
            clean_code = keywords.replace('-', '')
            if len(clean_code) == 10:  # ASIN length
                fallback_url = f"https://www.amazon.co.jp/dp/{clean_code}"
            else:
                # Try both with and without hyphens in the search
                fallback_url = f"https://www.amazon.co.jp/s?k={urllib.parse.quote(keywords)}+OR+{urllib.parse.quote(clean_code)}"
        else:
            # Regular search URL
            fallback_url = f"https://www.amazon.co.jp/s?k={urllib.parse.quote(keywords)}"
        
        # Add affiliate tag if available
        if AMAZON_PARTNER_TAG and '&tag=' not in fallback_url and '?tag=' not in fallback_url:
            separator = '&' if '?' in fallback_url else '?'
            fallback_url = f"{fallback_url}{separator}tag={AMAZON_PARTNER_TAG}"
        
        # Create a single fallback product
        fallback_product = {
            "asin": "FALLBACK",
            "title": f"{keywords} (Amazon)",
            "price": 0,
            "url": fallback_url,
            "image_url": self.default_image,
            "source": "amazon",
            "availability": False
        }
        
        # Return the requested number of fallback products
        return [fallback_product] * min(limit, 1)

    def _expand_search_keywords(self, keywords, direct_search=False):
        """
        Expand search keywords to improve match rate
        
        Args:
            keywords (str): The search keywords
            direct_search (bool): If True, only use the exact model number without variations
        """
        # For direct search with model numbers, don't expand keywords
        if direct_search and re.match(r'^[A-Za-z0-9\-]+$', keywords):
            print(f"Direct search enabled. Using exact model number: {keywords}")
            return f'"{keywords}"'  # Just use the exact model number with quotes
        
        # For product codes, try to format them in different ways to improve search results
        if re.match(r'^[A-Za-z0-9\-]+$', keywords):
            # Create variations of the product code for better search results
            variations = [
                f'"{keywords}"',                     # Original with quotes
                f'"{keywords.replace("-", "")}"',    # Without hyphens
                f'"{" ".join(keywords.split("-"))}"' # Spaces instead of hyphens
            ]
            return " OR ".join(variations)
        
        # For regular keywords, just add quotes
        return f'"{keywords}"'
    
    def _scrape_amazon_search(self, keywords, limit=5):
        """
        Scrape Amazon search results when API fails
        """
        try:
            # Encode the search query
            encoded_query = urllib.parse.quote(keywords)
            base_url = f"https://www.amazon.co.jp/s?k={encoded_query}"
            
            results = []
            
            for attempt in range(MAX_RETRIES):
                try:
                    # Add a random delay between attempts with exponential backoff
                    if attempt > 0:
                        delay = min(RETRY_DELAY_MAX, RETRY_DELAY_BASE * (2 ** attempt))
                        # Add jitter to appear more human-like
                        delay = delay * (0.5 + random.random() * 1.5)
                        print(f"Waiting {delay:.2f} seconds before retry {attempt + 1}/{MAX_RETRIES}")
                        time.sleep(delay)
                    
                    # Create a more realistic browser fingerprint
                    user_agent = random.choice(USER_AGENTS)
                    
                    # Add realistic headers
                    headers = {
                        'User-Agent': user_agent,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Sec-Fetch-User': '?1',
                        'Cache-Control': 'max-age=0'
                    }
                    
                    # Make the request
                    response = requests.get(base_url, headers=headers, timeout=10)
                    
                    if response.status_code == 503:
                        print(f"Amazon returned 503 on attempt {attempt + 1}/{MAX_RETRIES}")
                        continue
                        
                    if response.status_code != 200:
                        print(f"Failed to scrape Amazon: {response.status_code} on attempt {attempt + 1}/{MAX_RETRIES}")
                        continue
                    
                    # Parse the HTML
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Check for CAPTCHA
                    if 'api-services-support@amazon.com' in response.text or 'Type the characters you see in this image' in response.text:
                        print(f"CAPTCHA detected on attempt {attempt + 1}/{MAX_RETRIES}")
                        continue
                    
                    # Multiple selectors for product items
                    product_selectors = [
                        '.s-result-item[data-asin]:not([data-asin=""])',
                        '.sg-col-4-of-12.s-result-item',
                        '.sg-col-4-of-16.s-result-item',
                        '.sg-col-4-of-20.s-result-item',
                        '.s-asin',
                        'div[data-component-type="s-search-result"]'
                    ]
                    
                    # Try each selector
                    items = []
                    for selector in product_selectors:
                        items = soup.select(selector)
                        if items:
                            print(f"Found {len(items)} items with selector: {selector}")
                            break
                    
                    # Process the items
                    for index, item in enumerate(items):
                        if index >= limit:
                            break
                            
                        try:
                            # Get the ASIN
                            asin = None
                            if item.has_attr('data-asin'):
                                asin = item['data-asin']
                            
                            if not asin:
                                asin_elem = item.select_one('[data-asin]')
                                if asin_elem and asin_elem.has_attr('data-asin'):
                                    asin = asin_elem['data-asin']
                            
                            if not asin:
                                link_elem = item.select_one('a[href*="/dp/"]')
                                if link_elem and link_elem.has_attr('href'):
                                    url = link_elem['href']
                                    asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
                                    if asin_match:
                                        asin = asin_match.group(1)
                            
                            # If we still don't have an ASIN, skip this item
                            if not asin:
                                continue
                            
                            # Get the title
                            title = None
                            title_elem = item.select_one('.a-text-normal')
                            if title_elem:
                                title = title_elem.text.strip()
                            
                            if not title:
                                title_elem = item.select_one('h2')
                                if title_elem:
                                    title = title_elem.text.strip()
                            
                            if not title:
                                title = f"Amazon Product {asin}"
                            
                            # Get the price
                            price = 0
                            price_elem = item.select_one('.a-price .a-offscreen')
                            if price_elem:
                                price_text = price_elem.text.strip()
                                # Remove currency symbols and commas
                                price_digits = ''.join(filter(str.isdigit, price_text))
                                if price_digits:
                                    price = int(price_digits)
                            
                            # Get the image URL
                            image_url = None
                            img_elem = item.select_one('.s-image')
                            if img_elem and img_elem.has_attr('src'):
                                image_url = img_elem['src']
                            
                            # Get the product URL
                            product_url = f"https://www.amazon.co.jp/dp/{asin}?tag={AMAZON_PARTNER_TAG}"
                            link_elem = item.select_one('a.a-link-normal[href]')
                            if link_elem and link_elem.has_attr('href'):
                                href = link_elem['href']
                                if href.startswith('/'):
                                    product_url = f"https://www.amazon.co.jp{href}"
                                elif href.startswith('http'):
                                    product_url = href
                                
                                # Add affiliate tag if not present
                            if '&tag=' not in product_url and '?tag=' not in product_url:
                                    separator = '&' if '?' in product_url else '?'
                                    product_url = f"{product_url}{separator}tag={AMAZON_PARTNER_TAG}"
                            
                            # Create a product data dictionary
                            product_data = {
                                "asin": asin,
                                "title": title,
                                "price": price,
                                "url": product_url,
                                "image_url": image_url,
                                "source": "amazon",
                                "availability": True
                            }
                            
                            results.append(product_data)
                        except Exception as e:
                            print(f"Error processing Amazon search result: {e}")
                    
                    # If we found products, return them
                    if results:
                        print(f"Found {len(results)} products via scraping")
                        return results
                    
                except Exception as e:
                    print(f"Error in Amazon scraping (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            
            # If we get here, all attempts failed
            print("All scraping attempts failed, using fallback results")
            return self._get_fallback_products(keywords, limit)
        except Exception as e:
            print(f"Error in Amazon scraping: {e}")
            return self._get_fallback_products(keywords, limit)
    
    def _extract_price(self, price_str):
        """
        Extract a numeric price from a string
        """
        try:
            if isinstance(price_str, (int, float)):
                return int(price_str)
            
            # Remove currency symbols, commas, and spaces
            price_digits = ''.join(filter(str.isdigit, str(price_str)))
            if price_digits:
                return int(price_digits)
            return 0
        except Exception as e:
            print(f"Error extracting price from '{price_str}': {e}")
            return 0
    
    def get_items_by_request(self, request_data: dict) -> dict:
        """
        Get items using PA-API with a custom request structure
        
        Args:
            request_data (dict): Request data in the format:
                {
                    "ItemIds": ["B0199980K4", "B000HZD168", ...],
                    "ItemIdType": "ASIN",
                    "LanguagesOfPreference": ["en_US"],
                    "Marketplace": "www.amazon.com",
                    "PartnerTag": "xyz-20",
                    "PartnerType": "Associates",
                    "Resources": ["Images.Primary.Small", "ItemInfo.Title", ...]
                }
        
        Returns:
            dict: Response containing items data
        """
        try:
            # Extract request parameters
            item_ids = request_data.get("ItemIds", [])
            item_id_type = request_data.get("ItemIdType", "ASIN")
            languages_of_preference = request_data.get("LanguagesOfPreference", ["en_US"])
            marketplace = request_data.get("Marketplace", "www.amazon.com")
            partner_tag = request_data.get("PartnerTag", AMAZON_PARTNER_TAG)
            partner_type = request_data.get("PartnerType", "Associates")
            resources = request_data.get("Resources", [])
            
            # Validate inputs
            if not item_ids:
                return {"error": "ItemIds is required and cannot be empty"}
            
            if not isinstance(item_ids, list):
                return {"error": "ItemIds must be a list"}
            
            # Validate ASINs if ItemIdType is ASIN
            if item_id_type == "ASIN":
                validated_asins = []
                for item_id in item_ids:
                    # Clean ASIN (remove hyphens, convert to uppercase)
                    clean_asin = str(item_id).replace('-', '').upper()
                    if re.match(r'^[A-Z0-9]{10}$', clean_asin):
                        validated_asins.append(clean_asin)
                    else:
                        print(f"Warning: Invalid ASIN format: {item_id}, skipping")
                
                if not validated_asins:
                    return {"error": "No valid ASINs found in ItemIds"}
                
                item_ids = validated_asins
            
            print(f"Getting items via PA-API: {len(item_ids)} items, Marketplace: {marketplace}")
            
            # Check if we have a valid PAAPI client
            if not self.client:
                return {"error": "Amazon PAAPI client not initialized. Please check your credentials."}
            
            # Map marketplace to country code for the API client
            marketplace_to_country = {
                "www.amazon.com": "US",
                "www.amazon.co.jp": "JP",
                "www.amazon.co.uk": "UK",
                "www.amazon.de": "DE",
                "www.amazon.fr": "FR",
                "www.amazon.it": "IT",
                "www.amazon.es": "ES",
                "www.amazon.ca": "CA",
                "www.amazon.com.au": "AU",
                "www.amazon.com.mx": "MX",
                "www.amazon.in": "IN",
                "www.amazon.com.br": "BR"
            }
            
            # Get country code from marketplace
            country_code = marketplace_to_country.get(marketplace, "US")
            
            # If the marketplace is different from the initialized client, we need to handle it
            # For now, we'll use the existing client and note the limitation
            if marketplace != "www.amazon.co.jp" and country_code != "JP":
                print(f"Warning: Client initialized for JP marketplace, but request is for {marketplace}")
                print(f"Attempting to use existing client - results may vary")
            
            # Prepare the get_items call
            # The amazon-paapi library handles resources automatically, but we can specify languages
            try:
                # Call get_items with the ASINs
                items_result = self.client.get_items(
                    item_ids,
                    languages_of_preference=languages_of_preference if languages_of_preference else None,
                    include_unavailable=False
                )
                
                if not items_result:
                    return {"error": "No items found in PA-API response", "items": []}
                
                # Handle both list and object responses
                items_list = items_result if isinstance(items_result, list) else (items_result.items if hasattr(items_result, 'items') else [])
                
                if not items_list:
                    return {"error": "No items found in PA-API response", "items": []}
                
                # Process items based on requested resources
                processed_items = []
                for item in items_list:
                    try:
                        # Skip items with None ASIN
                        if not hasattr(item, 'asin') or item.asin is None:
                            continue
                        
                        item_data = {}
                        
                        # Extract ASIN
                        item_data["ASIN"] = item.asin
                        
                        # Extract ParentASIN if requested
                        if "ParentASIN" in resources:
                            if hasattr(item, 'parent_asin'):
                                item_data["ParentASIN"] = item.parent_asin
                            elif hasattr(item, 'item_info') and hasattr(item.item_info, 'parent_asin'):
                                item_data["ParentASIN"] = item.item_info.parent_asin
                            else:
                                item_data["ParentASIN"] = None
                        
                        # Extract Images.Primary.Small if requested
                        if any("Images" in r for r in resources):
                            image_url = self.default_image
                            if hasattr(item, 'images') and hasattr(item.images, 'primary'):
                                if "Small" in str(resources):
                                    if hasattr(item.images.primary, 'small') and hasattr(item.images.primary.small, 'url'):
                                        image_url = item.images.primary.small.url
                                elif "Large" in str(resources):
                                    if hasattr(item.images.primary, 'large') and hasattr(item.images.primary.large, 'url'):
                                        image_url = item.images.primary.large.url
                                elif hasattr(item.images.primary, 'medium') and hasattr(item.images.primary.medium, 'url'):
                                    image_url = item.images.primary.medium.url
                                elif hasattr(item.images.primary, 'large') and hasattr(item.images.primary.large, 'url'):
                                    image_url = item.images.primary.large.url
                            
                            item_data["Images"] = {
                                "Primary": {
                                    "Small": {"URL": image_url} if image_url else None
                                }
                            }
                        
                        # Extract ItemInfo.Title if requested
                        if any("ItemInfo.Title" in r for r in resources):
                            title = "Amazon Product"
                            if hasattr(item, 'item_info') and hasattr(item.item_info, 'title'):
                                if hasattr(item.item_info.title, 'display_value'):
                                    title = item.item_info.title.display_value
                                elif hasattr(item.item_info.title, 'label'):
                                    title = item.item_info.title.label
                            
                            item_data["ItemInfo"] = {
                                "Title": {"DisplayValue": title}
                            }
                        
                        # Extract ItemInfo.Features if requested
                        if any("ItemInfo.Features" in r for r in resources):
                            features = []
                            if hasattr(item, 'item_info') and hasattr(item.item_info, 'features'):
                                if hasattr(item.item_info.features, 'display_values'):
                                    features = item.item_info.features.display_values
                                elif hasattr(item.item_info.features, 'values'):
                                    features = item.item_info.features.values
                            
                            if "ItemInfo" not in item_data:
                                item_data["ItemInfo"] = {}
                            item_data["ItemInfo"]["Features"] = {
                                "DisplayValues": features
                            }
                        
                        # Extract Offers.Summaries.HighestPrice if requested
                        if any("Offers" in r for r in resources):
                            highest_price = None
                            lowest_price = None
                            availability = False
                            
                            if hasattr(item, 'offers') and hasattr(item.offers, 'listings') and item.offers.listings:
                                listing = item.offers.listings[0]
                                
                                # Get price
                                if hasattr(listing, 'price') and hasattr(listing.price, 'amount'):
                                    price_amount = float(listing.price.amount)
                                    currency = getattr(listing.price, 'currency', 'USD')
                                    lowest_price = {
                                        "Amount": price_amount,
                                        "Currency": currency
                                    }
                                    highest_price = lowest_price  # For single listing, highest = lowest
                                
                                # Get availability
                                if hasattr(listing, 'availability') and hasattr(listing.availability, 'type'):
                                    availability = listing.availability.type == 'Now'
                            
                            # Check summaries if available
                            if hasattr(item, 'offers') and hasattr(item.offers, 'summaries'):
                                summaries = item.offers.summaries
                                if summaries and len(summaries) > 0:
                                    summary = summaries[0]
                                    if hasattr(summary, 'highest_price') and hasattr(summary.highest_price, 'amount'):
                                        highest_price = {
                                            "Amount": float(summary.highest_price.amount),
                                            "Currency": getattr(summary.highest_price, 'currency', 'USD')
                                        }
                                    if hasattr(summary, 'lowest_price') and hasattr(summary.lowest_price, 'amount'):
                                        lowest_price = {
                                            "Amount": float(summary.lowest_price.amount),
                                            "Currency": getattr(summary.lowest_price, 'currency', 'USD')
                                        }
                            
                            item_data["Offers"] = {
                                "Summaries": [{
                                    "HighestPrice": highest_price,
                                    "LowestPrice": lowest_price,
                                    "OfferCount": 1 if availability else 0
                                }],
                                "Availability": {
                                    "Type": "Now" if availability else "Unavailable"
                                }
                            }
                        
                        # Add detail page URL
                        detail_page_url = f"https://{marketplace}/dp/{item.asin}"
                        if hasattr(item, 'detail_page_url'):
                            detail_page_url = item.detail_page_url
                        
                        # Add affiliate tag if partner tag is provided
                        if partner_tag and '&tag=' not in detail_page_url and '?tag=' not in detail_page_url:
                            separator = '&' if '?' in detail_page_url else '?'
                            detail_page_url = f"{detail_page_url}{separator}tag={partner_tag}"
                        
                        item_data["DetailPageURL"] = detail_page_url
                        
                        processed_items.append(item_data)
                        
                    except Exception as e:
                        print(f"Error processing item: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                return {
                    "ItemsResult": {
                        "Items": processed_items
                    },
                    "ItemsRequest": {
                        "ItemIds": item_ids,
                        "ItemIdType": item_id_type,
                        "LanguagesOfPreference": languages_of_preference,
                        "Marketplace": marketplace,
                        "PartnerTag": partner_tag,
                        "PartnerType": partner_type,
                        "Resources": resources
                    }
                }
                
            except ItemsNotFound as e:
                return {
                    "error": f"Items not found: {str(e)}",
                    "items": []
                }
            except Exception as e:
                print(f"Error calling PA-API get_items: {e}")
                import traceback
                traceback.print_exc()
                return {
                    "error": f"PA-API request failed: {str(e)}",
                    "items": []
                }
                
        except Exception as e:
            print(f"Error in get_items_by_request: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": f"Request processing failed: {str(e)}",
                "items": []
            }

amazon_api = AmazonAPI() 
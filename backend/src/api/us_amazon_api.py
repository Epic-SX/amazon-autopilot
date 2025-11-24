"""
US Amazon API Integration
Fetches product information and prices from Amazon.com (US)
"""
import requests
from typing import List, Optional, Dict, Any
from src.models.product import ProductDetail
import time
from bs4 import BeautifulSoup
import re
import json
import urllib.parse

class USAmazonAPI:
    """
    API client for Amazon.com (US)
    Uses Product Advertising API or web scraping as fallback
    """
    
    def __init__(self):
        self.session = requests.Session()
        # Rotate between multiple realistic user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        ]
        self._update_headers()
        self.base_url = "https://www.amazon.com"
        self.use_proxy = False  # Set to True if you have a proxy service
    
    def _update_headers(self):
        """Update session headers with a random user agent"""
        import random
        user_agent = random.choice(self.user_agents)
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Referer': 'https://www.amazon.com/',
        })
    
    def search_products(self, keywords: str, limit: int = 5) -> List[ProductDetail]:
        """
        Search for products on US Amazon
        
        Args:
            keywords: Search keywords
            limit: Maximum number of results
        
        Returns:
            List of ProductDetail objects
        """
        try:
            # Try to use Product Advertising API first
            # If not available, fall back to web scraping
            products = self._search_via_paapi(keywords, limit)
            
            if not products:
                products = self._search_via_web(keywords, limit)
            
            return products
        except Exception as e:
            print(f"Error searching US Amazon: {e}")
            return []
    
    def get_product_by_asin(self, asin: str) -> Optional[ProductDetail]:
        """
        Get product details by ASIN from US Amazon
        Uses search page scraping (same approach as Japan Amazon) to avoid bot detection
        
        Args:
            asin: Product ASIN
        
        Returns:
            ProductDetail object or None
        """
        # Use search-based approach (same as Japan Amazon) to avoid bot detection
        # This is more reliable than direct product page access
        return self._get_product_from_search(asin)
    
    def _get_product_from_search(self, asin: str) -> Optional[ProductDetail]:
        """
        Get product by searching for ASIN on Amazon.com
        Uses the same approach as Japan Amazon scraping with retry logic
        
        Args:
            asin: Product ASIN
        
        Returns:
            ProductDetail object or None
        """
        import random
        
        # Constants for retry logic (same as Japan Amazon)
        MAX_RETRIES = 3
        RETRY_DELAY_BASE = 1.0
        RETRY_DELAY_MAX = 5.0
        
        # Use search URL format: https://www.amazon.com/s?k=ASIN (same as Japan)
        search_url = f"{self.base_url}/s?k={urllib.parse.quote(asin)}"
        
        for attempt in range(MAX_RETRIES):
            try:
                print(f"Fetching US Amazon product from search (attempt {attempt + 1}/{MAX_RETRIES}): {search_url}")
                
                # Rotate user agent for each attempt
                self._update_headers()
                
                # Add random delay with exponential backoff (same as Japan Amazon)
                if attempt > 0:
                    delay = min(RETRY_DELAY_MAX, RETRY_DELAY_BASE * (2 ** attempt))
                    # Add jitter to appear more human-like
                    delay = delay * (0.5 + random.random() * 1.5)
                    print(f"Waiting {delay:.2f} seconds before retry {attempt + 1}/{MAX_RETRIES}")
                    time.sleep(delay)
                else:
                    # First attempt - shorter delay
                    delay = random.uniform(0.5, 2.0)
                    print(f"Waiting {delay:.2f} seconds before request...")
                    time.sleep(delay)
                
                # Try to visit homepage first to get cookies (same as Japan)
                try:
                    self.session.get(self.base_url, timeout=10)
                    time.sleep(random.uniform(0.3, 1.0))
                except:
                    pass
                
                response = self.session.get(search_url, timeout=15, allow_redirects=True)
                
                # Handle 503 Service Unavailable (same as Japan Amazon)
                if response.status_code == 503:
                    print(f"Amazon returned 503 on attempt {attempt + 1}/{MAX_RETRIES}")
                    if attempt < MAX_RETRIES - 1:
                        continue  # Retry
                    else:
                        print(f"Failed after {MAX_RETRIES} attempts due to 503 errors")
                        return None
                
                if response.status_code != 200:
                    print(f"Error: Got status code {response.status_code} for search")
                    if attempt < MAX_RETRIES - 1:
                        continue  # Retry
                    return None
                
                # Check for CAPTCHA (same check as Japan Amazon)
                if 'api-services-support@amazon.com' in response.text or 'Type the characters you see in this image' in response.text:
                    print(f"CAPTCHA detected on US Amazon search page (attempt {attempt + 1}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES - 1:
                        # Wait longer before retry on CAPTCHA
                        time.sleep(random.uniform(3.0, 5.0))
                        continue
                    return None
                
                soup = BeautifulSoup(response.content, 'html.parser')
                result = self._extract_from_search_results(soup, asin)
                
                if result:
                    return result
                elif attempt < MAX_RETRIES - 1:
                    print(f"No product found, retrying...")
                    continue
                else:
                    return None
                
            except requests.exceptions.RequestException as e:
                print(f"Request error on attempt {attempt + 1}/{MAX_RETRIES}: {e}")
                if attempt < MAX_RETRIES - 1:
                    continue
                return None
            except Exception as e:
                print(f"Error getting product from search (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    continue
                import traceback
                traceback.print_exc()
                return None
        
        return None
    
    def _extract_from_search_results(self, soup: BeautifulSoup, target_asin: str) -> Optional[ProductDetail]:
        """
        Extract product information from Amazon search results page
        Uses the same approach as Japan Amazon scraping
        
        Args:
            soup: BeautifulSoup object of the search results page
            target_asin: The ASIN we're looking for
        
        Returns:
            ProductDetail object or None
        """
        try:
            # Use the same selectors as Japan Amazon scraping
            product_selectors = [
                '.s-result-item[data-asin]:not([data-asin=""])',
                '.sg-col-4-of-12.s-result-item',
                '.sg-col-4-of-16.s-result-item',
                '.sg-col-4-of-20.s-result-item',
                '.s-asin',
                'div[data-component-type="s-search-result"]'
            ]
            
            # Try each selector (same as Japan Amazon)
            items = []
            for selector in product_selectors:
                items = soup.select(selector)
                if items:
                    print(f"Found {len(items)} items with selector: {selector}")
                    break
            
            if not items:
                print(f"No search results found for ASIN {target_asin}")
                return None
            
            # Look for the product with matching ASIN
            for item in items:
                # Get ASIN (same method as Japan Amazon)
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
                
                if not asin:
                    continue
                
                # Check if this is the product we're looking for
                if asin.upper() == target_asin.upper():
                    print(f"Found product with matching ASIN in search results: {asin}")
                    
                    # Extract title (same as Japan Amazon)
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
                    
                    # Extract price (same as Japan Amazon)
                    price = None
                    price_elem = item.select_one('.a-price .a-offscreen')
                    if price_elem:
                        price_text = price_elem.text.strip()
                        # Remove currency symbols and parse
                        price = self._parse_price(price_text)
                        if price:
                            # Convert to float (US prices are in dollars)
                            price = float(price)
                    
                    # Extract image (same as Japan Amazon)
                    image_url = None
                    img_elem = item.select_one('.s-image')
                    if img_elem:
                        image_url = img_elem.get('src') or img_elem.get('data-src')
                    
                    # Extract URL (same as Japan Amazon)
                    product_url = f"{self.base_url}/dp/{asin}"
                    link_elem = item.select_one('a.a-link-normal[href]')
                    if link_elem and link_elem.has_attr('href'):
                        href = link_elem['href']
                        if href.startswith('/'):
                            product_url = f"{self.base_url}{href}"
                        elif href.startswith('http'):
                            product_url = href
                    
                    # Extract availability
                    availability = bool(item.find('span', string=re.compile(r'Add to Cart|See options|in stock', re.I)))
                    
                    if title or price or image_url:
                        print(f"Extracted US product from search: Title: {title[:50] if title else 'N/A'}..., Price: ${price}, Image: {bool(image_url)}")
                        return ProductDetail(
                            source='Amazon US',
                            title=title,
                            price=price,
                            url=product_url,
                            image_url=image_url,
                            description=None,
                            availability=availability,
                            asin=asin
                        )
            
            print(f"Product with ASIN {target_asin} not found in search results")
            return None
            
        except Exception as e:
            print(f"Error extracting from search results: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _search_via_paapi(self, keywords: str, limit: int) -> List[ProductDetail]:
        """
        Search using Product Advertising API (if configured)
        """
        # TODO: Implement PA-API integration for US Amazon
        # This would require US Amazon PA-API credentials
        return []
    
    def _search_via_web(self, keywords: str, limit: int) -> List[ProductDetail]:
        """
        Search via web scraping (fallback method)
        """
        try:
            search_url = f"{self.base_url}/s?k={keywords.replace(' ', '+')}"
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            products = []
            
            # Find product containers (Amazon's structure may vary)
            product_containers = soup.find_all('div', {'data-component-type': 's-search-result'})[:limit]
            
            for container in product_containers:
                try:
                    # Extract ASIN
                    asin = container.get('data-asin', '')
                    if not asin:
                        continue
                    
                    # Extract title
                    title_elem = container.find('h2', class_='a-size-mini')
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    
                    # Extract price
                    price_elem = container.find('span', class_='a-price-whole')
                    price_text = price_elem.get_text(strip=True) if price_elem else ''
                    price = self._parse_price(price_text)
                    
                    # Extract image
                    img_elem = container.find('img', class_='s-image')
                    image_url = img_elem.get('src', '') if img_elem else ''
                    
                    # Extract URL
                    link_elem = container.find('a', class_='a-link-normal')
                    product_url = f"{self.base_url}{link_elem.get('href', '')}" if link_elem else ''
                    
                    products.append(ProductDetail(
                        source='Amazon US',
                        title=title,
                        price=price,
                        url=product_url,
                        image_url=image_url,
                        asin=asin
                    ))
                except Exception as e:
                    print(f"Error parsing product: {e}")
                    continue
            
            return products
        except Exception as e:
            print(f"Error in web search: {e}")
            return []
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract product title from product page with multiple fallbacks"""
        # Try multiple selectors for title
        title_selectors = [
            ('span', {'id': 'productTitle'}),
            ('h1', {'id': 'title'}),
            ('h1', {'data-automation-id': 'title'}),
            ('h1', {'class': 'a-size-large'}),
            ('span', {'data-automation-id': 'product-title'}),
            ('h1', {'class': 'a-size-base-plus'}),
            ('h1', {'class': 'a-size-large product-title-word-break'}),
        ]
        
        for tag, attrs in title_selectors:
            title_elem = soup.find(tag, attrs)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 3:  # Make sure it's not just whitespace
                    return title
        
        # Try CSS selectors as fallback
        css_selectors = [
            '#productTitle',
            '#title',
            'h1.a-size-large',
            'span[data-automation-id="product-title"]',
            'h1.product-title',
            'h1#title',
            '#productTitle_feature_div',
            '.product-title',
        ]
        
        for selector in css_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 3:
                    return title
        
        # Try to find any h1 tag that might be the title
        h1_tags = soup.find_all('h1', limit=5)
        for h1 in h1_tags:
            title = h1.get_text(strip=True)
            if title and len(title) > 10 and len(title) < 200:  # Reasonable title length
                # Check if it's not a generic page element
                if 'amazon' not in title.lower() or 'error' not in title.lower():
                    return title
        
        return ''
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract price from product page with multiple fallbacks"""
        # Try multiple price selectors
        price_selectors = [
            'span.a-price-whole',
            'span.a-price .a-offscreen',
            'span#priceblock_ourprice',
            'span#priceblock_dealprice',
            'span#priceblock_saleprice',
            'span.a-offscreen',
            '.a-price[data-a-color="price"] .a-offscreen',
            'span[data-a-color="price"] .a-offscreen',
            '.a-price-range .a-offscreen',
            '#price',
            '.priceToPay .a-offscreen',
            '.a-price.a-text-price.a-size-medium.apexPriceToPay .a-offscreen',
            'span[data-a-color="base"] .a-offscreen',
            '.a-price .a-offscreen',
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price = self._parse_price(price_text)
                if price and price > 0:
                    return price
        
        # Try to find price in data attributes
        price_elements = soup.find_all(attrs={'data-a-color': 'price'})
        for elem in price_elements:
            price_text = elem.get_text(strip=True)
            price = self._parse_price(price_text)
            if price and price > 0:
                return price
        
        # Try to find price in JSON-LD structured data
        try:
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    if not script.string:
                        continue
                    data = json.loads(script.string)
                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    if isinstance(data, dict):
                        offers = data.get('offers', {})
                        if isinstance(offers, dict):
                            price = offers.get('price')
                            if price:
                                price_float = self._parse_price(str(price))
                                if price_float and price_float > 0:
                                    return price_float
                        # Also check for price directly
                        price = data.get('price')
                        if price:
                            price_float = self._parse_price(str(price))
                            if price_float and price_float > 0:
                                return price_float
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
        except Exception as e:
            print(f"Error parsing JSON-LD for price: {e}")
        
        return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parse price string to float"""
        if not price_text:
            return None
        
        # Remove currency symbols and commas
        price_text = re.sub(r'[^\d.]', '', price_text)
        try:
            return float(price_text)
        except ValueError:
            return None
    
    def _extract_image(self, soup: BeautifulSoup) -> str:
        """Extract product image URL with multiple fallbacks"""
        # Try multiple image selectors
        image_selectors = [
            ('img', {'id': 'landingImage'}),
            ('img', {'id': 'imgBlkFront'}),
            ('img', {'data-a-image-name': 'landingImage'}),
            ('img', {'class': 'a-dynamic-image'}),
        ]
        
        for tag, attrs in image_selectors:
            img_elem = soup.find(tag, attrs)
            if img_elem:
                # Try data-src first (lazy loading), then src
                image_url = img_elem.get('data-src') or img_elem.get('src') or img_elem.get('data-old-src')
                if image_url:
                    # Clean up the URL (remove query parameters that might limit size)
                    if '._' in image_url:
                        # Amazon image URLs often have size parameters like ._AC_SL1500_
                        # Try to get a larger version
                        image_url = re.sub(r'\._AC_[^_]+_', '._AC_SL1500_', image_url)
                    return image_url
        
        # Try CSS selectors
        css_selectors = [
            '#landingImage',
            '#imgBlkFront',
            'img[data-a-image-name="landingImage"]',
            '.a-dynamic-image',
            '#main-image',
        ]
        
        for selector in css_selectors:
            img_elem = soup.select_one(selector)
            if img_elem:
                image_url = img_elem.get('data-src') or img_elem.get('src') or img_elem.get('data-old-src')
                if image_url:
                    if '._' in image_url:
                        image_url = re.sub(r'\._AC_[^_]+_', '._AC_SL1500_', image_url)
                    return image_url
        
        return ''
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract product description with multiple fallbacks"""
        # Try multiple description selectors
        desc_selectors = [
            ('div', {'id': 'productDescription'}),
            ('div', {'id': 'feature-bullets'}),
            ('div', {'class': 'product-description'}),
            ('div', {'data-feature-name': 'productDescription'}),
        ]
        
        description_parts = []
        
        for tag, attrs in desc_selectors:
            desc_elem = soup.find(tag, attrs)
            if desc_elem:
                text = desc_elem.get_text(strip=True)
                if text and len(text) > 20:  # Only use substantial descriptions
                    description_parts.append(text)
        
        # Also try to get feature bullets
        feature_bullets = soup.find('div', {'id': 'feature-bullets'})
        if feature_bullets:
            bullets = feature_bullets.find_all('span', class_='a-list-item')
            if bullets:
                bullet_texts = [b.get_text(strip=True) for b in bullets[:5] if b.get_text(strip=True)]
                if bullet_texts:
                    description_parts.append(' '.join(bullet_texts))
        
        if description_parts:
            return ' '.join(description_parts[:3])  # Combine first 3 parts
        
        return ''
    
    def _extract_availability(self, soup: BeautifulSoup) -> bool:
        """Extract availability status with multiple fallbacks"""
        # Try multiple availability selectors
        availability_selectors = [
            ('div', {'id': 'availability'}),
            ('span', {'id': 'availability'}),
            ('div', {'class': 'a-section a-spacing-none'}),
            ('span', {'data-automation-id': 'availability'}),
        ]
        
        for tag, attrs in availability_selectors:
            availability_elem = soup.find(tag, attrs)
            if availability_elem:
                availability_text = availability_elem.get_text(strip=True).lower()
                # Check for positive indicators
                if any(indicator in availability_text for indicator in ['in stock', 'available', 'ships from', 'add to cart']):
                    return True
                # Check for negative indicators
                if any(indicator in availability_text for indicator in ['out of stock', 'unavailable', 'currently unavailable', 'we don\'t know when']):
                    return False
        
        # Check if "Add to Cart" button exists (indicates availability)
        add_to_cart = soup.find('input', {'id': 'add-to-cart-button'}) or \
                     soup.find('span', {'id': 'submit.add-to-cart'}) or \
                     soup.find('button', {'id': 'add-to-cart-button'})
        if add_to_cart:
            return True
        
        # Check for "Buy Now" button
        buy_now = soup.find('input', {'id': 'buy-now-button'}) or \
                 soup.find('span', {'id': 'submit.buy-now'})
        if buy_now:
            return True
        
        # Default to False if we can't determine
        return False

# Global instance
us_amazon_api = USAmazonAPI()


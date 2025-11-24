from src.api.amazon_api import amazon_api
from src.api.rakuten_api import rakuten_api
from src.api.yahoo_api import yahoo_api
from src.config.settings import PRICE_THRESHOLD
from concurrent.futures import ThreadPoolExecutor
import re

class PriceComparisonEngine:
    def __init__(self):
        self.apis = {
            'Amazon': amazon_api,
            'Rakuten': rakuten_api,
            'Yahoo': yahoo_api
        }

    def compare_prices(self, product_info):
        """
        各サイトの価格を比較
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=len(self.apis)) as executor:
            future_to_api = {
                executor.submit(self._get_multiple_prices, api_name, api, product_info): api_name
                for api_name, api in self.apis.items()
            }
            
            for future in future_to_api:
                api_name = future_to_api[future]
                try:
                    price_info_list = future.result()
                    if price_info_list:
                        results.extend(price_info_list)
                except Exception as e:
                    print(f"Error getting price from {api_name}: {e}")

        return self.sort_and_filter_results(results)
        
    def compare_prices_direct(self, product_info):
        """
        各サイトの価格を比較 (直接検索モード)
        """
        print(f"DEBUG: Direct search for '{product_info}'")
        results = []
        
        with ThreadPoolExecutor(max_workers=len(self.apis)) as executor:
            future_to_api = {
                executor.submit(self._get_multiple_prices_direct, api_name, api, product_info): api_name
                for api_name, api in self.apis.items()
            }
            
            for future in future_to_api:
                api_name = future_to_api[future]
                try:
                    price_info_list = future.result()
                    if price_info_list:
                        results.extend(price_info_list)
                except Exception as e:
                    print(f"Error getting price from {api_name} (direct search): {e}")

        return self.sort_and_filter_results(results)
        
    def compare_prices_with_model_numbers(self, model_numbers):
        """
        複数の型番を使用して各サイトの価格を比較
        """
        print(f"DEBUG: Searching with multiple model numbers: {model_numbers}")
        all_results = []
        
        for model_number in model_numbers:
            try:
                # Get results for this model number
                results = self.compare_prices_direct(model_number)
                if results:
                    # Add a field to indicate which model number was used
                    for result in results:
                        result['model_number_used'] = model_number
                    all_results.extend(results)
            except Exception as e:
                print(f"Error searching for model number '{model_number}': {e}")
        
        return self.sort_and_filter_results(all_results)
        
    def get_detailed_products(self, product_info):
        """
        各サイトから詳細な商品情報を取得
        """
        print(f"DEBUG: Getting detailed products for: '{product_info}'")
        all_products = []
        
        # 各APIから詳細情報を取得
        for api_name, api in self.apis.items():
            try:
                if hasattr(api, 'get_product_details'):
                    print(f"DEBUG: Fetching products from {api_name} API")
                    products = api.get_product_details(product_info)
                    if products:
                        print(f"DEBUG: Found {len(products)} products from {api_name}")
                        all_products.extend(products)
                    else:
                        print(f"DEBUG: No products found from {api_name}")
            except Exception as e:
                print(f"Error getting product details from {api_name}: {e}")
                
        # 価格で昇順ソート
        sorted_products = sorted(all_products, key=lambda x: x.price if hasattr(x, 'price') else (x.get('price', float('inf')) if isinstance(x, dict) else float('inf')))
        
        print(f"DEBUG: Total products found across all sources: {len(sorted_products)}")
        # Print breakdown by source
        sources = {}
        for product in sorted_products:
            if product.source not in sources:
                sources[product.source] = 0
            sources[product.source] += 1
        
        for source, count in sources.items():
            print(f"DEBUG: {source}: {count} products")
            
        return sorted_products

    def get_detailed_products_direct(self, product_info):
        """
        Get detailed product information for a specific product
        """
        all_products = []
        api_results = {}
        
        # Convert to string in case we get a non-string input
        product_info = str(product_info).strip()
        
        # Check if this looks like a JAN code (13 digits or 8 digits)
        is_jan_code = bool(re.match(r'^[0-9]{8}$|^[0-9]{13}$', product_info))
        
        # Check if this is a common generic category that doesn't need strict filtering
        common_categories = ['laptop', 'ノートパソコン', 'パソコン', 'タブレット', 'スマホ', 'スマートフォン', 
                            'PC', 'コンピューター', 'computer', 'smartphone', 'tablet', 'phone']
        
        # Check if this is a laptop-related search
        laptop_brands = ['hp', 'dell', 'lenovo', 'asus', 'acer', 'msi', 'fujitsu', 'toshiba', 'nec', 'vaio']
        is_laptop_search = False
        
        # Check if product_info contains a laptop brand
        if any(brand.lower() in product_info.lower() for brand in laptop_brands):
            if any(category.lower() in product_info.lower() for category in ['laptop', 'ノートパソコン', 'パソコン', 'PC']):
                is_laptop_search = True
                print(f"DEBUG: Detected specific laptop search: {product_info}")
        
        is_common_category = any(category.lower() in product_info.lower() for category in common_categories)
        
        # Log what we're searching for
        print(f"DEBUG: Direct search for: {product_info} (JAN: {is_jan_code}, Common Category: {is_common_category}, Laptop: {is_laptop_search})")
        
        # For laptop searches, enhance the search query to be more specific
        search_terms = [product_info]
        if is_laptop_search:
            # Extract brand and key terms
            terms = product_info.split()
            brand = next((term for term in terms if term.lower() in laptop_brands), None)
            
            if brand:
                # Create additional specific search terms
                if 'windows' in product_info.lower():
                    search_terms.append(f"{brand} ノートパソコン windows")
                else:
                    search_terms.append(f"{brand} ノートパソコン")
                
                print(f"DEBUG: Enhanced laptop search terms: {search_terms}")
        
        # Iterate through each API to get products
        for api_name, api_instance in self.apis.items():
            try:
                print(f"DEBUG: Searching {api_name} for {product_info}")
                
                # For each search term, try to find products
                products = []
                for term in search_terms:
                    try:
                        # Get products from the API using the correct method name
                        if api_name == 'Amazon':
                            # For Amazon, use get_product_details
                            api_products = api_instance.get_product_details(term)
                        elif api_name == 'Yahoo' and is_jan_code:
                            # For Yahoo, use JAN code search if applicable
                            if hasattr(api_instance, 'get_products_by_jan'):
                                api_products = api_instance.get_products_by_jan(term)
                            else:
                                api_products = api_instance.get_product_details(term)
                        elif api_name == 'Rakuten' and is_jan_code:
                            # For Rakuten, use JAN code search if applicable
                            if hasattr(api_instance, 'get_products_by_jan'):
                                api_products = api_instance.get_products_by_jan(term)
                            else:
                                api_products = api_instance.get_product_details(term)
                        else:
                            # Regular search for other cases
                            api_products = api_instance.get_product_details(term)
                    except Exception as e:
                        print(f"Error calling API method for {api_name}: {e}")
                        api_products = []
                    
                    # If products found with this term, use them and stop trying other terms
                    if api_products and len(api_products) > 0:
                        print(f"DEBUG: Found {len(api_products)} products from {api_name} using term: {term}")
                        products = api_products
                        break
                
                # Store API results
                api_results[api_name] = products
                
                # For Amazon, include all products without filtering
                if api_name == 'Amazon':
                    all_products.extend(products)
                else:
                    # For other APIs, filter products based on various criteria
                    filtered_products = []
                    
                    # For common categories or laptop searches, accept more results
                    if (is_common_category or is_laptop_search) and api_name in ['Rakuten', 'Yahoo']:
                        filtered_products = products[:10]  # Take top 10 results
                        print(f"DEBUG: Using broad matching for {api_name} due to category or laptop search")
                    else:
                        # For JAN code searches, use strict exact matching
                        if is_jan_code:
                            print(f"DEBUG: Filtering {api_name} products by JAN code: {product_info}")
                            # If it's a JAN code search, all returned products should be relevant
                            # Just take them all (up to a reasonable limit) since we used the janCode parameter
                            filtered_products = products[:10]
                            
                            # Add JAN code metadata to each product if not already present
                            for product in filtered_products:
                                if isinstance(product, dict):
                                    # If it's a dictionary
                                    if 'additional_info' not in product:
                                        product['additional_info'] = {}
                                    product['additional_info']['searched_by_jan'] = True
                                    product['additional_info']['jan_code'] = product_info
                                else:
                                    # If it's a ProductDetail object
                                    if not hasattr(product, 'additional_info') or not product.additional_info:
                                        product.additional_info = {}
                                    product.additional_info['searched_by_jan'] = True
                                    product.additional_info['jan_code'] = product_info
                    
                    # Add filtered products to the overall list
                    all_products.extend(filtered_products)
                    
            except Exception as e:
                print(f"Error getting products from {api_name}: {e}")
                
        # Return the combined list of products
        print(f"DEBUG: Total products found across all APIs: {len(all_products)}")
        return all_products

    def get_detailed_products_with_model_numbers(self, model_numbers):
        """
        複数の型番を使用して各サイトから詳細な商品情報を取得
        """
        print(f"DEBUG: Getting detailed products with multiple model numbers: {model_numbers}")
        all_products = []
        
        for model_number in model_numbers:
            try:
                # Get products for this model number
                products = self.get_detailed_products_direct(model_number)
                if products:
                    # Add a field to indicate which model number was used
                    for product in products:
                        product.additional_info['model_number_used'] = model_number
                    all_products.extend(products)
            except Exception as e:
                print(f"Error getting detailed products for model number '{model_number}': {e}")
        
        # 価格で昇順ソート
        sorted_products = sorted(all_products, key=lambda x: x.price if hasattr(x, 'price') else (x.get('price', float('inf')) if isinstance(x, dict) else float('inf')))
        
        return sorted_products

    def _get_multiple_prices(self, api_name, api, product_info):
        """
        各APIから複数の価格情報を取得
        """
        try:
            if hasattr(api, 'get_multiple_prices'):
                results = api.get_multiple_prices(product_info)
                
                # Ensure all results have a 'store' property
                for result in results:
                    # If 'store' is missing but 'shop' is present, copy 'shop' to 'store'
                    if 'store' not in result and 'shop' in result:
                        result['store'] = result['shop']
                    # If neither 'store' nor 'shop' is present, set a default store name based on api_name
                    elif 'store' not in result:
                        if api_name.lower() == 'amazon':
                            result['store'] = 'Amazon.co.jp'
                        elif api_name.lower() == 'rakuten':
                            result['store'] = '楽天市場'
                        elif api_name.lower() == 'yahoo':
                            result['store'] = 'Yahoo!ショッピング'
                        else:
                            result['store'] = api_name
                
                return results
            else:
                # 単一の価格情報しか返さないAPIの場合
                price_info = api.get_price(product_info)
                if price_info:
                    price_info['source'] = api_name
                    
                    # Ensure the price_info has a 'store' property
                    if 'store' not in price_info and 'shop' in price_info:
                        price_info['store'] = price_info['shop']
                    elif 'store' not in price_info:
                        if api_name.lower() == 'amazon':
                            price_info['store'] = 'Amazon.co.jp'
                        elif api_name.lower() == 'rakuten':
                            price_info['store'] = '楽天市場'
                        elif api_name.lower() == 'yahoo':
                            price_info['store'] = 'Yahoo!ショッピング'
                        else:
                            price_info['store'] = api_name
                    
                    return [price_info]
                return []
        except Exception as e:
            print(f"Error in {api_name} API call: {e}")
            return []

    def _get_multiple_prices_direct(self, api_name, api, product_info):
        """
        各APIから複数の価格情報を取得 (直接検索モード)
        """
        try:
            # Enhanced list of common product categories with Japanese and English variations
            common_categories = {
                "tv": "2502",
                "テレビ": "2502", 
                "television": "2502",
                "pc": "2505",
                "パソコン": "2505",
                "computer": "2505",
                "laptop": "2505",
                "ノートパソコン": "2505",
                "camera": "2511",
                "カメラ": "2511",
                "smartphone": "2514",
                "スマートフォン": "2514",
                "スマホ": "2514",
                "phone": "2514",
                "携帯電話": "2514",
                "冷蔵庫": "2437",
                "家電": "2430",
                "オーディオ": "2516"
            }
            
            is_common_category = False
            category_id = None
            
            # Check if it's a common category
            query_lower = product_info.lower()
            for category, id_value in common_categories.items():
                if query_lower == category or query_lower.startswith(category + " "):
                    is_common_category = True
                    category_id = id_value
                    break

            # Check if this looks like a model number (alphanumeric with optional dashes)
            is_model_number = bool(re.match(r'^[A-Za-z0-9]+-?[A-Za-z0-9]+$', str(product_info)))
            
            if hasattr(api, 'get_multiple_prices'):
                # Special handling for common categories on Rakuten and Yahoo
                if is_common_category and api_name in ['Rakuten', 'Yahoo'] and hasattr(api, 'get_category_prices') and category_id:
                    print(f"DEBUG: Using category price search for {api_name} with category ID {category_id}")
                    results = api.get_category_prices(product_info, category_id)
                else:
                    results = api.get_multiple_prices(product_info)
                
                # Filter results based on whether it's a common category, model number, or product name
                filtered_results = []
                
                # For common categories on Rakuten/Yahoo, accept all results
                if is_common_category and api_name in ['Rakuten', 'Yahoo']:
                    # Just ensure all items have store property
                    for result in results[:10]:  # Take top 10 results
                        if 'store' not in result and 'shop' in result:
                            result['store'] = result['shop']
                        elif 'store' not in result:
                            result['store'] = f"{api_name} ショップ"
                        filtered_results.append(result)
                else:
                    # For other searches, use more sophisticated filtering
                    for result in results:
                        # For model numbers, require exact match in title
                        # For product names or common categories, use more relaxed matching
                        title = result.get('title', '').lower()
                        query = product_info.lower()
                        
                        # Different matching logic based on type of search
                        if (is_common_category or                          # Common category
                            not is_model_number or                         # Not a model number (likely a product name)
                            (is_model_number and query in title) or        # Model number found in title
                            any(word in title for word in query.split())):  # Any word in query found in title
                            
                            # Ensure the result has a 'store' property
                            if 'store' not in result and 'shop' in result:
                                result['store'] = result['shop']
                            elif 'store' not in result:
                                if api_name.lower() == 'amazon':
                                    result['store'] = 'Amazon.co.jp'
                                elif api_name.lower() == 'rakuten':
                                    result['store'] = '楽天市場'
                                elif api_name.lower() == 'yahoo':
                                    result['store'] = 'Yahoo!ショッピング'
                                else:
                                    result['store'] = api_name
                            
                            filtered_results.append(result)
                
                # For non-model number searches on Rakuten and Yahoo, relax filtering if no results
                if not is_model_number and len(filtered_results) == 0 and api_name in ['Rakuten', 'Yahoo']:
                    # Return all results without strict filtering for product name searches
                    for result in results[:10]:  # Increased from 5 to 10
                        # Ensure the result has a 'store' property
                        if 'store' not in result and 'shop' in result:
                            result['store'] = result['shop']
                        elif 'store' not in result:
                            result['store'] = f"{api_name} ショップ"
                        filtered_results.append(result)
                
                return filtered_results
            else:
                # 単一の価格情報しか返さないAPIの場合
                price_info = api.get_price(product_info)
                # Check if this looks like a model number (alphanumeric with optional dashes)
                is_model_number = bool(re.match(r'^[A-Za-z0-9]+-?[A-Za-z0-9]+$', str(product_info)))
                
                # For non-model numbers or common categories, don't filter by title match
                if price_info and (is_common_category or not is_model_number or product_info.lower() in price_info.get('title', '').lower()):
                    price_info['source'] = api_name
                    
                    # Ensure the price_info has a 'store' property
                    if 'store' not in price_info and 'shop' in price_info:
                        price_info['store'] = price_info['shop']
                    elif 'store' not in price_info:
                        if api_name.lower() == 'amazon':
                            price_info['store'] = 'Amazon.co.jp'
                        elif api_name.lower() == 'rakuten':
                            price_info['store'] = '楽天市場'
                        elif api_name.lower() == 'yahoo':
                            price_info['store'] = 'Yahoo!ショッピング'
                        else:
                            price_info['store'] = api_name
                    
                    return [price_info]
                return []
        except Exception as e:
            print(f"Error in {api_name} API call (direct search): {e}")
            return []

    def sort_and_filter_results(self, results):
        """
        結果を価格順にソートしてフィルタリング
        """
        if not results:
            return []
            
        # Ensure all results have a 'store' property
        for result in results:
            # If 'store' is missing but 'shop' is present, copy 'shop' to 'store'
            if 'store' not in result and 'shop' in result:
                result['store'] = result['shop']
            # If neither 'store' nor 'shop' is present, set a default store name based on 'source'
            elif 'store' not in result:
                if 'source' in result:
                    if result['source'].lower() == 'amazon':
                        result['store'] = 'Amazon.co.jp'
                    elif result['source'].lower() == 'rakuten':
                        result['store'] = '楽天市場'
                    elif result['source'].lower() == 'yahoo':
                        result['store'] = 'Yahoo!ショッピング'
                    else:
                        result['store'] = result['source']
                else:
                    result['store'] = '不明なショップ'
            
        # 価格で昇順ソート
        sorted_results = sorted(results, key=lambda x: x['price'])
        
        # 最安値との価格差が閾値以内の商品のみを抽出
        min_price = sorted_results[0]['price']
        filtered_results = [
            result for result in sorted_results
            if result['price'] <= min_price * (1 + PRICE_THRESHOLD)
        ]
        
        return filtered_results 
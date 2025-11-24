from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
# type: ignore
from werkzeug.utils import secure_filename
from src.search.similar_products import ProductSearchEngine
from src.search.image_search import ImageSearchEngine
from src.comparison.price_compare import PriceComparisonEngine
from dotenv import load_dotenv
import re
from datetime import datetime
from src.api.amazon_api import amazon_api, AmazonAPI
from src.api.rakuten_api import rakuten_api
from src.api.yahoo_api import yahoo_api
from src.tools.batch_keyword_generator import BatchKeywordGenerator
from src.api.perplexity_client import perplexity_client
from src.services.listing_manager import ListingManager
from src.services.stock_monitor import StockMonitor
from src.services.profit_calculator import ProfitCalculator
from src.services.shipping_calculator import ShippingCalculator
from src.api.us_amazon_api import us_amazon_api
import uuid
import time

app = Flask(__name__)
# Configure CORS properly with specific settings
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000", 
                                "allow_headers": ["Content-Type", "Authorization"],
                                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                                "supports_credentials": True}})

# Add an explicit route handler for OPTIONS requests
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return '', 200

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Allowed file extensions
ALLOWED_EXTENSIONS = {'txt', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize search engines and API clients
product_search = ProductSearchEngine()
image_search = ImageSearchEngine()
price_comparison = PriceComparisonEngine()

# Initialize listing management services
listing_manager = ListingManager()
profit_calculator = ProfitCalculator()
shipping_calculator = ShippingCalculator()
stock_monitor = StockMonitor(listing_manager)
stock_monitor.start_monitoring()  # Start automatic monitoring

# Load environment variables
load_dotenv()

# Amazon PA-API configuration
amazon_partner_tag = os.getenv('AMAZON_PARTNER_TAG')
amazon_access_key = os.getenv('AMAZON_ACCESS_KEY')
amazon_secret_key = os.getenv('AMAZON_SECRET_KEY')
amazon_host = "webservices.amazon.co.jp"
amazon_region = "ap-northeast-1"

# Initialize the BatchKeywordGenerator
batch_keyword_generator = BatchKeywordGenerator()

# Add a dictionary to track batch search statuses
batch_search_status = {}

def select_cheapest_highest_ranked_products(products, max_products=10):
    """
    価格とランキングに基づいて最適な商品を選択
    """
    if not products:
        return []
        
    # Sort by price (ascending) and then by ranking (descending) if available
    sorted_products = sorted(
        products,
        key=lambda p: (
            float('inf') if not p.get('price') or p.get('price') == 0 else p.get('price'),
            -1 * (p.get('ranking', 0) or 0)  # Higher ranking is better
        )
    )
    
    # Return the top N products
    return sorted_products[:max_products]

def search_amazon_products(keywords, limit=5):
    """
    Amazon Product Advertising API を使用して商品を検索
    """
    try:
        # Use the AmazonAPI class to search for products
        return amazon_api._search_amazon_products(keywords, limit)
    except Exception as e:
        print(f"Error in Amazon search: {e}")
        return []

def search_rakuten(keywords, limit=5):
    """
    Rakuten商品情報を検索（API優先）
    """
    # Use the Rakuten API to get product information
    return rakuten_api.search_products(keywords, limit)

def _get_rakuten_fallback(keywords, limit=5):
    """
    楽天APIが失敗した場合のフォールバック価格情報
    """
    # Use the fallback method from the Rakuten API
    return rakuten_api._get_fallback_prices(keywords, limit)

def get_item_value(result, key, default_value):
    """
    Helper function to get a value from a Rakuten API result item
    """
    # Check if 'Item' key exists in the response
    if 'Item' in result:
        return result['Item'].get(key, default_value)
    return result.get(key, default_value)

def get_item_image_url(result):
    """
    Helper function to get the image URL from a Rakuten API result item
    """
    item = result
    if 'Item' in result:
        item = result['Item']
    
    # Try to get medium image URL
    if 'mediumImageUrls' in item and len(item['mediumImageUrls']) > 0:
        first_image = item['mediumImageUrls'][0]
        if isinstance(first_image, dict) and 'imageUrl' in first_image:
            image_url = first_image['imageUrl']
            if image_url:
                # Ensure the URL uses HTTPS
                if image_url.startswith('http:'):
                    image_url = image_url.replace('http:', 'https:')
                
                # Add size parameter for better quality if using thumbnail.image.rakuten.co.jp
                if 'thumbnail.image.rakuten.co.jp' in image_url and not '_ex=' in image_url:
                    image_url = f"{image_url}{'&' if '?' in image_url else '?'}_ex=300x300"
                
                return image_url
    
    # Try to get small image URL
    if 'smallImageUrls' in item and len(item['smallImageUrls']) > 0:
        first_image = item['smallImageUrls'][0]
        if isinstance(first_image, dict) and 'imageUrl' in first_image:
            image_url = first_image['imageUrl']
            if image_url:
                # Ensure the URL uses HTTPS
                if image_url.startswith('http:'):
                    image_url = image_url.replace('http:', 'https:')
                
                # Add size parameter for better quality if using thumbnail.image.rakuten.co.jp
                if 'thumbnail.image.rakuten.co.jp' in image_url and not '_ex=' in image_url:
                    image_url = f"{image_url}{'&' if '?' in image_url else '?'}_ex=300x300"
                
                return image_url
    
    # Default Rakuten logo
    return "https://thumbnail.image.rakuten.co.jp/@0_mall/rakuten/cabinet/ichiba/app/pc/img/common/logo_rakuten_320x320.png"

def search_yahoo(keywords, limit=5):
    """
    Yahoo!ショッピングから商品情報を検索
    """
    try:
        return yahoo_api.get_product_details(keywords)
    except Exception as e:
        print(f"Error in Yahoo search: {e}")
        return []

@app.route('/api/search', methods=['POST'])
def search():
    """商品検索API"""
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({"error": "Search query is required"}), 400
    
    try:
        # キーワード生成
        keywords = product_search.generate_search_keywords(query)
        
        # 価格比較
        price_results = price_comparison.compare_prices(query)
        
        # 詳細な商品情報を取得
        detailed_products = price_comparison.get_detailed_products(query)
        
        # ProductDetailオブジェクトを辞書に変換
        serializable_detailed_products = []
        for product in detailed_products:
            if hasattr(product, 'to_dict'):
                # Use the to_dict method if available
                product_dict = product.to_dict()
                
                # Ensure price is an integer
                if 'price' in product_dict:
                    try:
                        if product_dict['price'] is None:
                            product_dict['price'] = 0
                        elif isinstance(product_dict['price'], str):
                            # Remove currency symbols and commas
                            price_str = product_dict['price'].replace('¥', '').replace(',', '').strip()
                            # Extract only digits
                            price_digits = ''.join(filter(str.isdigit, price_str))
                            if price_digits:
                                product_dict['price'] = int(price_digits)
                            else:
                                product_dict['price'] = 0
                        else:
                            # Ensure it's an integer
                            product_dict['price'] = int(product_dict['price'])
                    except Exception as e:
                        print(f"Error converting price to integer: {e}")
                        product_dict['price'] = 0
                
                serializable_detailed_products.append(product_dict)
            else:
                # すでに辞書の場合はそのまま追加
                if isinstance(product, dict) and 'price' in product:
                    try:
                        if product['price'] is None:
                            product['price'] = 0
                        elif isinstance(product['price'], str):
                            # Remove currency symbols and commas
                            price_str = product['price'].replace('¥', '').replace(',', '').strip()
                            # Extract only digits
                            price_digits = ''.join(filter(str.isdigit, price_str))
                            if price_digits:
                                product['price'] = int(price_digits)
                            else:
                                product['price'] = 0
                        else:
                            # Ensure it's an integer
                            product['price'] = int(product['price'])
                    except Exception as e:
                        print(f"Error converting price to integer: {e}")
                        product['price'] = 0
                
                serializable_detailed_products.append(product)
        
        # ランキングと価格に基づいて最適な商品を選択
        selected_products = select_cheapest_highest_ranked_products(serializable_detailed_products)
        
        # 結果を返す
        return jsonify({
            'query': query,
            'keywords': keywords,
            'price_results': price_results,
            'detailed_products': selected_products,
        })
        
    except Exception as e:
        print(f"Error in search: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search/batch', methods=['POST'])
def batch_search():
    """
    複数の商品情報を一括で検索
    """
    try:
        # テキスト入力からの一括検索
        if 'product_info_list' in request.json:
            product_info_list = request.json['product_info_list']
            direct_search = request.json.get('direct_search', False)  # Add direct search parameter
            
            if not product_info_list or not isinstance(product_info_list, list):
                return jsonify({'error': 'Invalid product info list'}), 400
                
            # 商品情報リストが大きすぎる場合はエラー
            if len(product_info_list) > 5:
                return jsonify({'error': 'Too many items. Maximum 5 items allowed.'}), 400
                
            # キーワード生成 (Skip AI enhancement if direct_search is True)
            if direct_search:
                results = []
                for product_info in product_info_list:
                    # For direct search, first find model numbers related to the keyword
                    model_numbers = product_search.find_model_numbers(product_info)
                    results.append({
                        'product_info': product_info,
                        'keywords': model_numbers,  # Use the model numbers as keywords
                        'error': None
                    })
                print(f"Direct batch search with model numbers for {len(product_info_list)} keywords")
            else:
                try:
                    results = product_search.batch_generate_keywords(product_info_list)
                except Exception as e:
                    print(f"Error in batch keyword generation: {e}")
                    # Fallback: use original terms as keywords
                    results = []
                    for product_info in product_info_list:
                        results.append({
                            'product_info': product_info,
                            'keywords': [product_info],
                            'error': None
                        })
            
            return jsonify(results)
            
        # ファイルアップロードからの一括検索
        elif 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
                
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # ファイルから商品情報を読み込む
                product_info_list = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:  # 空行をスキップ
                            product_info_list.append(line)
                
                # 商品情報リストが大きすぎる場合はエラー
                if len(product_info_list) > 1000:
                    return jsonify({'error': 'Too many items in file. Maximum 1000 items allowed.'}), 400
                
                # キーワード生成
                results = product_search.batch_generate_keywords(product_info_list)
                
                return jsonify(results)
            else:
                return jsonify({'error': 'File type not allowed. Please upload a .txt or .csv file'}), 400
        else:
            return jsonify({'error': 'No product info or file provided'}), 400
            
    except Exception as e:
        print(f"Error in batch search: {e}")

@app.route('/api/search/image', methods=['POST'])
def search_by_image():
    """
    画像から類似商品を検索
    """
    try:
        # 画像ファイルのアップロード
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename == '':
                return jsonify({'error': 'No image selected'}), 400
                
            try:
                # 画像を保存
                filename = secure_filename(image_file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image_file.save(file_path)
                
                # 画像データを読み込み
                with open(file_path, 'rb') as f:
                    image_data = f.read()
                
                # 画像からモデル番号を抽出
                try:
                    # 画像ファイル名からモデル番号を抽出する試み
                    import re
                    model_patterns = [
                        r'[A-Z0-9]{2,}-[A-Z0-9]{2,}',  # ABC-123 形式
                        r'[A-Z]{2,}[0-9]{2,}',         # ABC123 形式
                        r'[0-9]{2,}-[A-Z0-9]{2,}'      # 12-ABC 形式
                    ]
                    
                    input_model = None
                    for pattern in model_patterns:
                        matches = re.findall(pattern, filename)
                        if matches:
                            input_model = matches[0]
                            print(f"Extracted model number from filename: {input_model}")
                            break
                    
                    # モデル番号を抽出（入力されたモデル番号を優先）
                    model_numbers = []
                    try:
                        model_numbers = image_search.extract_model_numbers(image_data=image_data)
                        print(f"Extracted model numbers: {model_numbers}")
                    except Exception as e:
                        print(f"Error extracting model numbers from image: {e}")
                        # Continue with empty model numbers
                except Exception as e:
                    print(f"Error extracting model numbers: {e}")
                    model_numbers = []
                
                # モデル番号が見つからない場合は画像の内容を分析
                generic_term = None
                if not model_numbers:
                    try:
                        generic_term = image_search.analyze_image_content(image_data=image_data)
                        print(f"Analyzed image content: {generic_term}")
                    except Exception as e:
                        print(f"Error analyzing image content: {e}")
                        # Use a more useful default term instead of "ロープ"
                        generic_term = "スマートフォン"  # Default to "smartphone" which is likely to yield results
                
                # モデル番号が見つかった場合、それを使って検索
                if model_numbers:
                    # 最も信頼度の高いモデル番号を使用
                    best_model = model_numbers[0]['model_number']
                    print(f"Using model number for search: {best_model}")
                    
                    # 最も信頼度の高いモデル番号のみを使用
                    filtered_model_numbers = [model_numbers[0]]
                    
                    try:
                        # モデル番号で検索
                        search_results = product_search.search(best_model)
                        
                        # 結果を返す
                        return jsonify({
                            'query_image': f"/api/uploads/{filename}",
                            'model_numbers': filtered_model_numbers,
                            'generic_term': generic_term,  # Add generic term to the response
                            'similar_products': [],
                            'price_comparison': search_results.get('price_comparison', []),
                            'detailed_products': search_results.get('detailed_products', [])
                        })
                    except Exception as e:
                        print(f"Error searching with model number: {e}")
                        # Fall back to generic term search if model number search fails
                        generic_term = generic_term or "商品"
                
                # モデル番号が見つからないが、画像の内容が識別できた場合
                if generic_term:
                    print(f"No model number found or model number search failed. Using generic term for search: {generic_term}")
                    
                    # 単一検索を使用して商品を検索
                    search_results = product_search.search(generic_term)
                    
                    # 結果を返す
                    return jsonify({
                        'query_image': f"/api/uploads/{filename}",
                        'model_numbers': model_numbers,
                        'generic_term': generic_term,
                                'similar_products': [],
                        'price_comparison': search_results.get('price_comparison', []),
                        'detailed_products': search_results.get('detailed_products', [])
                    })
                
                # 何も見つからなかった場合
                    return jsonify({
                        'query_image': f"/api/uploads/{filename}",
                        'model_numbers': [],
                    'generic_term': "商品",
                        'similar_products': [],
                        'price_comparison': [],
                    'detailed_products': [],
                    'error': 'No model number or recognizable content found'
                    })
                
            except Exception as e:
                print(f"Error processing image file: {e}")
                return jsonify({'error': f'Error processing image file: {str(e)}'}), 500
            
        # 画像URLからの検索
        elif 'image_url' in request.json:
            image_url = request.json['image_url']
            if not image_url:
                return jsonify({'error': 'Invalid image URL'}), 400
                
            try:
                # 画像URLからモデル番号を抽出
                model_numbers = []
                try:
                    model_numbers = image_search.extract_model_numbers(image_url=image_url)
                    print(f"Extracted model numbers from URL: {model_numbers}")
                except Exception as e:
                    print(f"Error extracting model numbers from URL: {e}")
                    # Continue with empty model numbers
                
                # モデル番号が見つからない場合は画像の内容を分析
                generic_term = None
                if not model_numbers:
                    try:
                        generic_term = image_search.analyze_image_content(image_url=image_url)
                        print(f"Analyzed image content from URL: {generic_term}")
                    except Exception as e:
                        print(f"Error analyzing image content from URL: {e}")
                        # Use a more useful default term
                        generic_term = "スマートフォン"
                
                # モデル番号が見つかった場合、それを使って検索
                if model_numbers:
                    # 最も信頼度の高いモデル番号を使用
                    best_model = model_numbers[0]['model_number']
                    print(f"Using model number for search: {best_model}")
                    
                    # 最も信頼度の高いモデル番号のみを使用
                    filtered_model_numbers = [model_numbers[0]]
                    
                    try:
                        # モデル番号で検索
                        search_results = product_search.search(best_model)
                        
                        # 結果を返す
                        return jsonify({
                            'query_image': image_url,
                            'model_numbers': filtered_model_numbers,
                            'generic_term': generic_term,  # Add generic term to the response
                            'similar_products': [],
                            'price_comparison': search_results.get('price_comparison', []),
                            'detailed_products': search_results.get('detailed_products', [])
                        })
                    except Exception as e:
                        print(f"Error searching with model number from URL: {e}")
                        # Fall back to generic term search if model number search fails
                        generic_term = generic_term or "商品"
                
                # モデル番号が見つからないが、画像の内容が識別できた場合
                if generic_term:
                    print(f"No model number found or model number search failed. Using generic term for search from URL: {generic_term}")
                    
                    # 単一検索を使用して商品を検索
                    search_results = product_search.search(generic_term)
                    
                    # 結果を返す
                    return jsonify({
                        'query_image': image_url,
                        'model_numbers': model_numbers,
                        'generic_term': generic_term,
                        'similar_products': [],
                        'price_comparison': search_results.get('price_comparison', []),
                        'detailed_products': search_results.get('detailed_products', [])
                    })
                
                # 何も見つからなかった場合
                    return jsonify({
                        'query_image': image_url,
                        'model_numbers': [],
                    'generic_term': "商品",
                        'similar_products': [],
                        'price_comparison': [],
                        'detailed_products': [],
                    'error': 'No model number or recognizable content found'
                    })
                
            except Exception as e:
                print(f"Error processing image URL: {e}")
                return jsonify({'error': f'Error processing image URL: {str(e)}'}), 500
            
        else:
            return jsonify({'error': 'No image or image URL provided'}), 400
            
    except Exception as e:
        print(f"Error in image search: {e}")
        return jsonify({'error': str(e)}), 500

# Add a fallback route for image search without the /api prefix
@app.route('/search/image', methods=['POST'])
def search_by_image_fallback():
    """
    画像から類似商品を検索 (フォールバックエンドポイント)
    """
    return search_by_image()

@app.route('/api/compare', methods=['POST'])
def compare_products():
    """商品比較API"""
    data = request.json
    product_a = data.get('product_a')
    product_b = data.get('product_b')
    
    if not product_a or not product_b:
        return jsonify({"error": "Both products are required for comparison"}), 400
    
    # Helper function to safely get attribute from either dict or object
    def get_attr(obj, attr, default=None):
        if isinstance(obj, dict):
            return obj.get(attr, default)
        else:
            return getattr(obj, attr, default)
    
    # Helper function to clean HTML tags from text
    def clean_html(html_text):
        """Remove HTML tags from text"""
        if not html_text:
            return ""
            
        import re
        # Replace <br>, <br/>, <br /> with newlines
        text = re.sub(r'<br\s*/?>', '\n', html_text, flags=re.IGNORECASE)
        
        # Remove all other HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Replace multiple newlines with a single newline
        text = re.sub(r'\n+', '\n', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    try:
        # 各商品の詳細情報を取得
        products_a = price_comparison.get_detailed_products(product_a)
        products_b = price_comparison.get_detailed_products(product_b)
        
        # Check if we found any products
        if not products_a:
            return jsonify({"error": f"Could not find information for product: {product_a}"}), 404
        
        if not products_b:
            return jsonify({"error": f"Could not find information for product: {product_b}"}), 404
        
        # 最初の商品を使用
        product_a_info = products_a[0]
        product_b_info = products_b[0]
        
        # Validate that both products have the necessary data
        price_a = get_attr(product_a_info, 'price')
        price_b = get_attr(product_b_info, 'price')
        
        if price_a is None:
            return jsonify({"error": f"Price information not available for product: {product_a}"}), 400
            
        if price_b is None:
            return jsonify({"error": f"Price information not available for product: {product_b}"}), 400
        
        # 違いを分析（実際のアプリケーションではより詳細な分析が必要）
        differences = []
        
        # 価格の違い
        try:
            price_diff = abs(price_a - price_b)
            price_percentage = price_diff / max(price_a, price_b) * 100 if max(price_a, price_b) > 0 else 0
            
            differences.append({
                'category': '価格',
                'product_a_value': f"{price_a}円",
                'product_b_value': f"{price_b}円",
                'significance': 'high' if price_percentage > 20 else 'medium' if price_percentage > 5 else 'low'
            })
        except (TypeError, ZeroDivisionError) as e:
            print(f"Error calculating price difference: {e}")
            # Add a placeholder for price difference
            differences.append({
                'category': '価格',
                'product_a_value': f"{price_a or '不明'}円",
                'product_b_value': f"{price_b or '不明'}円",
                'significance': 'medium'
            })
        
        # 送料の違い
        try:
            shipping_fee_a = get_attr(product_a_info, 'shipping_fee', 0)
            shipping_fee_b = get_attr(product_b_info, 'shipping_fee', 0)
            
            if shipping_fee_a is not None and shipping_fee_b is not None:
                shipping_diff = abs((shipping_fee_a or 0) - (shipping_fee_b or 0))
                differences.append({
                    'category': '送料',
                    'product_a_value': f"{shipping_fee_a or 0}円",
                    'product_b_value': f"{shipping_fee_b or 0}円",
                    'significance': 'high' if shipping_diff > 500 else 'medium' if shipping_diff > 100 else 'low'
                })
        except Exception as e:
            print(f"Error calculating shipping difference: {e}")
        
        # 評価の違い
        try:
            rating_a = get_attr(product_a_info, 'rating')
            rating_b = get_attr(product_b_info, 'rating')
            
            if rating_a is not None and rating_b is not None:
                rating_diff = abs((rating_a or 0) - (rating_b or 0))
                differences.append({
                    'category': '評価',
                    'product_a_value': f"{rating_a or 0}点",
                    'product_b_value': f"{rating_b or 0}点",
                    'significance': 'high' if rating_diff > 1.5 else 'medium' if rating_diff > 0.5 else 'low'
                })
        except Exception as e:
            print(f"Error calculating rating difference: {e}")
        
        # 耐荷重の違い (Extract from description or additional_info)
        try:
            # Try to find load capacity information in the product data
            load_capacity_a = "不明"
            load_capacity_b = "不明"
            
            # Check in additional_info
            additional_info_a = get_attr(product_a_info, 'additional_info', {})
            if additional_info_a:
                for key, value in additional_info_a.items():
                    if '荷重' in key or '耐荷重' in key or '最大荷重' in key:
                        load_capacity_a = str(value)
                        break
            
            additional_info_b = get_attr(product_b_info, 'additional_info', {})
            if additional_info_b:
                for key, value in additional_info_b.items():
                    if '荷重' in key or '耐荷重' in key or '最大荷重' in key:
                        load_capacity_b = str(value)
                        break
            
            # Check in description
            description_a = get_attr(product_a_info, 'description', '')
            if load_capacity_a == "不明" and description_a:
                import re
                load_capacity_match = re.search(r'耐荷重[：:]\s*(\d+[kgkg]*)', description_a)
                if load_capacity_match:
                    load_capacity_a = load_capacity_match.group(1)
            
            description_b = get_attr(product_b_info, 'description', '')
            if load_capacity_b == "不明" and description_b:
                import re
                load_capacity_match = re.search(r'耐荷重[：:]\s*(\d+[kgkg]*)', description_b)
                if load_capacity_match:
                    load_capacity_b = load_capacity_match.group(1)
            
            # Add to differences if at least one product has load capacity info
            if load_capacity_a != "不明" or load_capacity_b != "不明":
                differences.append({
                    'category': '耐荷重',
                    'product_a_value': load_capacity_a,
                    'product_b_value': load_capacity_b,
                    'significance': 'high'  # Load capacity is usually important
                })
        except Exception as e:
            print(f"Error extracting load capacity: {e}")
        
        # 特徴の違い (Extract from features or description)
        try:
            # Try to find features information in the product data
            features_a = "不明"
            features_b = "不明"
            
            # Check in features field
            product_features_a = get_attr(product_a_info, 'features', [])
            if product_features_a:
                if isinstance(product_features_a, list):
                    features_a = ", ".join(product_features_a[:3])  # Take first 3 features
                else:
                    features_a = str(product_features_a)
            
            product_features_b = get_attr(product_b_info, 'features', [])
            if product_features_b:
                if isinstance(product_features_b, list):
                    features_b = ", ".join(product_features_b[:3])  # Take first 3 features
                else:
                    features_b = str(product_features_b)
            
            # If no features, extract from description
            if features_a == "不明" and description_a:
                # Use the full description instead of truncating
                features_a = clean_html(description_a)
            
            if features_b == "不明" and description_b:
                # Use the full description instead of truncating
                features_b = clean_html(description_b)
            
            # Add to differences if at least one product has features info
            if features_a != "不明" or features_b != "不明":
                differences.append({
                    'category': '特徴',
                    'product_a_value': features_a,
                    'product_b_value': features_b,
                    'significance': 'medium'
                })
        except Exception as e:
            print(f"Error extracting features: {e}")
        
        # 推奨
        recommendation = ""
        
        # 価格差が大きい場合は安い方を推奨
        try:
            if price_percentage > 20:
                cheaper_product = "商品A" if price_a < price_b else "商品B"
                recommendation = f"{cheaper_product}の方が{price_percentage:.1f}%安いため、コストパフォーマンスが良いでしょう。"
            # 価格差が小さい場合は評価が高い方を推奨
            elif rating_a is not None and rating_b is not None and abs(rating_a - rating_b) > 0.5:
                better_rated = "商品A" if rating_a > rating_b else "商品B"
                recommendation = f"{better_rated}の方が評価が高いため、品質が良い可能性があります。"
            # それ以外の場合は特徴に基づいて推奨
            else:
                # 特徴に基づく推奨ロジックを実装
                recommendation = "両商品は価格と評価が似ていますが、詳細な特徴を比較して選択することをお勧めします。"
        except Exception as e:
            print(f"Error generating recommendation: {e}")
            recommendation = "商品の詳細を比較して、ご自身のニーズに合った方を選択してください。"
        
        # 商品情報を辞書に変換
        def product_to_dict(product):
            if isinstance(product, dict):
                return product
            elif hasattr(product, 'to_dict') and callable(getattr(product, 'to_dict')):
                return product.to_dict()
            else:
                # If it's another type of object with __dict__
                if hasattr(product, '__dict__'):
                    product_dict = product.__dict__
                else:
                    # Last resort: try to convert to a dictionary or create an empty one
                    try:
                        product_dict = dict(product)
                    except:
                        print(f"Warning: Could not convert {type(product)} to dictionary. Using empty dict.")
                        product_dict = {}
            return product_dict
        
        # 結果を返す
        result = {
            'product_a': product_to_dict(product_a_info),
            'product_b': product_to_dict(product_b_info),
            'differences': differences,
            'recommendation': recommendation
        }
        
        return jsonify(result)
    except Exception as e:
        print(f"Error comparing products: {e}")
        return jsonify({"error": f"Error comparing products: {str(e)}"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェックAPI"""
    return jsonify({"status": "ok"})

@app.route('/api/uploads/<filename>')
def uploaded_file(filename):
    """
    アップロードされたファイルを提供
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Fallback route for /uploads/ without /api prefix
@app.route('/uploads/<filename>')
def uploaded_file_fallback(filename):
    """Fallback route for uploaded files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/search/enhance-keywords', methods=['POST'])
def enhance_keywords():
    """
    AIを使用して検索キーワードを最適化するエンドポイント
    """
    try:
        data = request.get_json()
        product_info_list = data.get('product_info_list', [])
        custom_prompt = data.get('custom_prompt', None)  # Get custom prompt if provided
        
        if not product_info_list:
            return jsonify({'error': '商品情報が提供されていません'}), 400
            
        # Use the BatchKeywordGenerator to generate keywords
        results = batch_keyword_generator.batch_generate(product_info_list, custom_prompt)
        
        # Extract just the keywords for the response
        enhanced_keywords = [item['keyword'] for item in results]
            
        # 結果を返す
        return jsonify({
            'keywords': enhanced_keywords
        })
        
    except Exception as e:
        print(f"Error in enhance_keywords: {e}")
        return jsonify({'error': str(e)}), 500

def generate_ai_keywords(model_number, custom_prompt=None):
    """
    AIを使用して型番から最適な検索キーワードを生成
    """
    try:
        # Use the BatchKeywordGenerator to generate a single keyword
        result = batch_keyword_generator.generate_keyword(model_number, custom_prompt)
        return result
    except Exception as e:
        print(f"Error in AI keyword generation: {e}")
        # Clean up the model number as a fallback
        cleaned_model = re.sub(r'^\d+\s+', '', model_number.strip())
        return cleaned_model  # Fallback to using the model number directly

@app.route('/api/search/status/<batch_id>', methods=['GET'])
def check_batch_status(batch_id):
    """
    バッチ検索のステータスを確認するエンドポイント
    """
    if batch_id not in batch_search_status:
        return jsonify({'error': 'Batch ID not found'}), 404
        
    return jsonify(batch_search_status[batch_id])

@app.route('/api/search/detailed-batch', methods=['POST'])
def detailed_batch_search():
    """
    複数の商品情報を一括で詳細検索
    """
    try:
        data = request.json
        product_info_list = data.get('product_info_list', [])
        use_ai = data.get('use_ai', False)
        # Always use direct search
        direct_search = True
        # Add JAN code support
        use_jan_code = data.get('use_jan_code', True)  # Default to True like in single search
        
        if not product_info_list or not isinstance(product_info_list, list):
            return jsonify({'error': 'Invalid product info list'}), 400
            
        # 商品情報リストが大きすぎる場合はエラー
        if len(product_info_list) > 500:
            return jsonify({'error': 'Too many items. Maximum 500 items allowed.'}), 400
        
        # Generate a unique batch ID for status tracking
        batch_id = str(uuid.uuid4())
        batch_search_status[batch_id] = {
            'total': len(product_info_list),
            'processed': 0,
            'completed': False,
            'has_errors': False,
            'start_time': time.time(),
            'results': []
        }
        
        results = []
        
        # Process items in chunks of 20 for better performance
        chunk_size = 20
        for i in range(0, len(product_info_list), chunk_size):
            chunk = product_info_list[i:i+chunk_size]
            print(f"Processing chunk {(i//chunk_size)+1}/{(len(product_info_list)+chunk_size-1)//chunk_size} ({len(chunk)} items)")
            
            for product_info in chunk:
                try:
                    # For direct search, use the exact model number provided by the user
                    keywords = [product_info]  # Use the exact input as the only keyword
                    jan_code = None
                    
                    # Check if it looks like a model number
                    is_model_number = bool(re.match(r'^[A-Za-z0-9]+-?[A-Za-z0-9]+', str(product_info)))
                    
                    # Check if it's already a JAN code (8 or 13 digits)
                    is_jan_code = bool(re.match(r'^[0-9]{8}$|^[0-9]{13}$', str(product_info)))
                    
                    # If it's already a JAN code, use it directly
                    if is_jan_code:
                        print(f"Input is already a JAN code: {product_info}")
                        jan_code = product_info
                        keywords = [jan_code]
                        
                        # Get detailed product information using JAN code
                        detailed_products = price_comparison.get_detailed_products_direct(jan_code)
                        
                    # If it's a model number and JAN code lookup is enabled, try to get a JAN code
                    elif is_model_number and use_jan_code:
                        jan_code = perplexity_client.get_jan_code(product_info)
                        if jan_code:
                            # If JAN code is found, it becomes the ONLY search term
                            print(f"Found JAN code for {product_info}: {jan_code}")
                            # Use only the JAN code for search to ensure consistency across platforms
                            keywords = [jan_code]
                            
                            # Get detailed product information using JAN code
                            detailed_products = price_comparison.get_detailed_products_direct(jan_code)
                            
                            # If no products found with JAN code, fall back to model number
                            if not detailed_products or len(detailed_products) == 0:
                                print(f"No products found with JAN code, falling back to model number")
                                detailed_products = price_comparison.get_detailed_products_direct(product_info)
                        else:
                            # No JAN code found, use the model number
                            print(f"No JAN code found for {product_info}, using model number directly")
                            detailed_products = price_comparison.get_detailed_products_direct(product_info)
                    else:
                        # Not a model number or JAN code lookup disabled, use normal search
                        print(f"Using normal search for {product_info} (not a model number or JAN lookup disabled)")
                        detailed_products = price_comparison.get_detailed_products_direct(product_info)
                    
                    # 価格比較
                    price_results = []
                    try:
                        # For price comparison, use the same keywords as for product search
                        price_results = price_comparison.compare_prices_with_model_numbers(keywords)
                    except Exception as e:
                        print(f"Error in price comparison for '{product_info}': {e}")
                        batch_search_status[batch_id]['has_errors'] = True
                    
                    # Convert product objects to dictionaries with JAN code metadata
                    serializable_products = []
                    for product in detailed_products:
                        if hasattr(product, 'to_dict'):
                            product_dict = product.to_dict()
                            # Add metadata to indicate this product was found via JAN code
                            if jan_code:
                                if not product_dict.get('additional_info'):
                                    product_dict['additional_info'] = {}
                                product_dict['additional_info']['searched_by_jan'] = True
                                product_dict['additional_info']['jan_code'] = jan_code
                            serializable_products.append(product_dict)
                        else:
                            # If it's already a dictionary
                            if isinstance(product, dict):
                                product_dict = product
                            else:
                                # If it's another type of object with __dict__
                                if hasattr(product, '__dict__'):
                                    product_dict = product.__dict__
                                else:
                                    # Last resort: try to convert to a dictionary or create an empty one
                                    try:
                                        product_dict = dict(product)
                                    except:
                                        print(f"Warning: Could not convert {type(product)} to dictionary. Using empty dict.")
                                        product_dict = {}
                            # Add metadata to indicate this product was found via JAN code
                            if jan_code:
                                if not product_dict.get('additional_info'):
                                    product_dict['additional_info'] = {}
                                product_dict['additional_info']['searched_by_jan'] = True
                                product_dict['additional_info']['jan_code'] = jan_code
                            serializable_products.append(product_dict)
                    
                    result = {
                        'product_info': product_info,
                        'keywords': keywords,
                        'jan_code': jan_code,  # Add JAN code to the result
                        'price_comparison': price_results,
                        'detailed_products': serializable_products,
                        'error': None
                    }
                    
                    results.append(result)
                    batch_search_status[batch_id]['results'].append(result)
                    
                except Exception as e:
                    print(f"Error processing '{product_info}': {e}")
                    error_result = {
                        'product_info': product_info,
                        'keywords': [product_info],
                        'price_comparison': [],
                        'detailed_products': [],
                        'error': str(e)
                    }
                    results.append(error_result)
                    batch_search_status[batch_id]['results'].append(error_result)
                    batch_search_status[batch_id]['has_errors'] = True
                
                # Update processed count
                batch_search_status[batch_id]['processed'] += 1
        
        # Mark as completed
        batch_search_status[batch_id]['completed'] = True
        batch_search_status[batch_id]['end_time'] = time.time()
        
        # Add batch ID to the response for status checking
        response = {
            'batch_id': batch_id,
            'results': results
        }
        
        # Clean up old statuses (older than 1 hour)
        cleanup_old_statuses()
        
        return jsonify(response)
    except Exception as e:
        print(f"Error in detailed batch search: {e}")
        # If a batch ID was created, update its status to show failure
        if 'batch_id' in locals():
            batch_search_status[batch_id]['completed'] = True
            batch_search_status[batch_id]['has_errors'] = True
            batch_search_status[batch_id]['error'] = str(e)
            
        return jsonify({'error': str(e)}), 500

def cleanup_old_statuses():
    """
    Clean up status entries older than 1 hour
    """
    current_time = time.time()
    to_delete = []
    
    for batch_id, status in batch_search_status.items():
        if status.get('completed', False) and 'start_time' in status:
            # If completed and older than 1 hour
            if current_time - status['start_time'] > 3600:
                to_delete.append(batch_id)
    
    for batch_id in to_delete:
        del batch_search_status[batch_id]

@app.route('/api/search/batch-keywords', methods=['POST'])
def batch_keywords():
    try:
        data = request.json
        model_numbers = data.get('model_numbers', [])
        custom_prompt = data.get('custom_prompt')
        force_refresh = data.get('force_refresh', False)  # New parameter to bypass cache
        
        if not model_numbers:
            return jsonify({'error': 'No model numbers provided'}), 400
        
        # Initialize the batch keyword generator
        generator = BatchKeywordGenerator()
        
        # Clean model numbers
        cleaned_model_numbers = []
        for model_number in model_numbers:
            cleaned = generator.clean_model_number(model_number)
            if cleaned:
                cleaned_model_numbers.append(cleaned)
        
        if not cleaned_model_numbers:
            return jsonify({'error': 'No valid model numbers provided'}), 400
            
        # First, fetch product information for each model number
        product_info_list = []
        for model_number in cleaned_model_numbers:
            # Try to fetch product info from Amazon or other sources
            try:
                # Use existing search functionality to get product info
                amazon_api = AmazonAPI()
                product_info = amazon_api.search_items(model_number, limit=5)
                
                if product_info and len(product_info) > 0:
                    # Extract relevant product information
                    product = product_info[0]
                    # Check if product is a ProductDetail object
                    if hasattr(product, 'title'):
                        product_details = {
                            "model_number": model_number,
                            "title": product.title,
                            "features": getattr(product, 'features', []),
                            "description": getattr(product, 'description', '')
                        }
                    else:
                        # Handle dictionary format
                        product_details = {
                            "model_number": model_number,
                            "title": product.get('title', ''),
                            "features": product.get('features', []),
                            "description": product.get('description', '')
                        }
                    product_info_list.append(product_details)
                else:
                    # If no product info found, just use the model number
                    product_info_list.append({"model_number": model_number})
            except Exception as e:
                print(f"Error fetching product info for {model_number}: {str(e)}")
                # If error, just use the model number
                product_info_list.append({"model_number": model_number})
        
        # Now generate keywords based on the product information
        results = generator.batch_generate(product_info_list, custom_prompt, force_refresh)
        
        # Extract just the keywords for the response
        enhanced_keywords = [item['keyword'] for item in results]
        
        # Return both the full results and just the keywords (for compatibility with different frontend implementations)
        return jsonify({
            'results': results,  # Original format
            'keywords': enhanced_keywords  # Same format as enhance_keywords endpoint
        })
    except Exception as e:
        print(f"Error in batch keywords: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/find-best-model', methods=['POST'])
def find_best_model():
    """
    Find the best model number that meets the criteria specified in the prompt
    """
    try:
        data = request.json
        model_numbers = data.get('model_numbers', [])
        criteria_prompt = data.get('criteria_prompt')
        
        if not model_numbers:
            return jsonify({'error': 'No model numbers provided'}), 400
            
        if not criteria_prompt:
            return jsonify({'error': 'No criteria prompt provided'}), 400
        
        # Initialize the batch keyword generator
        generator = BatchKeywordGenerator()
        
        # Clean model numbers
        cleaned_model_numbers = []
        for model_number in model_numbers:
            cleaned = generator.clean_model_number(model_number)
            if cleaned:
                cleaned_model_numbers.append(cleaned)
        
        if not cleaned_model_numbers:
            return jsonify({'error': 'No valid model numbers provided'}), 400
            
        # Instead of fetching product information for each model number,
        # directly use Perplexity AI to find the best model
        product_info_list = []
        for model_number in cleaned_model_numbers:
            product_info_list.append({"model_number": model_number})
        
        # Find the best model that meets the criteria
        result = generator.find_best_model(product_info_list, criteria_prompt)
        
        # Return just the best model number and reason
        return jsonify({
            'best_model_number': result.get('best_model_number'),
            'reason': result.get('reason')
        })
    except Exception as e:
        print(f"Error in find best model: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add a route to explicitly handle OPTIONS requests
@app.route('/api/search/product', methods=['OPTIONS'])
def handle_product_options():
    response = jsonify({'status': 'ok'})
    return response

@app.route('/api/search/product', methods=['POST'])
def search_product():
    """
    Search for a specific product by model number or product info
    """
    try:
        data = request.json
        product_info = data.get('product_info', '')
        use_jan_code = data.get('use_jan_code', True)  # Default to True
        
        if not product_info:
            return jsonify({"error": "Product info is required"}), 400
        
        print(f"Starting product search for: {product_info}")
        
        # Check if this is a laptop search to apply special handling
        laptop_brands = ['hp', 'dell', 'lenovo', 'asus', 'acer', 'msi', 'fujitsu', 'toshiba', 'nec', 'vaio']
        laptop_keywords = ['laptop', 'ノートパソコン', 'パソコン', 'PC', 'notebook', 'computer']
        
        is_laptop_search = False
        if any(brand.lower() in product_info.lower() for brand in laptop_brands) and \
           any(keyword.lower() in product_info.lower() for keyword in laptop_keywords):
            is_laptop_search = True
            print(f"Detected laptop search: {product_info}")
        
        # Use direct search with the exact model number/product info
        keywords = [product_info]
        jan_code = None
        
        # Check if it looks like a model number
        is_model_number = bool(re.match(r'^[A-Za-z0-9]+-?[A-Za-z0-9]+', str(product_info)))
        
        # Check if it's already a JAN code (8 or 13 digits)
        is_jan_code = bool(re.match(r'^[0-9]{8}$|^[0-9]{13}$', str(product_info)))
        
        # If it's already a JAN code, use it directly
        if is_jan_code:
            print(f"Input is already a JAN code: {product_info}")
            jan_code = product_info
            keywords = [jan_code]
            
            # Get detailed product information using JAN code
            detailed_products = price_comparison.get_detailed_products_direct(jan_code)
            
        # If it's a model number and JAN code lookup is enabled, try to get a JAN code
        elif is_model_number and use_jan_code:
            jan_code = perplexity_client.get_jan_code(product_info)
            if jan_code:
                # If JAN code is found, it becomes the ONLY search term
                print(f"Found JAN code for {product_info}: {jan_code}")
                # Use only the JAN code for search to ensure consistency across platforms
                keywords = [jan_code]
                
                # Get detailed product information using JAN code
                detailed_products = price_comparison.get_detailed_products_direct(jan_code)
                
                # If no products found with JAN code, fall back to model number
                if not detailed_products or len(detailed_products) == 0:
                    print(f"No products found with JAN code, falling back to model number")
                    detailed_products = price_comparison.get_detailed_products_direct(product_info)
            else:
                # No JAN code found, use the model number
                print(f"No JAN code found for {product_info}, using model number directly")
                detailed_products = price_comparison.get_detailed_products_direct(product_info)
        # Special handling for laptop searches
        elif is_laptop_search:
            print(f"Using specialized laptop search for: {product_info}")
            
            # Try to extract the brand and add it to keywords
            brand = next((brand for brand in laptop_brands if brand.lower() in product_info.lower()), None)
            if brand:
                # Create additional search terms focused on the laptop
                enhanced_terms = [
                    product_info,  # Original search
                    f"{brand} ノートパソコン",  # Brand + generic laptop term
                ]
                
                # If Windows is mentioned, add a Windows-specific term
                if 'windows' in product_info.lower():
                    enhanced_terms.append(f"{brand} ノートパソコン windows")
                
                print(f"Enhanced laptop search terms: {enhanced_terms}")
                
                # Try each term until we get good results
                for term in enhanced_terms:
                    temp_products = price_comparison.get_detailed_products_direct(term)
                    
                    # If we got good results, use them and break
                    if temp_products and len(temp_products) >= 3:
                        detailed_products = temp_products
                        print(f"Found {len(detailed_products)} products using term: {term}")
                        keywords = [term]
                        break
                    elif not detailed_products or len(detailed_products) == 0:
                        # If this is our first attempt, save these results
                        detailed_products = temp_products
                        keywords = [term]
            else:
                # If no brand identified, use standard search
                detailed_products = price_comparison.get_detailed_products_direct(product_info)
        else:
            # Not a model number or JAN code lookup disabled, use normal search
            print(f"Using normal search for {product_info}")
            detailed_products = price_comparison.get_detailed_products_direct(product_info)
        
        # If we still have no products, try a more generic search for laptops
        if is_laptop_search and (not detailed_products or len(detailed_products) == 0):
            print("No products found with specific terms, trying generic laptop search")
            # Extract brand for more generic search
            brand = next((brand for brand in laptop_brands if brand.lower() in product_info.lower()), None)
            if brand:
                generic_term = f"{brand} ノートパソコン"
                detailed_products = price_comparison.get_detailed_products_direct(generic_term)
                if detailed_products and len(detailed_products) > 0:
                    print(f"Found {len(detailed_products)} products using generic term: {generic_term}")
                    keywords = [generic_term]
        
        print(f"Found {len(detailed_products)} total products for search: {product_info}")
        
        # Convert product objects to dictionaries
        serializable_products = []
        for product in detailed_products:
            if hasattr(product, 'to_dict'):
                product_dict = product.to_dict()
                # Add metadata to indicate this product was found via JAN code
                if jan_code:
                    if not product_dict.get('additional_info'):
                        product_dict['additional_info'] = {}
                    product_dict['additional_info']['searched_by_jan'] = True
                    product_dict['additional_info']['jan_code'] = jan_code
                serializable_products.append(product_dict)
            else:
                # If it's already a dictionary
                if isinstance(product, dict):
                    product_dict = product
                else:
                    # If it's another type of object with __dict__
                    if hasattr(product, '__dict__'):
                        product_dict = product.__dict__
                    else:
                        # Last resort: try to convert to a dictionary or create an empty one
                        try:
                            product_dict = dict(product)
                        except:
                            print(f"Warning: Could not convert {type(product)} to dictionary. Using empty dict.")
                            product_dict = {}
                # Add metadata to indicate this product was found via JAN code
                if jan_code:
                    if not product_dict.get('additional_info'):
                        product_dict['additional_info'] = {}
                    product_dict['additional_info']['searched_by_jan'] = True
                    product_dict['additional_info']['jan_code'] = jan_code
                serializable_products.append(product_dict)
        
        # Return the results
        return jsonify({
            'query': product_info,
            'keywords': keywords,
            'jan_code': jan_code,
            'detailed_products': serializable_products
        })
        
    except Exception as e:
        print(f"Error in product search: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-jan-code', methods=['POST'])
def get_jan_code():
    """Get JAN code for a model number using Perplexity AI"""
    try:
        data = request.json
        model_number = data.get('model_number', '')
        
        if not model_number:
            return jsonify({"error": "Model number is required"}), 400
        
        # Get JAN code from Perplexity AI
        jan_code = perplexity_client.get_jan_code(model_number)
        
        # Return the JAN code
        return jsonify({
            'model_number': model_number,
            'jan_code': jan_code
        })
        
    except Exception as e:
        print(f"Error getting JAN code: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze-image-with-perplexity', methods=['POST'])
def analyze_image_with_perplexity():
    """
    Analyze an image using Google Vision API and then use Perplexity AI to extract 
    product information including JAN code, model number, and product name
    """
    try:
        if 'image' in request.files:
            # Handle file upload
            image_file = request.files['image']
            image_data = image_file.read()
            
            # First use Google Vision API to extract text and analyze content
            image_search_engine = ImageSearchEngine()
            text_results = image_search_engine.extract_model_numbers(image_data=image_data)
            content_results = image_search_engine.analyze_image_content(image_data=image_data)
            
            # Combine the results for Perplexity analysis
            detected_text = []
            detected_models = []
            
            if text_results:
                for result in text_results:
                    detected_models.append(result.get('model_number', ''))
                    
            # Now use Perplexity to get better product information
            prompt = f"""
            I have scanned a product image and need to identify it properly. Here's what I found:
            
            Detected Potential Model Numbers: {', '.join(detected_models) if detected_models else 'None'}
            Detected Product Category: {content_results if content_results else 'Unknown'}
            
            Look carefully at the image. If you see:
            - A laptop or notebook computer, identify the brand (HP, Dell, Lenovo, etc.), model series, and specific model if visible
            - Any visible operating system logos like Windows or macOS
            - Screen size, color, and distinctive features
            - Text on the device or packaging that indicates specifications
            
            Based on this detailed analysis, please identify:
            1. The exact product name in Japanese (be specific - e.g. "HP Pavilion ノートパソコン" instead of just "ノートパソコン")
            2. The model number or series
            3. The JAN code (Japanese barcode)
            
            Reply in this exact JSON format with detailed and specific information:
            {{
                "product_name": "Detailed product name in Japanese",
                "model_number": "The model number or series",
                "jan_code": "The JAN code (or 'unknown' if not found)",
                "additional_keywords": ["laptop", "notebook", "computer", "brand name", "operating system"] 
            }}
            
            Never return generic terms like '商品' or 'パソコン' alone. Always be as specific as possible about the exact product shown.
            """
            
            # Call Perplexity API
            perplexity_response = perplexity_client.complete(prompt)
            
            # Parse the JSON response
            try:
                # The response might contain explanatory text before or after the JSON
                import re
                import json
                
                # Try to extract JSON using regex
                json_match = re.search(r'\{.*\}', perplexity_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    product_info = json.loads(json_str)
                else:
                    # Fallback if no JSON is found
                    product_info = {
                        "product_name": content_results if content_results else "Unknown product",
                        "model_number": detected_models[0] if detected_models else "Unknown",
                        "jan_code": "unknown",
                        "additional_keywords": []
                    }
            except Exception as json_error:
                print(f"Error parsing Perplexity response JSON: {json_error}")
                print(f"Raw Perplexity response: {perplexity_response}")
                product_info = {
                    "product_name": content_results if content_results else "Unknown product",
                    "model_number": detected_models[0] if detected_models else "Unknown",
                    "jan_code": "unknown",
                    "additional_keywords": []
                }
            
            return jsonify(product_info)
            
        elif 'image_url' in request.json:
            # Handle image URL
            image_url = request.json['image_url']
            
            # First use Google Vision API to extract text and analyze content
            image_search_engine = ImageSearchEngine()
            text_results = image_search_engine.extract_model_numbers(image_url=image_url)
            content_results = image_search_engine.analyze_image_content(image_url=image_url)
            
            # Combine the results for Perplexity analysis
            detected_text = []
            detected_models = []
            
            if text_results:
                for result in text_results:
                    detected_models.append(result.get('model_number', ''))
                    
            # Now use Perplexity to get better product information
            prompt = f"""
            I have scanned a product image and need to identify it properly. Here's what I found:
            
            Detected Potential Model Numbers: {', '.join(detected_models) if detected_models else 'None'}
            Detected Product Category: {content_results if content_results else 'Unknown'}
            
            Look carefully at the image. If you see:
            - A laptop or notebook computer, identify the brand (HP, Dell, Lenovo, etc.), model series, and specific model if visible
            - Any visible operating system logos like Windows or macOS
            - Screen size, color, and distinctive features
            - Text on the device or packaging that indicates specifications
            
            Based on this detailed analysis, please identify:
            1. The exact product name in Japanese (be specific - e.g. "HP Pavilion ノートパソコン" instead of just "ノートパソコン")
            2. The model number or series
            3. The JAN code (Japanese barcode)
            
            Reply in this exact JSON format with detailed and specific information:
            {{
                "product_name": "Detailed product name in Japanese",
                "model_number": "The model number or series",
                "jan_code": "The JAN code (or 'unknown' if not found)",
                "additional_keywords": ["laptop", "notebook", "computer", "brand name", "operating system"] 
            }}
            
            Never return generic terms like '商品' or 'パソコン' alone. Always be as specific as possible about the exact product shown.
            """
            
            # Call Perplexity API
            perplexity_response = perplexity_client.complete(prompt)
            
            # Parse the JSON response
            try:
                # The response might contain explanatory text before or after the JSON
                import re
                import json
                
                # Try to extract JSON using regex
                json_match = re.search(r'\{.*\}', perplexity_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    product_info = json.loads(json_str)
                else:
                    # Fallback if no JSON is found
                    product_info = {
                        "product_name": content_results if content_results else "Unknown product",
                        "model_number": detected_models[0] if detected_models else "Unknown",
                        "jan_code": "unknown",
                        "additional_keywords": []
                    }
            except Exception as json_error:
                print(f"Error parsing Perplexity response JSON: {json_error}")
                print(f"Raw Perplexity response: {perplexity_response}")
                product_info = {
                    "product_name": content_results if content_results else "Unknown product",
                    "model_number": detected_models[0] if detected_models else "Unknown",
                    "jan_code": "unknown",
                    "additional_keywords": []
                }
            
            return jsonify(product_info)
        else:
            return jsonify({"error": "No image or image URL provided"}), 400
            
    except Exception as e:
        print(f"Error analyzing image with Perplexity: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# Listing Management API Endpoints
# ============================================

@app.route('/api/listings', methods=['GET'])
def get_listings():
    """Get all listings with optional filters"""
    try:
        status = request.args.get('status')
        category = request.args.get('category')
        
        listings = listing_manager.get_all_listings(status=status, category=category)
        
        return jsonify({
            'success': True,
            'listings': [listing.to_dict() for listing in listings],
            'count': len(listings)
        })
    except Exception as e:
        print(f"Error getting listings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/listings/<listing_id>', methods=['GET'])
def get_listing(listing_id):
    """Get a specific listing by ID"""
    try:
        listing = listing_manager.get_listing(listing_id)
        if not listing:
            return jsonify({"error": "Listing not found"}), 404
        
        return jsonify({
            'success': True,
            'listing': listing.to_dict()
        })
    except Exception as e:
        print(f"Error getting listing: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/listings', methods=['POST'])
def create_listing():
    """Create a new listing"""
    try:
        data = request.json
        
        result = listing_manager.create_listing(
            asin=data.get('asin'),
            jp_asin=data.get('jp_asin'),
            us_asin=data.get('us_asin'),
            title=data.get('title', ''),
            jp_price=float(data.get('jp_price', 0)),
            us_price=float(data.get('us_price', 0)),
            listing_price=float(data.get('listing_price', 0)),
            category=data.get('category'),
            manufacturer=data.get('manufacturer'),
            weight=float(data.get('weight', 0)) if data.get('weight') else None,
            dimensions=data.get('dimensions'),
            source_url=data.get('source_url'),
            minimum_profit_threshold=float(data.get('minimum_profit_threshold', 3000)),
            validate=data.get('validate', True)
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f"Error creating listing: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/listings/<listing_id>', methods=['PUT'])
def update_listing(listing_id):
    """Update a listing"""
    try:
        data = request.json
        
        result = listing_manager.update_listing(listing_id, **data)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        print(f"Error updating listing: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/listings/<listing_id>', methods=['DELETE'])
def delete_listing(listing_id):
    """Delete a listing"""
    try:
        result = listing_manager.delete_listing(listing_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        print(f"Error deleting listing: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/listings/bulk-update', methods=['POST'])
def bulk_update_listings():
    """Bulk update listing status"""
    try:
        data = request.json
        listing_ids = data.get('listing_ids', [])
        status = data.get('status')
        
        if not listing_ids or not status:
            return jsonify({"error": "listing_ids and status are required"}), 400
        
        result = listing_manager.bulk_update_status(listing_ids, status)
        return jsonify(result)
    except Exception as e:
        print(f"Error bulk updating listings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/listings/bulk-delete', methods=['POST'])
def bulk_delete_listings():
    """Bulk delete listings"""
    try:
        data = request.json
        listing_ids = data.get('listing_ids', [])
        
        if not listing_ids:
            return jsonify({"error": "listing_ids are required"}), 400
        
        result = listing_manager.bulk_delete(listing_ids)
        return jsonify(result)
    except Exception as e:
        print(f"Error bulk deleting listings: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# Profit Calculation API
# ============================================

@app.route('/api/profit/calculate', methods=['POST'])
def calculate_profit():
    """Calculate profit for a product"""
    try:
        data = request.json
        
        result = profit_calculator.calculate_profit(
            us_price=float(data.get('us_price', 0)),
            jp_listing_price=float(data.get('jp_listing_price', 0)),
            weight_kg=data.get('weight_kg'),
            dimensions_cm=data.get('dimensions_cm'),
            international_shipping_cost=data.get('international_shipping_cost'),
            domestic_shipping_cost=data.get('domestic_shipping_cost'),
            customs_fee=data.get('customs_fee'),
            transfer_fee=data.get('transfer_fee'),
            customs_clearance_fee=data.get('customs_clearance_fee'),
            exchange_rate=data.get('exchange_rate'),
            amazon_fee_override=data.get('amazon_fee_override'),
            calculate_shipping=data.get('calculate_shipping', True)
        )
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        print(f"Error calculating profit: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# Shipping Calculation API
# ============================================

@app.route('/api/shipping/calculate', methods=['POST'])
def calculate_shipping():
    """Calculate international shipping cost"""
    try:
        data = request.json
        
        result = shipping_calculator.calculate_shipping(
            weight_kg=float(data.get('weight_kg', 0)),
            dimensions_cm=data.get('dimensions_cm', {}),
            destination_country=data.get('destination_country', 'JP'),
            source_country=data.get('source_country', 'US'),
            provider=data.get('provider')
        )
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        print(f"Error calculating shipping: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# US Amazon Price Comparison API
# ============================================

@app.route('/api/compare/us-jp', methods=['POST'])
def compare_us_jp_prices():
    """Compare prices between US and Japan Amazon"""
    try:
        data = request.json
        asin = data.get('asin')
        us_asin = data.get('us_asin')
        
        if not asin:
            return jsonify({"error": "ASIN is required"}), 400
        
        # Get Japan Amazon price using PA-API
        # Check if asin is a valid ASIN format (10 characters)
        jp_price = None
        jp_title = None
        jp_image_url = None
        jp_url = None
        jp_description = None
        jp_availability = None
        jp_product_asin = asin
        
        if len(asin) == 10 and asin.isalnum():
            # Use PA-API get_items_by_asin for direct ASIN lookup
            print(f"Using PA-API to get Japan Amazon product by ASIN: {asin}")
            jp_product = amazon_api.get_items_by_asin(asin)
            if jp_product:
                jp_price = jp_product.get('price')
                jp_title = jp_product.get('title')
                jp_image_url = jp_product.get('image_url')
                jp_url = jp_product.get('url')
                jp_availability = jp_product.get('availability')
                jp_product_asin = jp_product.get('asin', asin)
                print(f"Found JP product via PA-API: {jp_title} - ¥{jp_price}")
            else:
                # Fallback to search_items if get_items_by_asin fails
                print(f"PA-API get_items_by_asin failed, trying search_items")
                jp_products = amazon_api.search_items(asin, limit=1, use_paapi_for_asin=True)
                if jp_products:
                    product = jp_products[0]
                    if hasattr(product, 'to_dict'):
                        product_dict = product.to_dict()
                        jp_price = product_dict.get('price')
                        jp_title = product_dict.get('title')
                        jp_image_url = product_dict.get('image_url')
                        jp_url = product_dict.get('url')
                        jp_description = product_dict.get('description')
                        jp_availability = product_dict.get('availability')
                    elif isinstance(product, dict):
                        jp_price = product.get('price')
                        jp_title = product.get('title')
                        jp_image_url = product.get('image_url')
                        jp_url = product.get('url')
                        jp_description = product.get('description')
                        jp_availability = product.get('availability')
                    else:
                        jp_price = getattr(product, 'price', None)
                        jp_title = getattr(product, 'title', None)
                        jp_image_url = getattr(product, 'image_url', None)
                        jp_url = getattr(product, 'url', None)
                        jp_description = getattr(product, 'description', None)
                        jp_availability = getattr(product, 'availability', None)
        else:
            # Not a valid ASIN format, use search
            print(f"Not a valid ASIN format, using search_items")
            jp_products = amazon_api.search_items(asin, limit=1)
            if jp_products:
                product = jp_products[0]
                if hasattr(product, 'to_dict'):
                    product_dict = product.to_dict()
                    jp_price = product_dict.get('price')
                    jp_title = product_dict.get('title')
                    jp_image_url = product_dict.get('image_url')
                    jp_url = product_dict.get('url')
                    jp_description = product_dict.get('description')
                    jp_availability = product_dict.get('availability')
                elif isinstance(product, dict):
                    jp_price = product.get('price')
                    jp_title = product.get('title')
                    jp_image_url = product.get('image_url')
                    jp_url = product.get('url')
                    jp_description = product.get('description')
                    jp_availability = product.get('availability')
                else:
                    jp_price = getattr(product, 'price', None)
                    jp_title = getattr(product, 'title', None)
                    jp_image_url = getattr(product, 'image_url', None)
                    jp_url = getattr(product, 'url', None)
                    jp_description = getattr(product, 'description', None)
                    jp_availability = getattr(product, 'availability', None)
        
        # Get US Amazon price
        us_asin_to_check = us_asin or asin
        us_price = None
        us_title = None
        us_image_url = None
        us_url = None
        us_description = None
        us_availability = None
        us_product_asin = us_asin_to_check
        
        # Try to use PA-API for US Amazon if we have US credentials configured
        # For now, use the existing method (which may use scraping)
        print(f"Getting US Amazon product by ASIN: {us_asin_to_check}")
        us_product = us_amazon_api.get_product_by_asin(us_asin_to_check)
        if us_product:
            us_price = us_product.price if us_product else None
            us_title = us_product.title if us_product else None
            us_image_url = us_product.image_url if hasattr(us_product, 'image_url') else None
            us_url = us_product.url if hasattr(us_product, 'url') else None
            us_description = us_product.description if hasattr(us_product, 'description') else None
            us_availability = us_product.availability if hasattr(us_product, 'availability') else None
            us_product_asin = us_product.asin if hasattr(us_product, 'asin') and us_product.asin else us_asin_to_check
            print(f"Found US product: {us_title} - ${us_price}")
        
        # Get exchange rate (default to 150.0 if not provided)
        exchange_rate = float(data.get('exchange_rate', 150.0))
        
        # Calculate price difference
        price_difference = None
        price_difference_percent = None
        if jp_price and us_price:
            # Convert US price to JPY
            us_price_jpy = us_price * exchange_rate
            price_difference = jp_price - us_price_jpy
            price_difference_percent = (price_difference / us_price_jpy * 100) if us_price_jpy > 0 else 0
        
        return jsonify({
            'success': True,
            'jp_amazon': {
                'asin': jp_product_asin,
                'title': jp_title,
                'price': jp_price,
                'price_currency': 'JPY',
                'image_url': jp_image_url,
                'url': jp_url,
                'description': jp_description,
                'availability': jp_availability
            },
            'us_amazon': {
                'asin': us_product_asin,
                'title': us_title,
                'price': us_price,
                'price_currency': 'USD',
                'price_jpy': us_price * exchange_rate if us_price else None,
                'image_url': us_image_url,
                'url': us_url,
                'description': us_description,
                'availability': us_availability
            },
            'price_difference': {
                'amount_jpy': price_difference,
                'percent': price_difference_percent,
                'exchange_rate_used': exchange_rate
            }
        })
    except Exception as e:
        print(f"Error comparing US-JP prices: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# Amazon PA-API GetItems Endpoint
# ============================================

@app.route('/api/amazon/get-items', methods=['POST'])
def get_amazon_items():
    """
    Get items using Amazon PA-API with custom request structure
    
    Request body format:
    {
        "ItemIds": ["B0199980K4", "B000HZD168", "B01180YUXS", "B00BKQTA4A"],
        "ItemIdType": "ASIN",
        "LanguagesOfPreference": ["en_US"],
        "Marketplace": "www.amazon.com",
        "PartnerTag": "xyz-20",
        "PartnerType": "Associates",
        "Resources": [
            "Images.Primary.Small",
            "ItemInfo.Title",
            "ItemInfo.Features",
            "Offers.Summaries.HighestPrice",
            "ParentASIN"
        ]
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate required fields
        if "ItemIds" not in data:
            return jsonify({"error": "ItemIds is required"}), 400
        
        if not data.get("ItemIds"):
            return jsonify({"error": "ItemIds cannot be empty"}), 400
        
        # Use default values if not provided
        request_data = {
            "ItemIds": data.get("ItemIds", []),
            "ItemIdType": data.get("ItemIdType", "ASIN"),
            "LanguagesOfPreference": data.get("LanguagesOfPreference", ["en_US"]),
            "Marketplace": data.get("Marketplace", "www.amazon.com"),
            "PartnerTag": data.get("PartnerTag", amazon_partner_tag),
            "PartnerType": data.get("PartnerType", "Associates"),
            "Resources": data.get("Resources", [
                "Images.Primary.Small",
                "ItemInfo.Title",
                "ItemInfo.Features",
                "Offers.Summaries.HighestPrice",
                "ParentASIN"
            ])
        }
        
        # Call the get_items_by_request method
        result = amazon_api.get_items_by_request(request_data)
        
        # Check if there's an error in the result
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify({
            "success": True,
            **result
        })
        
    except Exception as e:
        print(f"Error in get_amazon_items endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ============================================
# Stock Monitoring API
# ============================================

@app.route('/api/monitor/check/<listing_id>', methods=['POST'])
def check_listing_stock(listing_id):
    """Manually check stock for a specific listing"""
    try:
        result = stock_monitor.check_listing(listing_id)
        return jsonify(result)
    except Exception as e:
        print(f"Error checking listing stock: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/monitor/check-all', methods=['POST'])
def check_all_listings_stock():
    """Manually trigger check for all active listings"""
    try:
        result = stock_monitor.check_all_listings()
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        print(f"Error checking all listings: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/monitor/status', methods=['GET'])
def get_monitor_status():
    """Get stock monitoring status"""
    try:
        return jsonify({
            'success': True,
            'monitoring': stock_monitor.monitoring,
            'check_interval_hours': stock_monitor.check_interval_hours,
            'auto_stop_on_out_of_stock': stock_monitor.auto_stop_on_out_of_stock,
            'auto_update_prices': stock_monitor.auto_update_prices,
            'auto_stop_low_profit': stock_monitor.auto_stop_low_profit
        })
    except Exception as e:
        print(f"Error getting monitor status: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# Blacklist Management API
# ============================================

@app.route('/api/blacklist/check', methods=['POST'])
def check_blacklist():
    """Check if a product is blacklisted"""
    try:
        data = request.json
        
        result = listing_manager.blacklist_manager.check_product(
            asin=data.get('asin', ''),
            title=data.get('title', ''),
            manufacturer=data.get('manufacturer', ''),
            category=data.get('category', ''),
            brand=data.get('brand', '')
        )
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        print(f"Error checking blacklist: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/blacklist', methods=['GET'])
def get_blacklist():
    """Get all blacklist entries"""
    try:
        entries = listing_manager.blacklist_manager.get_all_entries()
        return jsonify({
            'success': True,
            'entries': entries,
            'count': len(entries)
        })
    except Exception as e:
        print(f"Error getting blacklist: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/blacklist', methods=['POST'])
def add_blacklist_entry():
    """Add a blacklist entry"""
    try:
        data = request.json or {}
        entry_type = data.get('type')
        value = data.get('value')
        reason = data.get('reason', '')
        severity = data.get('severity', 'high')

        if not entry_type or not value:
            return jsonify({"error": "type and value are required"}), 400

        entry = listing_manager.blacklist_manager.create_entry(
            entry_type=entry_type,
            value=value,
            reason=reason,
            severity=severity,
            auto_detected=False
        )
        listing_manager.blacklist_manager.persist()

        return jsonify({
            'success': True,
            'entry': entry.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"Error adding blacklist entry: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/blacklist/<entry_id>', methods=['DELETE'])
def delete_blacklist_entry(entry_id):
    """Delete a blacklist entry"""
    try:
        removed = listing_manager.blacklist_manager.remove_entry(entry_id)
        if not removed:
            return jsonify({"error": "Entry not found"}), 404

        listing_manager.blacklist_manager.persist()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting blacklist entry: {e}")
        return jsonify({"error": str(e)}), 500
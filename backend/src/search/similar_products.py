from src.api.perplexity_client import perplexity_client
from src.utils.helpers import clean_text, validate_product_info
from src.comparison.price_compare import PriceComparisonEngine

class ProductSearchEngine:
    def __init__(self):
        self.ai_client = perplexity_client
        self.price_comparison = PriceComparisonEngine()

    def search(self, search_term):
        """
        検索語を使用して商品を検索
        """
        try:
            print(f"Searching for products with term: '{search_term}'")
            
            # 価格比較
            price_results = []
            try:
                # 直接検索モードを使用
                price_results = self.price_comparison.compare_prices_direct(search_term)
                print(f"Found {len(price_results)} price results")
            except Exception as e:
                print(f"Error in price comparison: {e}")
                # Continue with empty price results if this fails
            
            # 詳細な商品情報を取得
            detailed_products = []
            try:
                # 直接検索モードを使用
                detailed_products = self.price_comparison.get_detailed_products_direct(search_term)
                print(f"Found {len(detailed_products)} detailed products")
                
                # ProductDetailオブジェクトを辞書に変換
                serializable_detailed_products = []
                for product in detailed_products:
                    if isinstance(product, dict):
                        # If it's already a dictionary, just copy it
                        serializable_detailed_products.append(product)
                    elif hasattr(product, '__dict__'):
                        # オブジェクトを辞書に変換
                        product_dict = product.__dict__.copy()
                        # 非シリアライズ可能なフィールドを削除
                        if '_sa_instance_state' in product_dict:
                            del product_dict['_sa_instance_state']
                        serializable_detailed_products.append(product_dict)
                    else:
                        # Other types, try to convert to dictionary if possible
                        try:
                            product_dict = dict(product)
                            serializable_detailed_products.append(product_dict)
                        except:
                            # If all else fails, add as is
                            serializable_detailed_products.append(product)
                
                detailed_products = serializable_detailed_products
            except Exception as e:
                print(f"Error getting detailed products: {e}")
                # Continue with empty detailed products if this fails
            
            return {
                'price_comparison': price_results,
                'detailed_products': detailed_products
            }
        except Exception as e:
            print(f"Error in product search: {e}")
            return {
                'price_comparison': [],
                'detailed_products': [],
                'error': str(e)
            }

    def generate_search_keywords(self, product_info):
        """
        商品情報から検索キーワードを生成
        """
        if not validate_product_info(product_info):
            # Instead of raising an error, return the original term as the keyword
            print(f"Warning: Invalid product information '{product_info}'. Using as-is.")
            return [product_info]

        prompt = f"""
        以下の商品名、型番、仕様情報から重要なキーワードを組み合わせて表現を変え、
        類似商品を検索しやすくする検索キーワードを作成してください。
        商品情報と特徴を組み合わせて、重要な検索キーワードを1つ抽出してください。
        商品名＋商品特徴＋サイズや重量など互いに近いものを出力してください。
        
        既存メーカーを選択しないように、メーカー名や型番は含めないでください。
        
        型番: {product_info}
        
        検索キーワードを生成してください。
        """
        
        response = self.ai_client.complete(prompt)
        return self.process_keywords(response)

    def find_model_numbers(self, keyword):
        """
        キーワードから関連する型番を検索
        """
        print(f"Finding model numbers for keyword: '{keyword}'")
        
        prompt = f"""
        以下のキーワードに関連する代表的な製品の型番を3つ見つけてください。
        型番のみをリストで出力してください。
        
        キーワード: {keyword}
        
        出力形式:
        - 型番1
        - 型番2
        - 型番3
        
        メーカー名や説明は含めず、型番のみを出力してください。
        """
        
        try:
            response = self.ai_client.complete(prompt)
            model_numbers = self.extract_model_numbers(response)
            
            # Always include the original keyword as the first item
            if keyword not in model_numbers:
                model_numbers.insert(0, keyword)
                
            print(f"Found model numbers for '{keyword}': {model_numbers}")
            return model_numbers
        except Exception as e:
            print(f"Error finding model numbers for '{keyword}': {e}")
            # Return the original keyword if there's an error
            return [keyword]
    
    def extract_model_numbers(self, response):
        """
        AIのレスポンスから型番を抽出
        """
        if not response:
            return []
            
        model_numbers = []
        for line in response.split('\n'):
            line = line.strip()
            # Skip empty lines and lines that don't look like model numbers
            if line and (line.startswith('-') or line.startswith('*') or line.startswith('•')):
                # Extract the model number by removing the list marker
                model_number = line.lstrip('-*•').strip()
                if model_number:
                    model_numbers.append(model_number)
                    
        # If no model numbers were found in the expected format, try to extract any non-empty lines
        if not model_numbers:
            for line in response.split('\n'):
                line = line.strip()
                if line and not line.lower().startswith(('キーワード', '出力形式')):
                    model_numbers.append(line)
                    
        return model_numbers[:3]  # Return at most 3 model numbers

    def process_keywords(self, response):
        """
        AIのレスポンスを処理してキーワードリストを生成
        """
        if not response:
            return []
            
        # 改行で分割し、各行を個別のキーワードとして扱う
        keywords = []
        for line in response.split('\n'):
            line = line.strip()
            if line and not line.startswith('型番:') and not line.startswith('検索キーワード'):
                keyword = clean_text(line)
                if keyword:
                    keywords.append(keyword)
                    
        # 重複を削除し、最大3つのキーワードを返す
        unique_keywords = list(dict.fromkeys(keywords))
        return unique_keywords[:3]  # 上位3つのキーワードを返す

    def batch_generate_keywords(self, product_info_list):
        """
        複数の商品情報から一括でキーワードを生成
        """
        results = []
        for product_info in product_info_list:
            try:
                keywords = self.generate_search_keywords(product_info)
                results.append({
                    'product_info': product_info,
                    'keywords': keywords,
                    'error': None
                })
            except Exception as e:
                print(f"Error generating keywords for '{product_info}': {e}")
                # Return the original term as fallback
                results.append({
                    'product_info': product_info,
                    'keywords': [product_info],
                    'error': str(e)
                })
        
        return results 
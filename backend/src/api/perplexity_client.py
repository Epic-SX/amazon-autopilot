import requests
import json
from ..config.settings import PERPLEXITY_API_KEY
from ..cache.jan_code_cache import jan_code_cache

class PerplexityClient:
    def __init__(self):
        self.api_key = PERPLEXITY_API_KEY
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def complete(self, prompt):
        try:
            payload = {
                "model": "sonar",  # ドキュメントに記載されている正しいモデル名
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.2,
                "top_p": 0.9
            }
            
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                data=json.dumps(payload)
            )
            
            if response.status_code != 200:
                print(f"Error: API returned status code {response.status_code}")
                print(f"Response: {response.text}")
                # エラー時にはダミーのキーワードを返す
                return "- 精密工具\n- 測定器具\n- 工業用部品"
                
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            print(f"Error in Perplexity API call: {e}")
            # 例外発生時にもダミーのキーワードを返す
            return "- 精密工具\n- 測定器具\n- 工業用部品"
            
    def get_jan_code(self, model_number):
        """
        Get JAN code for a specific model number using Perplexity AI
        
        Args:
            model_number (str): The model number to search for
            
        Returns:
            str: JAN code if found, None otherwise
        """
        # First, check if the JAN code is in the cache
        cached_jan_code = jan_code_cache.get(model_number)
        if cached_jan_code:
            print(f"Found cached JAN code for {model_number}: {cached_jan_code}")
            return cached_jan_code
        
        try:
            # Improved prompt with more details and context
            prompt = f"""
            I'm searching for the exact JAN code (Japanese barcode) for a product with this model number: {model_number}

            A JAN code (similar to UPC or EAN) is typically 8 or 13 digits, all numeric.
            For example: 4901480000000 or 49123456

            Please search Japanese e-commerce sites like Amazon.co.jp, Rakuten, Yahoo Shopping, etc.
            Even if you find multiple potential JAN codes, return ONLY the most likely one that matches this exact product.

            Return ONLY the JAN code in the following format:
            JAN: [the JAN code with ONLY digits, no spaces or dashes]

            If you can't find the exact JAN code with high confidence, reply with:
            JAN: NOT_FOUND
            """
            
            payload = {
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a specialized agent that only searches for JAN codes (Japanese barcodes) for products. Reply ONLY with the requested information in the specified format. Never explain your reasoning or add any commentary."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 100,
                "temperature": 0.1
            }
            
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                data=json.dumps(payload)
            )
            
            if response.status_code != 200:
                print(f"Error: API returned status code {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Extract JAN code from response
            jan_code = None
            if "JAN:" in content:
                jan_code = content.split("JAN:")[1].strip().split("\n")[0].strip()
                # Validate JAN code - it should only contain digits and be 8 or 13 digits
                if jan_code and jan_code != "NOT_FOUND":
                    # Remove any non-digit characters
                    clean_jan = ''.join(c for c in jan_code if c.isdigit())
                    if len(clean_jan) in [8, 13]:
                        # Cache the JAN code for future use
                        print(f"Valid JAN code found: {clean_jan}")
                        jan_code_cache.set(model_number, clean_jan)
                        return clean_jan
                    else:
                        print(f"Invalid JAN code format (expected 8 or 13 digits): {jan_code}")
            
            # If not found or invalid, try a second attempt with a different approach
            if jan_code is None or jan_code == "NOT_FOUND":
                print(f"First attempt failed, trying second approach for model number: {model_number}")
                
                # Focus on Japanese search in the second attempt
                second_prompt = f"""
                製品のJANコード（日本のバーコード）を見つけてください。
                型番: {model_number}
                
                JAN コードは通常8桁または13桁の数字のみです（例: 4901480000000）。
                Amazon.co.jp、楽天市場、Yahoo!ショッピングなどで検索してください。
                
                見つけたJANコードのみを以下の形式で返してください:
                JAN: [数字のみのJANコード]
                
                見つからない場合は次のように返してください:
                JAN: NOT_FOUND
                """
                
                payload = {
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": "あなたは日本の製品のJANコードを検索する専門家です。結果のみを指定された形式で返してください。"
                        },
                        {
                            "role": "user",
                            "content": second_prompt
                        }
                    ],
                    "max_tokens": 100,
                    "temperature": 0.1
                }
                
                try:
                    response = requests.post(
                        self.endpoint,
                        headers=self.headers,
                        data=json.dumps(payload)
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result["choices"][0]["message"]["content"]
                        
                        if "JAN:" in content:
                            jan_code = content.split("JAN:")[1].strip().split("\n")[0].strip()
                            if jan_code and jan_code != "NOT_FOUND":
                                # Remove any non-digit characters
                                clean_jan = ''.join(c for c in jan_code if c.isdigit())
                                if len(clean_jan) in [8, 13]:
                                    # Cache the JAN code for future use
                                    print(f"Valid JAN code found in second attempt: {clean_jan}")
                                    jan_code_cache.set(model_number, clean_jan)
                                    return clean_jan
                                else:
                                    print(f"Invalid JAN code format in second attempt: {jan_code}")
                except Exception as second_e:
                    print(f"Error in second attempt to get JAN code: {second_e}")
            
            return None
            
        except Exception as e:
            print(f"Error getting JAN code from Perplexity: {e}")
            return None

perplexity_client = PerplexityClient() 
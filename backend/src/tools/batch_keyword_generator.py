import os
import re
import requests
import sys
import json
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

class BatchKeywordGenerator:
    def __init__(self):
        self.api_key = os.environ.get('PERPLEXITY_API_KEY')
        if not self.api_key:
            print("Error: PERPLEXITY_API_KEY environment variable is not set.")
            sys.exit(1)
        
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def clean_model_number(self, model_number):
        """
        Clean up the model number by removing numbering like "1 EA628W-25B" -> "EA628W-25B"
        and other common patterns that might appear in user input
        """
        if isinstance(model_number, dict):
            # If it's already a dictionary, just return it
            return model_number
            
        # Convert to string if it's not already
        model_number = str(model_number).strip()
        
        # Remove numbering at the beginning (e.g., "1 EA628W-25B" -> "EA628W-25B")
        model_number = re.sub(r'^\d+[\s\.:]?\s*', '', model_number)
        
        # Remove "型番:" prefix if present
        model_number = re.sub(r'^型番[:：]?\s*', '', model_number)
        
        # Remove any text that looks like part of a prompt
        if any(phrase in model_number for phrase in ['下記の商品', '検索キーワード', 'プロンプト', '出力は商品名', 'メーカー名']):
            return ""
            
        return model_number.strip()

    def generate_keyword(self, model_number, custom_prompt=None):
        """
        Generate a search keyword for a single model number or product information
        
        Args:
            model_number: Can be just a model number string or a detailed product information string
            custom_prompt: Optional custom prompt template
        
        Returns:
            A generated keyword string
        """
        # Check if model_number is a simple string or a detailed product info
        if isinstance(model_number, dict):
            # It's a product info dictionary
            product_info = model_number
            model_number_str = product_info.get("model_number", "")
            context = ""
            
            # Build context from product info
            if "model_number" in product_info:
                context += f"型番: {product_info['model_number']}\n"
            
            if "title" in product_info and product_info["title"]:
                context += f"商品名: {product_info['title']}\n"
            
            if "features" in product_info and product_info["features"]:
                context += "特徴:\n" + "\n".join([f"- {feature}" for feature in product_info["features"]]) + "\n"
            
            if "description" in product_info and product_info["description"]:
                context += f"説明: {product_info['description']}\n"
            
            cleaned_model = context
        else:
            # It's just a model number string
            cleaned_model = self.clean_model_number(model_number)
        
        # Use custom prompt if provided, otherwise use default prompt
        if custom_prompt:
            if isinstance(model_number, dict):
                # If we have rich product info, just append the prompt to the context
                prompt = cleaned_model + "\n\n" + custom_prompt.replace('{model_number}', model_number_str)
            else:
                prompt = custom_prompt.replace('{model_number}', cleaned_model)
        else:
            if isinstance(model_number, dict):
                # Use the rich context with default instructions
                prompt = f"""
                下記の商品情報から重要なキーワードを組み合わせて表現を変えて
                類似品を検索しやすいように検索キーワードを作成してください。
                商品の情報や特徴を組み合わせて重要な検索キーワードを１個抽出してください。
                出力は商品名＋商品の特徴＋サイズや重量は近いものでお願いします。
                既存のメーカーを選定しないように、メーカー名、型番は記載しないようにお願いします。
                英語の場合は日本語に翻訳してください。
                情報が少ない場合は、型番から製品の種類を推測し、一般的な用途や特徴を考慮してキーワードを生成してください。
                単に型番をそのまま返すのではなく、その型番が表す可能性のある製品の一般名称や特徴を推測してください。
                
                {cleaned_model}
                
                最適な検索キーワードを1つだけ出力してください。余計な説明は不要です。
                """
            else:
                prompt = f"""
                下記の商品名、型番、仕様情報から重要なキーワードを組み合わせて表現を変えて
                類似品を検索しやすいように検索キーワードを作成してください。
                商品の情報や特徴を組み合わせて重要な検索キーワードを１個抽出してください。
                出力は商品名＋商品の特徴＋サイズや重量は近いものでお願いします。
                既存のメーカーを選定しないように、メーカー名、型番は記載しないようにお願いします。
                英語の場合は日本語に翻訳してください。
                情報が少ない場合は、型番から製品の種類を推測し、一般的な用途や特徴を考慮してキーワードを生成してください。
                単に型番をそのまま返すのではなく、その型番が表す可能性のある製品の一般名称や特徴を推測してください。
                
                型番 {cleaned_model}
                
                最適な検索キーワードを1つだけ出力してください。余計な説明は不要です。
                """
        
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json={
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": "あなたは製品型番から最適な検索キーワードを生成する専門家です。型番を見て、その製品が何であるかを推測し、具体的な特徴や用途を含む日本語のキーワードを1つ生成してください。単に型番をそのまま返すのではなく、その製品を表す一般的な名称や特徴を提供してください。例えば「EA628W-25B」という型番からは「25mm幅 耐久性 防水テープ」のようなキーワードを生成します。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 100
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                enhanced_keyword = result["choices"][0]["message"]["content"].strip()
                return enhanced_keyword
            else:
                print(f"API error: {response.status_code} - {response.text}")
                if isinstance(model_number, dict) and "model_number" in model_number:
                    return model_number["model_number"]  # Fallback to using the model number directly
                else:
                    return cleaned_model  # Fallback to using the model number directly
                
        except Exception as e:
            print(f"Error in API call: {e}")
            if isinstance(model_number, dict) and "model_number" in model_number:
                return model_number["model_number"]  # Fallback to using the model number directly
            else:
                return cleaned_model  # Fallback to using the model number directly

    def batch_generate(self, model_numbers, custom_prompt=None, force_refresh=False):
        """
        Generate search keywords for multiple model numbers or product information
        
        Args:
            model_numbers: List of model numbers or product information dictionaries
            custom_prompt: Optional custom prompt template
            force_refresh: If True, bypass cache and generate new keywords
        
        Returns:
            List of dictionaries with model_number and keyword
        """
        results = []
        
        # Create cache directory if it doesn't exist
        os.makedirs("cache", exist_ok=True)
        
        # Process model numbers in batches to improve performance
        batch_size = 5  # Process 5 model numbers at a time
        batched_model_numbers = [model_numbers[i:i + batch_size] for i in range(0, len(model_numbers), batch_size)]
        
        for batch in batched_model_numbers:
            batch_results = []
            
            for item in batch:
                if not item:
                    continue
                
                if isinstance(item, dict):
                    # It's a product info dictionary
                    model_number = item.get("model_number", "")
                    # Clean the model number
                    model_number = self.clean_model_number(model_number)
                    if not model_number.strip():
                        continue
                        
                    # Update the model number in the dictionary
                    item["model_number"] = model_number
                    
                    # Check cache first (unless force refresh is enabled)
                    cache_key = f"{model_number}-{hash(str(custom_prompt))}"
                    cache_file = os.path.join("cache", f"keyword_{hash(cache_key)}.json")
                    
                    if not force_refresh and os.path.exists(cache_file):
                        try:
                            with open(cache_file, 'r', encoding='utf-8') as f:
                                cached_result = json.load(f)
                                # Check if the cache is still valid (less than 24 hours old)
                                if 'timestamp' in cached_result:
                                    cache_time = cached_result.get('timestamp', 0)
                                    if time.time() - cache_time < 86400:  # 24 hours
                                        # Remove timestamp from the result
                                        result_copy = cached_result.copy()
                                        if 'timestamp' in result_copy:
                                            del result_copy['timestamp']
                                        batch_results.append(result_copy)
                                        continue
                        except Exception as e:
                            print(f"Error reading cache: {e}")
                    
                    keyword = self.generate_keyword(item, custom_prompt)
                    result = {
                        "model_number": model_number.strip(),
                        "keyword": keyword,
                        "timestamp": time.time()
                    }
                    
                    # Save to cache
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    
                    # Remove timestamp from the result
                    result_copy = result.copy()
                    if 'timestamp' in result_copy:
                        del result_copy['timestamp']
                    
                    batch_results.append(result_copy)
                else:
                    # It's a model number string
                    # Clean the model number
                    model_number = self.clean_model_number(item)
                    if not model_number.strip():
                        continue
                    
                    # Check cache first (unless force refresh is enabled)
                    cache_key = f"{model_number}-{hash(str(custom_prompt))}"
                    cache_file = os.path.join("cache", f"keyword_{hash(cache_key)}.json")
                    
                    if not force_refresh and os.path.exists(cache_file):
                        try:
                            with open(cache_file, 'r', encoding='utf-8') as f:
                                cached_result = json.load(f)
                                # Check if the cache is still valid (less than 24 hours old)
                                if 'timestamp' in cached_result:
                                    cache_time = cached_result.get('timestamp', 0)
                                    if time.time() - cache_time < 86400:  # 24 hours
                                        # Remove timestamp from the result
                                        result_copy = cached_result.copy()
                                        if 'timestamp' in result_copy:
                                            del result_copy['timestamp']
                                        batch_results.append(result_copy)
                                        continue
                        except Exception as e:
                            print(f"Error reading cache: {e}")
                    
                    keyword = self.generate_keyword(model_number, custom_prompt)
                    result = {
                        "model_number": model_number.strip(),
                        "keyword": keyword,
                        "timestamp": time.time()
                    }
                    
                    # Save to cache
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    
                    # Remove timestamp from the result
                    result_copy = result.copy()
                    if 'timestamp' in result_copy:
                        del result_copy['timestamp']
                    
                    batch_results.append(result_copy)
            
            # Add batch results to overall results
            results.extend(batch_results)
        
        return results
        
    def find_best_model(self, model_numbers, criteria_prompt):
        """
        Find the best model number that meets the criteria specified in the prompt
        
        Args:
            model_numbers: List of model numbers or product information dictionaries
            criteria_prompt: Prompt describing the criteria for selection
            
        Returns:
            Dictionary with best_model_number and reason (without all_evaluations)
        """
        # First, gather product information for all model numbers
        product_info_list = []
        
        for item in model_numbers:
            if not item:
                continue
                
            if isinstance(item, dict):
                # It's already a product info dictionary
                model_number = item.get("model_number", "")
                # Clean the model number
                model_number = self.clean_model_number(model_number)
                if not model_number.strip():
                    continue
                    
                # Update the model number in the dictionary
                item["model_number"] = model_number
                product_info_list.append(item)
            else:
                # It's a model number string
                # Clean the model number
                model_number = self.clean_model_number(item)
                if not model_number.strip():
                    continue
                    
                # Just use the model number as is
                product_info_list.append({"model_number": model_number})
        
        if not product_info_list:
            return {
                "best_model_number": None,
                "reason": "No valid model numbers provided"
            }
            
        # Generate a cache key based on model numbers and criteria
        cache_key = f"{','.join([item.get('model_number', '') for item in product_info_list])}-{hash(criteria_prompt)}"
        cache_file = os.path.join("cache", f"best_model_{hash(cache_key)}.json")
        
        # Check if we have a cached result
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_result = json.load(f)
                    # Check if the cache is still valid (less than 24 hours old)
                    if 'timestamp' in cached_result:
                        cache_time = cached_result.get('timestamp', 0)
                        if time.time() - cache_time < 86400:  # 24 hours
                            # Remove timestamp and all_evaluations from the result
                            result_copy = cached_result.copy()
                            if 'timestamp' in result_copy:
                                del result_copy['timestamp']
                            if 'all_evaluations' in result_copy:
                                del result_copy['all_evaluations']
                            return result_copy
            except Exception as e:
                print(f"Error reading cache: {e}")
        
        # Create a simplified prompt with just model numbers to reduce API call size
        model_numbers_list = [item.get('model_number', '') for item in product_info_list]
        
        # Create a prompt to evaluate all models against the criteria
        evaluation_prompt = f"""
        以下の複数の型番から、次の条件に最も合致する商品を1つ選んでください。
        各型番について、Amazonや楽天などのECサイトで検索して情報を収集し、条件に照らし合わせて評価してください。
        
        条件：
        {criteria_prompt}
        
        型番リスト：
        {', '.join(model_numbers_list)}
        
        回答形式：
        {{
          "best_model_number": "選択した商品の型番",
          "reason": "選択した理由の詳細な説明"
        }}
        
        JSONフォーマットで回答してください。評価の詳細は不要です。
        """
        
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json={
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": "あなたは商品選定の専門家です。複数の型番から条件に最も合致するものを選び、その理由を詳しく説明してください。回答はJSON形式で提供してください。"
                        },
                        {
                            "role": "user",
                            "content": evaluation_prompt
                        }
                    ],
                    "max_tokens": 1000
                },
                timeout=30  # Add timeout to prevent hanging
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"].strip()
                
                # Try to parse the JSON response
                try:
                    # Extract JSON from the response (in case there's additional text)
                    json_match = re.search(r'({.*})', ai_response, re.DOTALL)
                    if json_match:
                        ai_response = json_match.group(1)
                    
                    evaluation_result = json.loads(ai_response)
                    
                    # Add timestamp for caching
                    evaluation_result['timestamp'] = time.time()
                    
                    # Save to cache
                    os.makedirs("cache", exist_ok=True)
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(evaluation_result, f, ensure_ascii=False, indent=2)
                    
                    # Remove timestamp from the result
                    result_copy = evaluation_result.copy()
                    if 'timestamp' in result_copy:
                        del result_copy['timestamp']
                    if 'all_evaluations' in result_copy:
                        del result_copy['all_evaluations']
                    
                    return result_copy
                except json.JSONDecodeError as e:
                    print(f"Error parsing AI response as JSON: {e}")
                    print(f"Raw response: {ai_response}")
                    # Return a basic response with the raw AI text
                    return {
                        "best_model_number": model_numbers_list[0] if model_numbers_list else None,
                        "reason": f"Error parsing AI response: {ai_response}"
                    }
            else:
                print(f"API error: {response.status_code} - {response.text}")
                return {
                    "best_model_number": model_numbers_list[0] if model_numbers_list else None,
                    "reason": f"API error: {response.status_code}"
                }
                
        except Exception as e:
            print(f"Error in API call: {e}")
            return {
                "best_model_number": model_numbers_list[0] if model_numbers_list else None,
                "reason": f"Error: {str(e)}"
            }

def main():
    """
    Main function to run the batch keyword generator from command line
    """
    if len(sys.argv) < 2:
        print("Usage: python batch_keyword_generator.py <input_file> [output_file] [custom_prompt_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "keywords_output.json"
    custom_prompt_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    # Read model numbers from input file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            model_numbers = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)
    
    # Read custom prompt if provided
    custom_prompt = None
    if custom_prompt_file:
        try:
            with open(custom_prompt_file, 'r', encoding='utf-8') as f:
                custom_prompt = f.read().strip()
        except Exception as e:
            print(f"Error reading custom prompt file: {e}")
            sys.exit(1)
    
    # Generate keywords
    generator = BatchKeywordGenerator()
    results = generator.batch_generate(model_numbers, custom_prompt)
    
    # Write results to output file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Results written to {output_file}")
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
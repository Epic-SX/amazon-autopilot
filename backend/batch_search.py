#!/usr/bin/env python
"""
Batch Keyword Generator for Product Model Numbers

This script generates optimized search keywords for multiple product model numbers
using the Perplexity AI API.

Usage:
    python batch_search.py [options]

Options:
    -i, --input FILE       Input file with model numbers (one per line)
    -o, --output FILE      Output file for results (default: keywords_output.json)
    -p, --prompt FILE      Custom prompt file (optional)
    -m, --models           Directly specify model numbers (comma-separated)
    -h, --help             Show this help message

Examples:
    python batch_search.py -i model_numbers.txt -o results.json
    python batch_search.py -m "EA628W-25B,EA715SE-10,EA628PP-35" -o results.json
    python batch_search.py -i model_numbers.txt -p custom_prompt.txt
"""

import os
import re
import sys
import json
import argparse
from src.tools.batch_keyword_generator import BatchKeywordGenerator
from src.api.amazon_api import AmazonAPI

def parse_arguments():
    parser = argparse.ArgumentParser(description='Batch Keyword Generator for Product Model Numbers')
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-i', '--input', help='Input file with model numbers (one per line)')
    input_group.add_argument('-m', '--models', help='Directly specify model numbers (comma-separated)')
    
    # Output options
    parser.add_argument('-o', '--output', default='keywords_output.json', 
                        help='Output file for results (default: keywords_output.json)')
    
    # Prompt options
    parser.add_argument('-p', '--prompt', help='Custom prompt file (optional)')
    
    return parser.parse_args()

def read_model_numbers(file_path):
    """Read model numbers from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)

def read_custom_prompt(file_path):
    """Read custom prompt from a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading custom prompt file: {e}")
        sys.exit(1)

def main():
    """
    Main function to run the batch keyword generator from command line
    """
    args = parse_arguments()
    
    # Get model numbers from either file or command line
    model_numbers = []
    if args.input:
        model_numbers = read_model_numbers(args.input)
    elif args.models:
        model_numbers = [m.strip() for m in args.models.split(',') if m.strip()]
    
    if not model_numbers:
        print("Error: No model numbers provided")
        sys.exit(1)
    
    # Read custom prompt if provided
    custom_prompt = None
    if args.prompt:
        custom_prompt = read_custom_prompt(args.prompt)
    
    print(f"Processing {len(model_numbers)} model numbers...")
    
    # Initialize the batch keyword generator
    generator = BatchKeywordGenerator()
    
    # Clean model numbers
    cleaned_model_numbers = []
    for model_number in model_numbers:
        cleaned = generator.clean_model_number(model_number)
        if cleaned:
            cleaned_model_numbers.append(cleaned)
            
    if not cleaned_model_numbers:
        print("Error: No valid model numbers found after cleaning")
        sys.exit(1)
        
    print(f"Found {len(cleaned_model_numbers)} valid model numbers after cleaning")
    
    # First, try to fetch product information for each model number
    product_info_list = []
    amazon_api = AmazonAPI()
    
    for model_number in cleaned_model_numbers:
        print(f"Fetching product info for {model_number}...")
        try:
            # Search for products using the model number
            product_info = amazon_api.search_items(model_number, limit=5)
            if product_info:
                print(f"Found {len(product_info)} products on Amazon for model number: {model_number}")
                # Extract relevant product information
                if product_info and len(product_info) > 0:
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
                    print(f"Found product info for {model_number}")
                else:
                    # If no product info found, just use the model number
                    product_info_list.append({"model_number": model_number})
                    print(f"No product info found for {model_number}")
            else:
                # If no product info found, just use the model number
                product_info_list.append({"model_number": model_number})
                print(f"No product info found for {model_number}")
        except Exception as e:
            print(f"Error fetching product info for {model_number}: {str(e)}")
            # If error, just use the model number
            product_info_list.append({"model_number": model_number})
    
    # Generate keywords based on the product information
    print("Generating keywords...")
    results = generator.batch_generate(product_info_list, custom_prompt)
    
    # Print results to console
    print("\n=== Generated Keywords ===")
    for result in results:
        print(f"Model: {result['model_number']}")
        print(f"Keyword: {result['keyword']}")
        print("---")
    
    # Write results to output file
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nResults written to {args.output}")
    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
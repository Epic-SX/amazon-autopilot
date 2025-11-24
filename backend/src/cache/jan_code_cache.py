import os
import json
import time
from pathlib import Path

class JanCodeCache:
    """
    Cache for JAN codes to avoid repeated API calls for the same model numbers
    """
    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "jan_code_cache.json")
        self.cache = {}
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load existing cache if it exists
        self._load_cache()
    
    def _load_cache(self):
        """Load the cache from the cache file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
            except Exception as e:
                print(f"Error loading JAN code cache: {e}")
                self.cache = {}
    
    def _save_cache(self):
        """Save the cache to the cache file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving JAN code cache: {e}")
    
    def get(self, model_number):
        """
        Get a JAN code from the cache
        
        Args:
            model_number (str): The model number to look up
            
        Returns:
            str or None: The JAN code if it exists in the cache and is still valid, None otherwise
        """
        if model_number in self.cache:
            cache_entry = self.cache[model_number]
            
            # Check if the cache entry is still valid (less than 7 days old)
            if time.time() - cache_entry.get('timestamp', 0) < 7 * 24 * 60 * 60:
                return cache_entry.get('jan_code')
        
        return None
    
    def set(self, model_number, jan_code):
        """
        Set a JAN code in the cache
        
        Args:
            model_number (str): The model number
            jan_code (str): The JAN code to cache
        """
        self.cache[model_number] = {
            'jan_code': jan_code,
            'timestamp': time.time()
        }
        
        # Save the cache
        self._save_cache()
    
    def clear(self):
        """Clear the cache"""
        self.cache = {}
        self._save_cache()
    
    def cleanup(self, max_age_days=30):
        """
        Remove old entries from the cache
        
        Args:
            max_age_days (int): Maximum age of cache entries in days
        """
        now = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        # Remove old entries
        to_remove = []
        for model_number, cache_entry in self.cache.items():
            if now - cache_entry.get('timestamp', 0) > max_age_seconds:
                to_remove.append(model_number)
        
        # Remove the entries
        for model_number in to_remove:
            del self.cache[model_number]
        
        # Save the cache if any entries were removed
        if to_remove:
            self._save_cache()

# Create a singleton instance
jan_code_cache = JanCodeCache() 
import os
import json
import time
import shutil
from pathlib import Path

def clear_old_cache(max_age_days=7):
    """
    Clear cache files older than max_age_days
    
    Args:
        max_age_days (int): Maximum age of cache files in days
    """
    print(f"Clearing cache files older than {max_age_days} days")
    
    # Convert days to seconds
    max_age_seconds = max_age_days * 24 * 60 * 60
    current_time = time.time()
    
    # Cache directories to check
    cache_dirs = [
        Path("cache"),
        Path("cache/amazon")
    ]
    
    # Create directories if they don't exist
    for cache_dir in cache_dirs:
        cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Track statistics
    total_files = 0
    deleted_files = 0
    freed_space = 0
    
    # Process each cache directory
    for cache_dir in cache_dirs:
        if not cache_dir.exists():
            continue
            
        print(f"Processing cache directory: {cache_dir}")
        
        # Process JSON cache files
        for cache_file in cache_dir.glob("*.json"):
            total_files += 1
            
            try:
                # Check file modification time
                file_mtime = os.path.getmtime(cache_file)
                file_age = current_time - file_mtime
                
                # If file is older than max_age_days, delete it
                if file_age > max_age_seconds:
                    file_size = os.path.getsize(cache_file)
                    os.remove(cache_file)
                    deleted_files += 1
                    freed_space += file_size
                    print(f"Deleted old cache file: {cache_file}")
                else:
                    # Check if the file contains a timestamp
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'timestamp' in data:
                                cache_time = data.get('timestamp', 0)
                                if current_time - cache_time > max_age_seconds:
                                    file_size = os.path.getsize(cache_file)
                                    os.remove(cache_file)
                                    deleted_files += 1
                                    freed_space += file_size
                                    print(f"Deleted old cache file based on timestamp: {cache_file}")
                    except:
                        # If we can't read the file as JSON, skip it
                        pass
            except Exception as e:
                print(f"Error processing cache file {cache_file}: {e}")
        
        # Process pickle files
        for cache_file in cache_dir.glob("*.pkl"):
            total_files += 1
            
            try:
                # Check file modification time
                file_mtime = os.path.getmtime(cache_file)
                file_age = current_time - file_mtime
                
                # If file is older than max_age_days, delete it
                if file_age > max_age_seconds:
                    file_size = os.path.getsize(cache_file)
                    os.remove(cache_file)
                    deleted_files += 1
                    freed_space += file_size
                    print(f"Deleted old cache file: {cache_file}")
            except Exception as e:
                print(f"Error processing cache file {cache_file}: {e}")
    
    # Print summary
    print(f"Cache cleanup complete:")
    print(f"  Total files checked: {total_files}")
    print(f"  Files deleted: {deleted_files}")
    print(f"  Space freed: {freed_space / (1024*1024):.2f} MB")

if __name__ == "__main__":
    clear_old_cache()
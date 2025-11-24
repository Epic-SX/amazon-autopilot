"""
Duplicate Detection Service
Detects duplicate listings based on ASIN, source URL, and keyword similarity
"""
from typing import List, Dict, Any, Optional
from src.models.listing import ProductListing
import difflib

class DuplicateDetector:
    """
    Detects duplicate product listings
    """
    
    def __init__(self):
        self.similarity_threshold = 0.85  # 85% similarity threshold
    
    def check_duplicate(
        self,
        asin: str,
        source_url: Optional[str] = None,
        title: Optional[str] = None,
        existing_listings: Optional[List[ProductListing]] = None
    ) -> Dict[str, Any]:
        """
        Check if a product is a duplicate
        
        Args:
            asin: Product ASIN
            source_url: Source URL (purchase URL)
            title: Product title
            existing_listings: List of existing listings to check against
        
        Returns:
            Dict with 'is_duplicate', 'reason', and 'matching_listing_id'
        """
        if not existing_listings:
            return {
                'is_duplicate': False,
                'reason': None,
                'matching_listing_id': None
            }
        
        # Check ASIN duplicate
        for listing in existing_listings:
            if listing.asin == asin:
                return {
                    'is_duplicate': True,
                    'reason': f'ASIN already exists: {asin}',
                    'matching_listing_id': listing.listing_id,
                    'match_type': 'asin'
                }
            
            # Check US ASIN match
            if listing.us_asin and listing.us_asin == asin:
                return {
                    'is_duplicate': True,
                    'reason': f'US ASIN already exists: {asin}',
                    'matching_listing_id': listing.listing_id,
                    'match_type': 'us_asin'
                }
        
        # Check source URL duplicate
        if source_url:
            for listing in existing_listings:
                if listing.source_url and listing.source_url == source_url:
                    return {
                        'is_duplicate': True,
                        'reason': f'Source URL already exists: {source_url}',
                        'matching_listing_id': listing.listing_id,
                        'match_type': 'source_url'
                    }
        
        # Check keyword similarity (pseudo-duplicate)
        if title:
            for listing in existing_listings:
                if listing.title:
                    similarity = self._calculate_similarity(title, listing.title)
                    if similarity >= self.similarity_threshold:
                        return {
                            'is_duplicate': True,
                            'reason': f'Similar product title (similarity: {similarity:.2%})',
                            'matching_listing_id': listing.listing_id,
                            'match_type': 'keyword_similarity',
                            'similarity_score': similarity
                        }
        
        return {
            'is_duplicate': False,
            'reason': None,
            'matching_listing_id': None
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings
        Uses sequence matcher for fuzzy matching
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize text
        text1_lower = text1.lower().strip()
        text2_lower = text2.lower().strip()
        
        # Use sequence matcher
        similarity = difflib.SequenceMatcher(None, text1_lower, text2_lower).ratio()
        
        return similarity
    
    def find_duplicates(
        self,
        listings: List[ProductListing]
    ) -> List[Dict[str, Any]]:
        """
        Find all duplicate pairs in a list of listings
        
        Returns:
            List of duplicate pairs with details
        """
        duplicates = []
        checked = set()
        
        for i, listing1 in enumerate(listings):
            for j, listing2 in enumerate(listings[i+1:], start=i+1):
                pair_key = tuple(sorted([listing1.listing_id, listing2.listing_id]))
                
                if pair_key in checked:
                    continue
                
                checked.add(pair_key)
                
                # Check if duplicates
                duplicate_check = self.check_duplicate(
                    asin=listing1.asin,
                    source_url=listing1.source_url,
                    title=listing1.title,
                    existing_listings=[listing2]
                )
                
                if duplicate_check['is_duplicate']:
                    duplicates.append({
                        'listing1_id': listing1.listing_id,
                        'listing2_id': listing2.listing_id,
                        'reason': duplicate_check['reason'],
                        'match_type': duplicate_check.get('match_type', 'unknown')
                    })
        
        return duplicates



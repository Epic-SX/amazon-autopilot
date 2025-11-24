"""
Migration script to move data from JSON files to SQLite database
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from src.database.db import get_db

def migrate_listings(json_file: Path, db):
    """Migrate listings from JSON to SQLite"""
    if not json_file.exists():
        print(f"Listings JSON file not found: {json_file}")
        return 0
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        listings = data.get('listings', [])
        if not listings:
            print("No listings found in JSON file")
            return 0
        
        migrated = 0
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            for listing_data in listings:
                try:
                    # Check if listing already exists
                    cursor.execute(
                        "SELECT listing_id FROM listings WHERE listing_id = ?",
                        (listing_data.get('listing_id'),)
                    )
                    if cursor.fetchone():
                        print(f"Listing {listing_data.get('listing_id')} already exists, skipping")
                        continue
                    
                    # Convert dimensions dict to JSON string
                    dimensions = listing_data.get('dimensions', {})
                    dimensions_str = json.dumps(dimensions) if dimensions else None
                    
                    # Convert metadata dict to JSON string
                    metadata = listing_data.get('metadata', {})
                    metadata_str = json.dumps(metadata) if metadata else None
                    
                    cursor.execute("""
                        INSERT INTO listings (
                            listing_id, asin, jp_asin, us_asin, title,
                            jp_price, us_price, listing_price, profit_amount, profit_rate,
                            status, stock_status, shipping_available, last_checked,
                            created_at, updated_at, risk_score, category, manufacturer,
                            weight, dimensions, international_shipping_cost, domestic_shipping_cost,
                            customs_fee, transfer_fee, amazon_fee, minimum_profit_threshold,
                            source_url, notes, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        listing_data.get('listing_id'),
                        listing_data.get('asin'),
                        listing_data.get('jp_asin'),
                        listing_data.get('us_asin'),
                        listing_data.get('title', ''),
                        listing_data.get('jp_price', 0.0),
                        listing_data.get('us_price', 0.0),
                        listing_data.get('listing_price', 0.0),
                        listing_data.get('profit_amount', 0.0),
                        listing_data.get('profit_rate', 0.0),
                        listing_data.get('status', 'draft'),
                        listing_data.get('stock_status', 'unknown'),
                        1 if listing_data.get('shipping_available', False) else 0,
                        listing_data.get('last_checked'),
                        listing_data.get('created_at', datetime.now().isoformat()),
                        listing_data.get('updated_at', datetime.now().isoformat()),
                        listing_data.get('risk_score', 0.0),
                        listing_data.get('category'),
                        listing_data.get('manufacturer'),
                        listing_data.get('weight'),
                        dimensions_str,
                        listing_data.get('international_shipping_cost', 0.0),
                        listing_data.get('domestic_shipping_cost', 0.0),
                        listing_data.get('customs_fee', 0.0),
                        listing_data.get('transfer_fee', 0.0),
                        listing_data.get('amazon_fee', 0.0),
                        listing_data.get('minimum_profit_threshold', 3000.0),
                        listing_data.get('source_url'),
                        listing_data.get('notes'),
                        metadata_str
                    ))
                    migrated += 1
                except Exception as e:
                    print(f"Error migrating listing {listing_data.get('listing_id')}: {e}")
            
            conn.commit()
        
        print(f"Migrated {migrated} listings to SQLite")
        return migrated
    except Exception as e:
        print(f"Error migrating listings: {e}")
        return 0

def migrate_blacklist(json_file: Path, db):
    """Migrate blacklist entries from JSON to SQLite"""
    if not json_file.exists():
        print(f"Blacklist JSON file not found: {json_file}")
        return 0
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        entries = data.get('entries', [])
        if not entries:
            print("No blacklist entries found in JSON file")
            return 0
        
        migrated = 0
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            for entry_data in entries:
                try:
                    # Check if entry already exists
                    cursor.execute(
                        "SELECT entry_id FROM blacklist_entries WHERE entry_id = ?",
                        (entry_data.get('entry_id'),)
                    )
                    if cursor.fetchone():
                        print(f"Blacklist entry {entry_data.get('entry_id')} already exists, skipping")
                        continue
                    
                    # Convert metadata dict to JSON string
                    metadata = entry_data.get('metadata', {})
                    metadata_str = json.dumps(metadata) if metadata else None
                    
                    cursor.execute("""
                        INSERT INTO blacklist_entries (
                            entry_id, entry_type, value, reason, severity,
                            auto_detected, metadata, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry_data.get('entry_id'),
                        entry_data.get('entry_type'),
                        entry_data.get('value'),
                        entry_data.get('reason', ''),
                        entry_data.get('severity', 'high'),
                        1 if entry_data.get('auto_detected', False) else 0,
                        metadata_str,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    migrated += 1
                except Exception as e:
                    print(f"Error migrating blacklist entry {entry_data.get('entry_id')}: {e}")
            
            conn.commit()
        
        print(f"Migrated {migrated} blacklist entries to SQLite")
        return migrated
    except Exception as e:
        print(f"Error migrating blacklist: {e}")
        return 0

def main():
    """Main migration function"""
    data_dir = Path("data")
    listings_json = data_dir / "listings.json"
    blacklist_json = data_dir / "blacklist.json"
    
    print("Starting migration from JSON to SQLite...")
    print(f"Database will be created at: data/app.db")
    
    db = get_db()
    
    # Migrate listings
    if listings_json.exists():
        print(f"\nMigrating listings from {listings_json}...")
        migrate_listings(listings_json, db)
    else:
        print(f"\nListings JSON file not found: {listings_json}")
    
    # Migrate blacklist
    if blacklist_json.exists():
        print(f"\nMigrating blacklist from {blacklist_json}...")
        migrate_blacklist(blacklist_json, db)
    else:
        print(f"\nBlacklist JSON file not found: {blacklist_json}")
    
    print("\nMigration completed!")
    print("\nNote: Original JSON files are preserved. You can delete them after verifying the migration.")

if __name__ == "__main__":
    main()



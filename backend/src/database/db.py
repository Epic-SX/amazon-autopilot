"""
SQLite Database Module
Handles database initialization, connection, and schema management
"""
import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

class Database:
    """
    SQLite database manager
    """
    def __init__(self, db_path: str = "data/app.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_schema(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Listings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS listings (
                    listing_id TEXT PRIMARY KEY,
                    asin TEXT NOT NULL,
                    jp_asin TEXT,
                    us_asin TEXT,
                    title TEXT NOT NULL,
                    jp_price REAL DEFAULT 0.0,
                    us_price REAL DEFAULT 0.0,
                    listing_price REAL DEFAULT 0.0,
                    profit_amount REAL DEFAULT 0.0,
                    profit_rate REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'draft',
                    stock_status TEXT DEFAULT 'unknown',
                    shipping_available INTEGER DEFAULT 0,
                    last_checked TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    risk_score REAL DEFAULT 0.0,
                    category TEXT,
                    manufacturer TEXT,
                    weight REAL,
                    dimensions TEXT,
                    international_shipping_cost REAL DEFAULT 0.0,
                    domestic_shipping_cost REAL DEFAULT 0.0,
                    customs_fee REAL DEFAULT 0.0,
                    transfer_fee REAL DEFAULT 0.0,
                    amazon_fee REAL DEFAULT 0.0,
                    minimum_profit_threshold REAL DEFAULT 3000.0,
                    source_url TEXT,
                    notes TEXT,
                    metadata TEXT
                )
            """)
            
            # Blacklist entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blacklist_entries (
                    entry_id TEXT PRIMARY KEY,
                    entry_type TEXT NOT NULL,
                    value TEXT NOT NULL,
                    reason TEXT,
                    severity TEXT DEFAULT 'high',
                    auto_detected INTEGER DEFAULT 0,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(entry_type, value)
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_listings_asin ON listings(asin)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_listings_category ON listings(category)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_blacklist_type ON blacklist_entries(entry_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_blacklist_value ON blacklist_entries(value)
            """)
            
            conn.commit()
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch one row"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

# Global database instance
_db_instance: Optional[Database] = None

def get_db(db_path: str = "data/app.db") -> Database:
    """Get or create database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance



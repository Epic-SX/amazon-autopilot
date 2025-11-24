"""
Blacklist Model for Prohibited/Restricted Products
"""
from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path
import json
import os
import uuid
from datetime import datetime
from src.database.db import get_db

class BlacklistType(Enum):
    """Types of blacklist entries"""
    ASIN = "asin"
    MANUFACTURER = "manufacturer"
    KEYWORD = "keyword"
    CATEGORY = "category"
    BRAND = "brand"

class BlacklistEntry:
    """
    Represents a blacklist entry for prohibited/restricted products
    """
    def __init__(
        self,
        entry_id: str,
        entry_type: BlacklistType,
        value: str,
        reason: str = "",
        severity: str = "high",  # high, medium, low
        auto_detected: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.entry_id = entry_id
        self.entry_type = entry_type
        self.value = value.lower() if isinstance(value, str) else value  # Normalize to lowercase
        self.reason = reason
        self.severity = severity
        self.auto_detected = auto_detected
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'entry_id': self.entry_id,
            'entry_type': self.entry_type.value,
            'value': self.value,
            'reason': self.reason,
            'severity': self.severity,
            'auto_detected': self.auto_detected,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlacklistEntry':
        """Create from dictionary"""
        return cls(
            entry_id=data['entry_id'],
            entry_type=BlacklistType(data['entry_type']),
            value=data['value'],
            reason=data.get('reason', ''),
            severity=data.get('severity', 'high'),
            auto_detected=data.get('auto_detected', False),
            metadata=data.get('metadata', {})
        )

class BlacklistManager:
    """
    Manages blacklist entries and provides checking functionality using SQLite
    """
    def __init__(self, data_file: str = "data/blacklist.json"):
        self.entries: Dict[str, List[BlacklistEntry]] = {
            BlacklistType.ASIN.value: [],
            BlacklistType.MANUFACTURER.value: [],
            BlacklistType.KEYWORD.value: [],
            BlacklistType.CATEGORY.value: [],
            BlacklistType.BRAND.value: []
        }
        self.db = get_db()
        self._load_default_blacklist()
        self._load_from_database()
    
    def _load_from_database(self):
        """Load blacklist entries from database"""
        rows = self.db.fetch_all("SELECT * FROM blacklist_entries")
        for row in rows:
            entry = BlacklistEntry(
                entry_id=row['entry_id'],
                entry_type=BlacklistType(row['entry_type']),
                value=row['value'],
                reason=row.get('reason', ''),
                severity=row.get('severity', 'high'),
                auto_detected=bool(row.get('auto_detected', 0)),
                metadata=json.loads(row['metadata']) if row.get('metadata') else {}
            )
            # Only add if not already in memory (check by value, not object identity)
            entry_type = entry.entry_type.value
            existing_values = [e.value for e in self.entries[entry_type]]
            if entry.value not in existing_values:
                self.entries[entry_type].append(entry)
    
    def _load_default_blacklist(self):
        """Load default blacklist entries based on real-world Amazon restrictions"""
        # High-risk manufacturers (known for IP issues)
        high_risk_manufacturers = [
            'apple', 'sony', 'nintendo', 'microsoft', 'samsung', 
            'canon', 'nikon', 'panasonic', 'sharp', 'toshiba',
            'dyson', 'dyson', 'philips', 'braun', 'oral-b'
        ]
        
        # Dangerous goods keywords
        dangerous_keywords = [
            'battery', 'リチウム', 'lithium', 'explosive', '爆発物',
            'flammable', '可燃性', 'toxic', '毒性', 'hazardous',
            'dangerous', '危険物', 'hazmat', 'corrosive', '腐食性',
            'radioactive', '放射性', 'weapon', '武器', 'knife', 'ナイフ',
            'gun', '銃', 'ammunition', '弾薬'
        ]
        
        # Restricted categories
        restricted_categories = [
            'toys_and_games', 'toys', '玩具',  # High risk for new accounts
            'health_personal_care', 'health', '健康',  # Requires approval
            'beauty', '美容',  # Requires approval
            'grocery', '食品',  # Requires approval
            'baby', 'ベビー',  # Requires approval
        ]
        
        # Prohibited keywords
        prohibited_keywords = [
            'counterfeit', '偽物', 'replica', 'レプリカ',
            'used sold as new', '中古を新品として',
            'unauthorized', '無許可', 'parallel import', '並行輸入'
        ]
        
        # Add default entries (will be saved to DB if not already present)
        for manufacturer in high_risk_manufacturers:
            entry = BlacklistEntry(
                entry_id=str(uuid.uuid4()),
                entry_type=BlacklistType.MANUFACTURER,
                value=manufacturer,
                reason="High-risk manufacturer - potential IP infringement",
                severity="high",
                auto_detected=True
            )
            self.entries[BlacklistType.MANUFACTURER.value].append(entry)
            # Save to database (check if exists first)
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT entry_id FROM blacklist_entries WHERE entry_type = ? AND value = ?",
                        (entry.entry_type.value, entry.value)
                    )
                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO blacklist_entries (
                                entry_id, entry_type, value, reason, severity,
                                auto_detected, metadata, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            entry.entry_id,
                            entry.entry_type.value,
                            entry.value,
                            entry.reason,
                            entry.severity,
                            1,
                            None,
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))
                    conn.commit()
            except Exception:
                pass  # Ignore errors for default entries
        
        for keyword in dangerous_keywords:
            entry = BlacklistEntry(
                entry_id=str(uuid.uuid4()),
                entry_type=BlacklistType.KEYWORD,
                value=keyword,
                reason="Dangerous goods keyword",
                severity="high",
                auto_detected=True
            )
            self.entries[BlacklistType.KEYWORD.value].append(entry)
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR IGNORE INTO blacklist_entries (
                            entry_id, entry_type, value, reason, severity,
                            auto_detected, metadata, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.entry_id,
                        entry.entry_type.value,
                        entry.value,
                        entry.reason,
                        entry.severity,
                        1,
                        None,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
            except Exception:
                pass
        
        for category in restricted_categories:
            entry = BlacklistEntry(
                entry_id=str(uuid.uuid4()),
                entry_type=BlacklistType.CATEGORY,
                value=category,
                reason="Restricted category for new accounts",
                severity="medium",
                auto_detected=True
            )
            self.entries[BlacklistType.CATEGORY.value].append(entry)
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR IGNORE INTO blacklist_entries (
                            entry_id, entry_type, value, reason, severity,
                            auto_detected, metadata, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.entry_id,
                        entry.entry_type.value,
                        entry.value,
                        entry.reason,
                        entry.severity,
                        1,
                        None,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
            except Exception:
                pass
        
        for keyword in prohibited_keywords:
            entry = BlacklistEntry(
                entry_id=str(uuid.uuid4()),
                entry_type=BlacklistType.KEYWORD,
                value=keyword,
                reason="Prohibited keyword",
                severity="high",
                auto_detected=True
            )
            self.entries[BlacklistType.KEYWORD.value].append(entry)
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR IGNORE INTO blacklist_entries (
                            entry_id, entry_type, value, reason, severity,
                            auto_detected, metadata, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.entry_id,
                        entry.entry_type.value,
                        entry.value,
                        entry.reason,
                        entry.severity,
                        1,
                        None,
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    conn.commit()
            except Exception:
                pass
    
    def add_entry(self, entry: BlacklistEntry):
        """Add a blacklist entry to memory and database"""
        entry_type = entry.entry_type.value
        # Check if entry with same type and value already exists
        existing_values = [e.value for e in self.entries[entry_type]]
        if entry.value not in existing_values:
            self.entries[entry_type].append(entry)
            # Save to database (check if exists first to avoid UNIQUE constraint violation)
            try:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    # Check if entry with same type and value exists
                    cursor.execute(
                        "SELECT entry_id FROM blacklist_entries WHERE entry_type = ? AND value = ?",
                        (entry.entry_type.value, entry.value)
                    )
                    existing = cursor.fetchone()
                    if not existing:
                        cursor.execute("""
                            INSERT INTO blacklist_entries (
                                entry_id, entry_type, value, reason, severity,
                                auto_detected, metadata, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            entry.entry_id,
                            entry.entry_type.value,
                            entry.value,
                            entry.reason,
                            entry.severity,
                            1 if entry.auto_detected else 0,
                            json.dumps(entry.metadata) if entry.metadata else None,
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))
                    conn.commit()
            except Exception as e:
                print(f"Error saving blacklist entry to database: {e}")

    def create_entry(
        self,
        entry_type: str,
        value: str,
        reason: str = "",
        severity: str = "high",
        auto_detected: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BlacklistEntry:
        """Helper to create and store a blacklist entry"""
        entry = BlacklistEntry(
            entry_id=str(uuid.uuid4()),
            entry_type=BlacklistType(entry_type),
            value=value,
            reason=reason,
            severity=severity,
            auto_detected=auto_detected,
            metadata=metadata
        )
        self.add_entry(entry)
        return entry
    
    def remove_entry(self, entry_id: str) -> bool:
        """Remove a blacklist entry by ID from memory and database"""
        removed = False
        for entry_list in self.entries.values():
            for entry in entry_list:
                if entry.entry_id == entry_id:
                    entry_list.remove(entry)
                    removed = True
                    break
            if removed:
                break
        
        if removed:
            # Remove from database
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM blacklist_entries WHERE entry_id = ?", (entry_id,))
                conn.commit()
        
        return removed
    
    def check_asin(self, asin: str) -> Optional[BlacklistEntry]:
        """Check if ASIN is blacklisted"""
        asin_lower = asin.lower()
        for entry in self.entries[BlacklistType.ASIN.value]:
            if entry.value == asin_lower:
                return entry
        return None
    
    def check_manufacturer(self, manufacturer: str) -> Optional[BlacklistEntry]:
        """Check if manufacturer is blacklisted"""
        if not manufacturer:
            return None
        manufacturer_lower = manufacturer.lower()
        for entry in self.entries[BlacklistType.MANUFACTURER.value]:
            if entry.value in manufacturer_lower or manufacturer_lower in entry.value:
                return entry
        return None
    
    def check_keywords(self, text: str) -> List[BlacklistEntry]:
        """Check if text contains blacklisted keywords"""
        if not text:
            return []
        text_lower = text.lower()
        matches = []
        for entry in self.entries[BlacklistType.KEYWORD.value]:
            if entry.value in text_lower:
                matches.append(entry)
        return matches
    
    def check_category(self, category: str) -> Optional[BlacklistEntry]:
        """Check if category is blacklisted"""
        if not category:
            return None
        category_lower = category.lower()
        for entry in self.entries[BlacklistType.CATEGORY.value]:
            if entry.value in category_lower or category_lower in entry.value:
                return entry
        return None
    
    def check_product(
        self, 
        asin: str, 
        title: str = "", 
        manufacturer: str = "", 
        category: str = "",
        brand: str = ""
    ) -> Dict[str, Any]:
        """
        Comprehensive product blacklist check
        Returns dict with is_blocked flag and reasons
        """
        reasons = []
        severity = "low"
        
        # Check ASIN
        asin_match = self.check_asin(asin)
        if asin_match:
            reasons.append(f"ASIN blacklisted: {asin_match.reason}")
            severity = asin_match.severity
        
        # Check manufacturer
        manufacturer_match = self.check_manufacturer(manufacturer)
        if manufacturer_match:
            reasons.append(f"Manufacturer blacklisted: {manufacturer_match.reason}")
            if manufacturer_match.severity == "high":
                severity = "high"
        
        # Check keywords in title
        keyword_matches = self.check_keywords(title)
        if keyword_matches:
            for match in keyword_matches:
                reasons.append(f"Prohibited keyword found: {match.reason}")
                if match.severity == "high":
                    severity = "high"
        
        # Check category
        category_match = self.check_category(category)
        if category_match:
            reasons.append(f"Restricted category: {category_match.reason}")
            if category_match.severity == "high":
                severity = "high"
        
        # Check brand
        if brand:
            brand_match = self.check_manufacturer(brand)  # Use same logic as manufacturer
            if brand_match:
                reasons.append(f"Brand blacklisted: {brand_match.reason}")
                if brand_match.severity == "high":
                    severity = "high"
        
        is_blocked = len(reasons) > 0
        
        return {
            'is_blocked': is_blocked,
            'severity': severity,
            'reasons': reasons,
            'matches': {
                'asin': asin_match.to_dict() if asin_match else None,
                'manufacturer': manufacturer_match.to_dict() if manufacturer_match else None,
                'keywords': [m.to_dict() for m in keyword_matches],
                'category': category_match.to_dict() if category_match else None
            }
        }
    
    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all blacklist entries from database"""
        rows = self.db.fetch_all("SELECT * FROM blacklist_entries ORDER BY created_at DESC")
        entries = []
        for row in rows:
            entries.append({
                'entry_id': row['entry_id'],
                'entry_type': row['entry_type'],
                'value': row['value'],
                'reason': row.get('reason', ''),
                'severity': row.get('severity', 'high'),
                'auto_detected': bool(row.get('auto_detected', 0)),
                'metadata': json.loads(row['metadata']) if row.get('metadata') else {}
            })
        return entries

    def persist(self):
        """Persist current entries to database (entries are saved immediately, this is for compatibility)"""
        # Entries are already persisted when added/removed, so this is a no-op
        # But we refresh from database to ensure consistency
        self._load_from_database()


# database/repositories/settings_repository.py - FIXED VERSION
from typing import Optional, Dict, Any
from datetime import datetime
from core.models import MotionRegion
from .base import BaseRepository

class SettingsRepository(BaseRepository):
    def create_table(self):
        with self.db_manager.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS motion_settings (
                    id INTEGER PRIMARY KEY,
                    region_x1 INTEGER,
                    region_y1 INTEGER, 
                    region_x2 INTEGER,
                    region_y2 INTEGER,
                    motion_threshold INTEGER DEFAULT 5000,
                    min_contour_area INTEGER DEFAULT 500,
                    motion_timeout_seconds INTEGER DEFAULT 30,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def save_motion_settings(self, region: MotionRegion, motion_threshold: int, min_contour_area: int, motion_timeout_seconds: int = 30):
        """Save motion detection settings with timeout"""
        with self.db_manager.get_connection() as conn:
            # Clear old settings
            conn.execute('DELETE FROM motion_settings')
            
            # Insert new settings
            conn.execute('''
                INSERT INTO motion_settings (region_x1, region_y1, region_x2, region_y2, 
                                           motion_threshold, min_contour_area, motion_timeout_seconds, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (region.x1, region.y1, region.x2, region.y2, 
                  motion_threshold, min_contour_area, motion_timeout_seconds, datetime.now()))
            
            print(f"💾 Saved motion settings: region=({region.x1},{region.y1},{region.x2},{region.y2}), "
                  f"threshold={motion_threshold}, min_area={min_contour_area}, timeout={motion_timeout_seconds}s")
    
    def load_motion_settings(self) -> Optional[Dict[str, Any]]:
        """Load motion detection settings"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM motion_settings ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            
            if row and all(coord is not None for coord in [row['region_x1'], row['region_y1'], row['region_x2'], row['region_y2']]):
                timeout = 30
                # sqlite3.Row doesn't support `.get`, so check the keys first
                if 'motion_timeout_seconds' in row.keys():
                    timeout = row['motion_timeout_seconds']

                return {
                    'region': MotionRegion(row['region_x1'], row['region_y1'], row['region_x2'], row['region_y2']),
                    'motion_threshold': row['motion_threshold'],
                    'min_contour_area': row['min_contour_area'],
                    'motion_timeout_seconds': timeout,
                    'updated_at': row['updated_at']
                }
        
        return None
    
    def migrate_settings_table(self):
        """Add motion_timeout_seconds column if it doesn't exist (for existing databases)"""
        with self.db_manager.get_connection() as conn:
            try:
                # Check if column exists
                cursor = conn.execute("PRAGMA table_info(motion_settings)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'motion_timeout_seconds' not in columns:
                    print("🔄 Adding motion_timeout_seconds column to existing database...")
                    conn.execute('ALTER TABLE motion_settings ADD COLUMN motion_timeout_seconds INTEGER DEFAULT 30')
                    print("✅ Database migration completed")
                    
            except Exception as e:
                print(f"⚠️ Database migration failed (probably fine if new database): {e}")
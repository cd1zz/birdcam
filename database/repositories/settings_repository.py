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
                    motion_box_enabled INTEGER DEFAULT 1,
                    motion_box_x1 INTEGER DEFAULT 0,
                    motion_box_y1 INTEGER DEFAULT 0,
                    motion_box_x2 INTEGER DEFAULT 640,
                    motion_box_y2 INTEGER DEFAULT 480,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def save_motion_settings(self, region: MotionRegion, motion_threshold: int, min_contour_area: int, motion_timeout_seconds: int = 30, motion_box_enabled: bool = True, motion_box_x1: int = 0, motion_box_y1: int = 0, motion_box_x2: int = 640, motion_box_y2: int = 480):
        """Save motion detection settings with timeout and motion box"""
        with self.db_manager.get_connection() as conn:
            # Clear old settings
            conn.execute('DELETE FROM motion_settings')
            
            # Insert new settings
            conn.execute('''
                INSERT INTO motion_settings (region_x1, region_y1, region_x2, region_y2, 
                                           motion_threshold, min_contour_area, motion_timeout_seconds,
                                           motion_box_enabled, motion_box_x1, motion_box_y1, motion_box_x2, motion_box_y2, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (region.x1, region.y1, region.x2, region.y2, 
                  motion_threshold, min_contour_area, motion_timeout_seconds,
                  int(motion_box_enabled), motion_box_x1, motion_box_y1, motion_box_x2, motion_box_y2, datetime.now()))
            
            print(f"Saved motion settings: region=({region.x1},{region.y1},{region.x2},{region.y2}), "
                  f"threshold={motion_threshold}, min_area={min_contour_area}, timeout={motion_timeout_seconds}s, "
                  f"motion_box_enabled={motion_box_enabled}, box=({motion_box_x1},{motion_box_y1},{motion_box_x2},{motion_box_y2})")
    
    def load_motion_settings(self) -> Optional[Dict[str, Any]]:
        """Load motion detection settings"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM motion_settings ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            
            if row and all(coord is not None for coord in [row['region_x1'], row['region_y1'], row['region_x2'], row['region_y2']]):
                timeout = 30
                motion_box_enabled = True
                motion_box_x1 = 0
                motion_box_y1 = 0
                motion_box_x2 = 640
                motion_box_y2 = 480
                
                # sqlite3.Row doesn't support `.get`, so check the keys first
                if 'motion_timeout_seconds' in row.keys():
                    timeout = row['motion_timeout_seconds']
                if 'motion_box_enabled' in row.keys():
                    motion_box_enabled = bool(row['motion_box_enabled'])
                if 'motion_box_x1' in row.keys():
                    motion_box_x1 = row['motion_box_x1']
                if 'motion_box_y1' in row.keys():
                    motion_box_y1 = row['motion_box_y1']
                if 'motion_box_x2' in row.keys():
                    motion_box_x2 = row['motion_box_x2']
                if 'motion_box_y2' in row.keys():
                    motion_box_y2 = row['motion_box_y2']

                return {
                    'region': MotionRegion(row['region_x1'], row['region_y1'], row['region_x2'], row['region_y2']),
                    'motion_threshold': row['motion_threshold'],
                    'min_contour_area': row['min_contour_area'],
                    'motion_timeout_seconds': timeout,
                    'motion_box_enabled': motion_box_enabled,
                    'motion_box_x1': motion_box_x1,
                    'motion_box_y1': motion_box_y1,
                    'motion_box_x2': motion_box_x2,
                    'motion_box_y2': motion_box_y2,
                    'updated_at': row['updated_at']
                }
        
        return None
    
    def migrate_settings_table(self):
        """Add motion_timeout_seconds and motion box columns if they don't exist (for existing databases)"""
        with self.db_manager.get_connection() as conn:
            try:
                # Check if column exists
                cursor = conn.execute("PRAGMA table_info(motion_settings)")
                columns = [row[1] for row in cursor.fetchall()]
                
                migrations_performed = []
                
                if 'motion_timeout_seconds' not in columns:
                    print("Adding motion_timeout_seconds column to existing database...")
                    conn.execute('ALTER TABLE motion_settings ADD COLUMN motion_timeout_seconds INTEGER DEFAULT 30')
                    migrations_performed.append('motion_timeout_seconds')
                
                if 'motion_box_enabled' not in columns:
                    print("Adding motion box columns to existing database...")
                    conn.execute('ALTER TABLE motion_settings ADD COLUMN motion_box_enabled INTEGER DEFAULT 1')
                    conn.execute('ALTER TABLE motion_settings ADD COLUMN motion_box_x1 INTEGER DEFAULT 0')
                    conn.execute('ALTER TABLE motion_settings ADD COLUMN motion_box_y1 INTEGER DEFAULT 0')
                    conn.execute('ALTER TABLE motion_settings ADD COLUMN motion_box_x2 INTEGER DEFAULT 640')
                    conn.execute('ALTER TABLE motion_settings ADD COLUMN motion_box_y2 INTEGER DEFAULT 480')
                    migrations_performed.append('motion_box columns')
                
                if migrations_performed:
                    print(f"Database schema updated: added {', '.join(migrations_performed)}")
                else:
                    print("Database schema check: all required columns present")
                    
            except Exception as e:
                print(f"Database migration check failed (probably fine if new database): {e}")
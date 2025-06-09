# database/repositories/settings_repository.py
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
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def save_motion_settings(self, region: MotionRegion, motion_threshold: int, min_contour_area: int):
        """Save motion detection settings"""
        with self.db_manager.get_connection() as conn:
            # Clear old settings
            conn.execute('DELETE FROM motion_settings')
            
            # Insert new settings
            conn.execute('''
                INSERT INTO motion_settings (region_x1, region_y1, region_x2, region_y2, 
                                           motion_threshold, min_contour_area, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (region.x1, region.y1, region.x2, region.y2, 
                  motion_threshold, min_contour_area, datetime.now()))
            
            print(f"💾 Saved motion settings: region=({region.x1},{region.y1},{region.x2},{region.y2}), threshold={motion_threshold}")
    
    def load_motion_settings(self) -> Optional[Dict[str, Any]]:
        """Load motion detection settings"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM motion_settings ORDER BY id DESC LIMIT 1')
            row = cursor.fetchone()
            
            if row and all(coord is not None for coord in [row['region_x1'], row['region_y1'], row['region_x2'], row['region_y2']]):
                return {
                    'region': MotionRegion(row['region_x1'], row['region_y1'], row['region_x2'], row['region_y2']),
                    'motion_threshold': row['motion_threshold'],
                    'min_contour_area': row['min_contour_area'],
                    'updated_at': row['updated_at']
                }
        
        return None
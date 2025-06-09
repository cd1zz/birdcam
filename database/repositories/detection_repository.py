# database/repositories/detection_repository.py
from typing import List, Optional
from datetime import datetime
from core.models import BirdDetection
from .base import BaseRepository

class DetectionRepository(BaseRepository):
    def create_table(self):
        with self.db_manager.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    frame_number INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    confidence REAL NOT NULL,
                    bbox_x1 INTEGER NOT NULL,
                    bbox_y1 INTEGER NOT NULL,
                    bbox_x2 INTEGER NOT NULL,
                    bbox_y2 INTEGER NOT NULL,
                    species TEXT DEFAULT 'bird',
                    thumbnail_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (video_id) REFERENCES videos (id)
                )
            ''')
    
    def create(self, detection: BirdDetection) -> int:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO detections (video_id, frame_number, timestamp, confidence,
                                      bbox_x1, bbox_y1, bbox_x2, bbox_y2, species, thumbnail_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                detection.video_id, detection.frame_number, detection.timestamp,
                detection.confidence, *detection.bbox, detection.species, detection.thumbnail_path
            ))
            return cursor.lastrowid
    
    def get_by_video_id(self, video_id: int) -> List[BirdDetection]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM detections WHERE video_id = ?', (video_id,))
            return [self._row_to_detection(row) for row in cursor.fetchall()]
    
    def get_recent_with_thumbnails(self, limit: int = 20) -> List[BirdDetection]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('''
                SELECT d.*, v.filename, v.received_time, v.duration
                FROM detections d
                JOIN videos v ON d.video_id = v.id
                WHERE d.thumbnail_path IS NOT NULL
                ORDER BY v.received_time DESC, d.timestamp DESC
                LIMIT ?
            ''', (limit,))
            return [self._row_to_detection_with_video(row) for row in cursor.fetchall()]
    
    def update_thumbnail_path(self, detection_id: int, thumbnail_path: str):
        with self.db_manager.get_connection() as conn:
            conn.execute('UPDATE detections SET thumbnail_path = ? WHERE id = ?', 
                        (thumbnail_path, detection_id))
    
    def _row_to_detection(self, row) -> BirdDetection:
        return BirdDetection(
            id=row['id'],
            video_id=row['video_id'],
            frame_number=row['frame_number'],
            timestamp=row['timestamp'],
            confidence=row['confidence'],
            bbox=(row['bbox_x1'], row['bbox_y1'], row['bbox_x2'], row['bbox_y2']),
            species=row['species'],
            thumbnail_path=row['thumbnail_path'],
            created_at=datetime.fromisoformat(row['created_at'])
        )
    
    def _row_to_detection_with_video(self, row) -> dict:
        detection = self._row_to_detection(row)
        return {
            'detection': detection,
            'filename': row['filename'],
            'received_time': row['received_time'],
            'duration': row['duration']
        }
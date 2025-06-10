# database/repositories/video_repository.py
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from core.models import VideoFile, ProcessingStatus
from .base import BaseRepository

class VideoRepository(BaseRepository):
    def create_table(self):
        with self.db_manager.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    duration REAL,
                    fps REAL,
                    resolution TEXT,
                    received_time TIMESTAMP NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    processing_time REAL,
                    detection_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def create(self, video: VideoFile) -> int:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO videos (filename, original_filename, file_size, duration, 
                                  fps, resolution, received_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video.filename, video.original_filename, video.file_size,
                video.duration, video.fps, video.resolution, 
                video.received_time, video.status.value
            ))
            return cursor.lastrowid
    
    def get_by_id(self, video_id: int) -> Optional[VideoFile]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
            row = cursor.fetchone()
            return self._row_to_video(row) if row else None
    
    def get_by_filename(self, filename: str) -> Optional[VideoFile]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM videos WHERE filename = ?', (filename,))
            row = cursor.fetchone()
            return self._row_to_video(row) if row else None
    
    def get_pending_videos(self) -> List[VideoFile]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM videos WHERE status = ?', ('pending',))
            return [self._row_to_video(row) for row in cursor.fetchall()]
    
    def update_status(self, video_id: int, status: ProcessingStatus, 
                     processing_time: Optional[float] = None, detection_count: Optional[int] = None):
        fields = ['status = ?']
        values = [status.value]
        
        if processing_time is not None:
            fields.append('processing_time = ?')
            values.append(processing_time)
        
        if detection_count is not None:
            fields.append('detection_count = ?')
            values.append(detection_count)
        
        values.append(video_id)
        
        with self.db_manager.get_connection() as conn:
            conn.execute(f'UPDATE videos SET {", ".join(fields)} WHERE id = ?', values)
    
    def get_total_count(self) -> int:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM videos')
            return cursor.fetchone()[0]
    
    def get_processed_count(self) -> int:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM videos WHERE status = ?', ('completed',))
            return cursor.fetchone()[0]
    
    def get_total_detections(self) -> int:
        """Get total number of detections found across all videos"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT SUM(detection_count) FROM videos WHERE status = ?', ('completed',))
            result = cursor.fetchone()[0]
            return result if result else 0
    
    def get_today_detections(self) -> int:
        """Get number of detections found today"""
        from datetime import date
        today = date.today()
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('''
                SELECT SUM(detection_count) FROM videos 
                WHERE status = ? AND DATE(received_time) = ?
            ''', ('completed', today))
            result = cursor.fetchone()[0]
            return result if result else 0
    
    def get_average_processing_time(self) -> float:
        """Get average processing time for completed videos"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('''
                SELECT AVG(processing_time) FROM videos 
                WHERE status = ? AND processing_time IS NOT NULL
            ''', ('completed',))
            result = cursor.fetchone()[0]
            return round(result, 2) if result else 0.0
    
    def _row_to_video(self, row) -> VideoFile:
        return VideoFile(
            id=row['id'],
            filename=row['filename'],
            original_filename=row['original_filename'],
            file_path=Path(),  # Will be set by service layer
            file_size=row['file_size'],
            duration=row['duration'],
            fps=row['fps'],
            resolution=row['resolution'],
            received_time=datetime.fromisoformat(row['received_time']),
            status=ProcessingStatus(row['status']),
            processing_time=row['processing_time'],
            bird_count=row['detection_count'],  # For backward compatibility
            created_at=datetime.fromisoformat(row['created_at'])
        )
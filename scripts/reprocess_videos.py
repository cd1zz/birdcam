#!/usr/bin/env python3
"""
Reprocess existing videos with updated AI model.
This script safely moves videos back to incoming and resets their database status.
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import load_processing_config

# Simple logging since utils.logger_config might not exist
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reprocess_videos(video_type='all', limit=None):
    """
    Reprocess videos by moving them back to incoming folder and resetting database status.
    
    Args:
        video_type: 'all', 'detections', or 'no_detections'
        limit: Maximum number of videos to reprocess (None for all)
    """
    config = load_processing_config()
    db_path = config.database.path
    base_path = Path(config.processing.storage_path)
    
    incoming_dir = base_path / 'incoming'
    detections_dir = base_path / 'processed' / 'detections'
    no_detections_dir = base_path / 'processed' / 'no_detections'
    
    # Determine which directories to process
    if video_type == 'all':
        source_dirs = [detections_dir, no_detections_dir]
    elif video_type == 'detections':
        source_dirs = [detections_dir]
    elif video_type == 'no_detections':
        source_dirs = [no_detections_dir]
    else:
        raise ValueError("video_type must be 'all', 'detections', or 'no_detections'")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    videos_reprocessed = 0
    
    try:
        for source_dir in source_dirs:
            if not source_dir.exists():
                continue
                
            video_files = list(source_dir.glob('*.mp4'))
            
            for video_file in video_files:
                if limit and videos_reprocessed >= limit:
                    break
                    
                filename = video_file.name
                
                # Check if video exists in database
                cursor.execute("SELECT id, status FROM videos WHERE filename = ?", (filename,))
                result = cursor.fetchone()
                
                if not result:
                    logger.warning(f"Video {filename} not found in database, skipping")
                    continue
                
                video_id, current_status = result
                
                # Delete existing detections for this video
                cursor.execute("DELETE FROM detections WHERE video_id = ?", (video_id,))
                deleted_detections = cursor.rowcount
                
                # Update video status to pending
                cursor.execute("""
                    UPDATE videos 
                    SET status = 'pending', 
                        detection_count = 0,
                        processing_time = NULL
                    WHERE id = ?
                """, (video_id,))
                
                # Move file back to incoming
                dest_path = incoming_dir / filename
                if dest_path.exists():
                    logger.warning(f"File {filename} already exists in incoming, skipping")
                    continue
                
                shutil.move(str(video_file), str(dest_path))
                
                videos_reprocessed += 1
                logger.info(f"Reprocessing {filename}: deleted {deleted_detections} detections, moved to incoming")
        
        conn.commit()
        logger.info(f"Successfully prepared {videos_reprocessed} videos for reprocessing")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during reprocessing: {e}")
        raise
    finally:
        conn.close()
    
    return videos_reprocessed

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Reprocess videos with updated AI model")
    parser.add_argument('--type', choices=['all', 'detections', 'no_detections'], 
                        default='all', help='Which videos to reprocess')
    parser.add_argument('--limit', type=int, help='Maximum number of videos to reprocess')
    parser.add_argument('--dry-run', action='store_true', 
                        help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("DRY RUN MODE - no changes will be made")
        config = load_processing_config()
        base_path = Path(config.processing.storage_path)
        
        detections_dir = base_path / 'processed' / 'detections'
        no_detections_dir = base_path / 'processed' / 'no_detections'
        
        if args.type in ['all', 'detections']:
            detection_videos = len(list(detections_dir.glob('*.mp4')))
            print(f"Videos with detections: {detection_videos}")
        
        if args.type in ['all', 'no_detections']:
            no_detection_videos = len(list(no_detections_dir.glob('*.mp4')))
            print(f"Videos without detections: {no_detection_videos}")
    else:
        try:
            count = reprocess_videos(args.type, args.limit)
            print(f"Successfully prepared {count} videos for reprocessing")
            print("Videos have been moved to incoming folder and will be processed automatically")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
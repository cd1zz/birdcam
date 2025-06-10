#!/usr/bin/env python3
"""
Clean reset script - removes all old videos and databases for fresh start
Works for both Pi (bird_footage) and Processing Server (bird_processing)
Updated for new detections/no_detections structure
"""
import shutil
from pathlib import Path
import os

def clean_processing_server():
    """Clean processing server data"""
    base_path = Path('./bird_processing')
    
    if not base_path.exists():
        print("📁 No bird_processing directory found")
        return False
    
    print("🧹 Cleaning processing server data...")
    
    # Remove entire bird_processing directory
    shutil.rmtree(base_path)
    print(f"🗑️ Removed {base_path}")
    
    # Recreate clean directory structure with new layout
    directories = [
        base_path / "incoming",
        base_path / "processed",
        base_path / "processed" / "detections",      # NEW: Videos WITH detections
        base_path / "processed" / "no_detections",   # NEW: Videos WITHOUT detections
        base_path / "thumbnails"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created {directory}")
    
    return True

def clean_pi_capture():
    """Clean Pi capture data"""
    base_path = Path('./bird_footage')
    
    if not base_path.exists():
        print("📁 No bird_footage directory found")
        return False
    
    print("🧹 Cleaning Pi capture data...")
    
    # Remove the database file
    db_file = base_path / "capture.db"
    if db_file.exists():
        db_file.unlink()
        print(f"🗑️ Removed {db_file}")
    
    # Clean video directories but keep structure
    video_dirs = [
        base_path / "raw_footage",
        base_path / "synced"
    ]
    
    for video_dir in video_dirs:
        if video_dir.exists():
            # Remove all files in the directory
            for file_path in video_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink()
                    print(f"🗑️ Removed {file_path.name}")
            print(f"🧹 Cleaned {video_dir}")
        else:
            # Create directory if it doesn't exist
            video_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created {video_dir}")
    
    return True

def clean_reset():
    """Detect and clean appropriate system"""
    processing_cleaned = clean_processing_server()
    pi_cleaned = clean_pi_capture()
    
    if processing_cleaned and pi_cleaned:
        system_type = "Processing Server + Pi Capture"
    elif processing_cleaned:
        system_type = "Processing Server"
    elif pi_cleaned:
        system_type = "Pi Capture"
    else:
        print("❌ No bird system directories found!")
        return
    
    print(f"✅ Clean reset complete for: {system_type}")
    print("🚀 Ready for fresh data with:")
    print("   📂 detections/ and no_detections/ directories")
    print("   🎬 H.264 video conversion")
    print("   🎯 Multi-animal detection support")
    print("   ⚙️ .env configuration")

if __name__ == '__main__':
    print("🧹 Animal Detection System - Clean Reset")
    print("This will remove ALL old videos and database data.")
    print("")
    print("📂 New directory structure:")
    print("   bird_processing/processed/detections/     (videos WITH animals)")
    print("   bird_processing/processed/no_detections/  (videos WITHOUT animals)")
    print("")
    
    confirm = input("Are you sure you want to proceed? (yes/no): ").lower().strip()
    
    if confirm in ['yes', 'y']:
        clean_reset()
    else:
        print("❌ Reset cancelled")
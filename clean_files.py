#!/usr/bin/env python3
"""
Clean reset script - removes all old videos and databases for fresh start
"""
import shutil
from pathlib import Path

def clean_reset():
    """Remove all old data and start fresh"""
    base_path = Path('./bird_processing')
    
    if not base_path.exists():
        print("📁 No bird_processing directory found - already clean!")
        return
    
    print("🧹 Cleaning up old data...")
    
    # Remove entire bird_processing directory
    if base_path.exists():
        shutil.rmtree(base_path)
        print(f"🗑️ Removed {base_path}")
    
    # Recreate clean directory structure
    directories = [
        base_path / "incoming",
        base_path / "processed", 
        base_path / "thumbnails"
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"📁 Created {directory}")
    
    print("✅ Clean reset complete!")
    print("🚀 Ready for fresh videos with H.264 conversion")

if __name__ == '__main__':
    print("🧹 Bird Processing System - Clean Reset")
    print("This will remove ALL old videos and database data.")
    
    confirm = input("Are you sure you want to proceed? (yes/no): ").lower().strip()
    
    if confirm in ['yes', 'y']:
        clean_reset()
    else:
        print("❌ Reset cancelled")
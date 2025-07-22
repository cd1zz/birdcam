# database/connection.py
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

# Alias for backward compatibility with new code
class DatabaseConnection(DatabaseManager):
    """Database connection that auto-loads config path"""
    def __init__(self, db_path: Path = None):
        if db_path is None:
            # Auto-load from config
            from config.settings import load_processing_config
            config = load_processing_config()
            db_path = config.database.path
        super().__init__(db_path)


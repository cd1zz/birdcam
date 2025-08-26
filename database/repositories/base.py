# database/repositories/base.py
from abc import ABC, abstractmethod
from database.connection import DatabaseManager

class BaseRepository(ABC):
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    @abstractmethod
    def create_table(self):
        pass
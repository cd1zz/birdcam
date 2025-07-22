# database/repositories/registration_repository.py
from typing import List, Optional
from datetime import datetime
from core.registration_models import RegistrationLink, RegistrationLinkType
from .base import BaseRepository

class RegistrationRepository(BaseRepository):
    def create_table(self):
        with self.db_manager.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS registration_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT NOT NULL UNIQUE,
                    link_type TEXT NOT NULL,
                    max_uses INTEGER,
                    uses INTEGER NOT NULL DEFAULT 0,
                    expires_at TIMESTAMP,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    CHECK (link_type IN ('single_use', 'multi_use')),
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            ''')
            # Create index for faster token lookups
            conn.execute('CREATE INDEX IF NOT EXISTS idx_registration_token ON registration_links(token)')
    
    def create(self, link: RegistrationLink) -> int:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO registration_links 
                (token, link_type, max_uses, uses, expires_at, created_by, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                link.token,
                link.link_type.value,
                link.max_uses,
                link.uses,
                link.expires_at,
                link.created_by,
                link.is_active
            ))
            return cursor.lastrowid
    
    def get_by_token(self, token: str) -> Optional[RegistrationLink]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM registration_links WHERE token = ? AND is_active = 1',
                (token,)
            )
            row = cursor.fetchone()
            return self._row_to_link(row) if row else None
    
    def get_by_id(self, link_id: int) -> Optional[RegistrationLink]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM registration_links WHERE id = ?', (link_id,))
            row = cursor.fetchone()
            return self._row_to_link(row) if row else None
    
    def get_all_active(self) -> List[RegistrationLink]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM registration_links WHERE is_active = 1 ORDER BY created_at DESC'
            )
            return [self._row_to_link(row) for row in cursor.fetchall()]
    
    def get_by_creator(self, user_id: int) -> List[RegistrationLink]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM registration_links WHERE created_by = ? ORDER BY created_at DESC',
                (user_id,)
            )
            return [self._row_to_link(row) for row in cursor.fetchall()]
    
    def increment_uses(self, link_id: int):
        with self.db_manager.get_connection() as conn:
            conn.execute(
                'UPDATE registration_links SET uses = uses + 1 WHERE id = ?',
                (link_id,)
            )
    
    def deactivate(self, link_id: int):
        with self.db_manager.get_connection() as conn:
            conn.execute(
                'UPDATE registration_links SET is_active = 0 WHERE id = ?',
                (link_id,)
            )
    
    def cleanup_expired(self):
        """Deactivate expired links"""
        with self.db_manager.get_connection() as conn:
            conn.execute(
                'UPDATE registration_links SET is_active = 0 WHERE expires_at < ? AND is_active = 1',
                (datetime.now(),)
            )
    
    def _row_to_link(self, row) -> RegistrationLink:
        return RegistrationLink(
            id=row['id'],
            token=row['token'],
            link_type=RegistrationLinkType(row['link_type']),
            max_uses=row['max_uses'],
            uses=row['uses'],
            expires_at=datetime.fromisoformat(row['expires_at']) if row['expires_at'] else None,
            created_by=row['created_by'],
            created_at=datetime.fromisoformat(row['created_at']),
            is_active=bool(row['is_active'])
        )
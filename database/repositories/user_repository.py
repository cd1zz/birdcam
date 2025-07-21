# database/repositories/user_repository.py
from typing import List, Optional
from datetime import datetime
from core.models import User, UserRole
from .base import BaseRepository

class UserRepository(BaseRepository):
    def create_table(self):
        with self.db_manager.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    CHECK (role IN ('admin', 'viewer'))
                )
            ''')
            # Create index on username for faster lookups
            conn.execute('CREATE INDEX IF NOT EXISTS idx_username ON users(username)')
    
    def create(self, user: User) -> int:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO users (username, password_hash, role, is_active)
                VALUES (?, ?, ?, ?)
            ''', (
                user.username.lower(), 
                user.password_hash, 
                user.role.value,
                user.is_active
            ))
            return cursor.lastrowid
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
    
    def get_by_username(self, username: str) -> Optional[User]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM users WHERE LOWER(username) = LOWER(?)', (username,))
            row = cursor.fetchone()
            return self._row_to_user(row) if row else None
    
    def get_all(self) -> List[User]:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM users ORDER BY created_at DESC')
            return [self._row_to_user(row) for row in cursor.fetchall()]
    
    def update(self, user: User):
        with self.db_manager.get_connection() as conn:
            conn.execute('''
                UPDATE users 
                SET password_hash = ?, role = ?, is_active = ?, last_login = ?
                WHERE id = ?
            ''', (
                user.password_hash,
                user.role.value,
                user.is_active,
                user.last_login,
                user.id
            ))
    
    def update_last_login(self, user_id: int):
        with self.db_manager.get_connection() as conn:
            conn.execute(
                'UPDATE users SET last_login = ? WHERE id = ?',
                (datetime.now(), user_id)
            )
    
    def delete(self, user_id: int):
        with self.db_manager.get_connection() as conn:
            conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    def deactivate(self, user_id: int):
        with self.db_manager.get_connection() as conn:
            conn.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
    
    def count_by_role(self, role: UserRole) -> int:
        with self.db_manager.get_connection() as conn:
            cursor = conn.execute(
                'SELECT COUNT(*) FROM users WHERE role = ? AND is_active = 1',
                (role.value,)
            )
            return cursor.fetchone()[0]
    
    def _row_to_user(self, row) -> User:
        return User(
            id=row['id'],
            username=row['username'],
            password_hash=row['password_hash'],
            role=UserRole(row['role']),
            is_active=bool(row['is_active']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None
        )
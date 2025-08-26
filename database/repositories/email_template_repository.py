# database/repositories/email_template_repository.py
from typing import List, Optional
from datetime import datetime
from core.email_template_model import EmailTemplate, EmailTemplateType, DEFAULT_TEMPLATES
from database.connection import DatabaseConnection
from database.repositories.base import BaseRepository
from utils.capture_logger import logger

class EmailTemplateRepository(BaseRepository):
    def __init__(self, db_connection: DatabaseConnection):
        super().__init__(db_connection)
        self.create_table()
    
    def create_table(self):
        """Create email_templates table if it doesn't exist"""
        with self.db_manager.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS email_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_type TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    body_html TEXT NOT NULL,
                    variables TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
        
        # Insert default templates if they don't exist
        self._insert_default_templates()
    
    def _insert_default_templates(self):
        """Insert default templates if they don't exist"""
        for template_type, template_data in DEFAULT_TEMPLATES.items():
            existing = self.get_by_type(template_type)
            if not existing:
                template = EmailTemplate(
                    template_type=template_type,
                    subject=template_data['subject'],
                    body_text=template_data['body_text'],
                    body_html=template_data['body_html'],
                    variables=template_data['variables'],
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.create(template)
                logger.info(f"[EMAIL_TEMPLATES] Created default template: {template_type.value}")
    
    def create(self, template: EmailTemplate) -> Optional[EmailTemplate]:
        """Create a new email template"""
        query = """
        INSERT INTO email_templates 
        (template_type, subject, body_text, body_html, variables, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        now = datetime.now()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (
                    template.template_type.value,
                    template.subject,
                    template.body_text,
                    template.body_html,
                    template.variables,
                    template.is_active,
                    now.isoformat(),
                    now.isoformat()
                )
            )
            template_id = cursor.lastrowid
            
            if template_id:
                template.id = template_id
                template.created_at = now
                template.updated_at = now
                return template
        return None
    
    def get_by_type(self, template_type: EmailTemplateType) -> Optional[EmailTemplate]:
        """Get template by type"""
        query = """
        SELECT id, template_type, subject, body_text, body_html, variables, 
               is_active, created_at, updated_at
        FROM email_templates
        WHERE template_type = ?
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (template_type.value,))
            result = cursor.fetchone()
            return EmailTemplate.from_row(result) if result else None
    
    def get_active_by_type(self, template_type: EmailTemplateType) -> Optional[EmailTemplate]:
        """Get active template by type"""
        query = """
        SELECT id, template_type, subject, body_text, body_html, variables, 
               is_active, created_at, updated_at
        FROM email_templates
        WHERE template_type = ? AND is_active = 1
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (template_type.value,))
            result = cursor.fetchone()
            return EmailTemplate.from_row(result) if result else None
    
    def get_all(self) -> List[EmailTemplate]:
        """Get all templates"""
        query = """
        SELECT id, template_type, subject, body_text, body_html, variables, 
               is_active, created_at, updated_at
        FROM email_templates
        ORDER BY template_type
        """
        
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            return [EmailTemplate.from_row(row) for row in results]
    
    def update(self, template: EmailTemplate) -> bool:
        """Update an email template"""
        query = """
        UPDATE email_templates
        SET subject = ?, body_text = ?, body_html = ?, variables = ?, 
            is_active = ?, updated_at = ?
        WHERE id = ?
        """
        
        now = datetime.now()
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (
                    template.subject,
                    template.body_text,
                    template.body_html,
                    template.variables,
                    template.is_active,
                    now.isoformat(),
                    template.id
                )
            )
            rows_affected = cursor.rowcount
            
            if rows_affected:
                template.updated_at = now
                return True
        return False
    
    def delete(self, template_id: int) -> bool:
        """Delete a template (not recommended for default templates)"""
        query = "DELETE FROM email_templates WHERE id = ?"
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (template_id,))
            return cursor.rowcount > 0
    
    def reset_to_default(self, template_type: EmailTemplateType) -> Optional[EmailTemplate]:
        """Reset a template to its default values"""
        if template_type in DEFAULT_TEMPLATES:
            template_data = DEFAULT_TEMPLATES[template_type]
            existing = self.get_by_type(template_type)
            
            if existing:
                existing.subject = template_data['subject']
                existing.body_text = template_data['body_text']
                existing.body_html = template_data['body_html']
                existing.variables = template_data['variables']
                existing.is_active = True
                
                if self.update(existing):
                    logger.info(f"[EMAIL_TEMPLATES] Reset template to default: {template_type.value}")
                    return existing
            else:
                # Create new default template
                template = EmailTemplate(
                    template_type=template_type,
                    subject=template_data['subject'],
                    body_text=template_data['body_text'],
                    body_html=template_data['body_html'],
                    variables=template_data['variables'],
                    is_active=True
                )
                return self.create(template)
        
        return None
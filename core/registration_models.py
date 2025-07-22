# core/registration_models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class RegistrationLinkType(Enum):
    SINGLE_USE = "single_use"
    MULTI_USE = "multi_use"

@dataclass
class RegistrationLink:
    id: Optional[int]
    token: str
    link_type: RegistrationLinkType
    max_uses: Optional[int]  # None for unlimited
    uses: int
    expires_at: Optional[datetime]
    created_by: int  # User ID who created the link
    created_at: datetime
    is_active: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
    
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        if not self.is_active or self.is_expired:
            return False
        
        if self.link_type == RegistrationLinkType.SINGLE_USE and self.uses > 0:
            return False
        
        if self.max_uses is not None and self.uses >= self.max_uses:
            return False
        
        return True
    
    @property
    def remaining_uses(self) -> Optional[int]:
        if self.max_uses is None:
            return None
        return max(0, self.max_uses - self.uses)
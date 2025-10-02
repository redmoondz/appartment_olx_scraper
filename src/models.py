"""Data models for apartment listings"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
import json


@dataclass
class Apartment:
    """Apartment listing data model"""
    
    post_id: str
    name: str
    price: float
    currency: str
    location: str
    description: str
    contact_phone: Optional[str] = None
    photos: List[str] = field(default_factory=list)
    created_date: Optional[str] = None
    watch_count: Optional[int] = None
    tags: List[str] = field(default_factory=list)
    url: str = ""
    
    # Additional fields
    total_area: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    rooms: Optional[int] = None
    district: Optional[str] = None
    furnished: Optional[bool] = None
    
    # Metadata
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert lists to JSON strings for CSV compatibility
        if data['photos']:
            data['photos'] = json.dumps(data['photos'])
        if data['tags']:
            data['tags'] = json.dumps(data['tags'])
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Apartment":
        """Create from dictionary"""
        # Parse JSON strings back to lists
        if isinstance(data.get('photos'), str):
            try:
                data['photos'] = json.loads(data['photos'])
            except (json.JSONDecodeError, TypeError):
                data['photos'] = []
        
        if isinstance(data.get('tags'), str):
            try:
                data['tags'] = json.loads(data['tags'])
            except (json.JSONDecodeError, TypeError):
                data['tags'] = []
        
        return cls(**data)
    
    def __hash__(self):
        """Make hashable based on post_id"""
        return hash(self.post_id)
    
    def __eq__(self, other):
        """Check equality based on post_id"""
        if isinstance(other, Apartment):
            return self.post_id == other.post_id
        return False

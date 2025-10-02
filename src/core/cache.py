"""Cache manager for apartment listings"""
import csv
from pathlib import Path
from typing import List, Set, Optional
import pandas as pd

from src.models import Apartment
from src.utils.logger import get_logger


class CacheManager:
    """Manager for caching apartment listings"""
    
    def __init__(self, cache_path: Path):
        """
        Initialize cache manager
        
        Args:
            cache_path: Path to cache file
        """
        self.cache_path = cache_path
        self.logger = get_logger()
        self._ensure_cache_exists()
    
    def _ensure_cache_exists(self):
        """Ensure cache file and directory exist"""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.cache_path.exists():
            # Create empty cache file with headers
            self._write_apartments([])
            self.logger.info(f"Created new cache file: {self.cache_path}")
    
    def load_cached_apartments(self) -> List[Apartment]:
        """
        Load apartments from cache
        
        Returns:
            List of cached apartments
        """
        try:
            if not self.cache_path.exists() or self.cache_path.stat().st_size == 0:
                return []
            
            df = pd.read_csv(self.cache_path)
            apartments = [Apartment.from_dict(row.to_dict()) for _, row in df.iterrows()]
            
            self.logger.info(f"Loaded {len(apartments)} apartments from cache")
            return apartments
            
        except Exception as e:
            self.logger.error(f"Error loading cache: {e}", exc_info=True)
            return []
    
    def get_cached_ids(self) -> Set[str]:
        """
        Get set of cached apartment IDs
        
        Returns:
            Set of apartment post IDs
        """
        apartments = self.load_cached_apartments()
        return {apt.post_id for apt in apartments}
    
    def save_apartments(self, apartments: List[Apartment], append: bool = False):
        """
        Save apartments to cache
        
        Args:
            apartments: List of apartments to save
            append: Whether to append to existing cache
        """
        try:
            if not apartments:
                self.logger.warning("No apartments to save")
                return
            
            if append:
                # Load existing and merge
                existing = self.load_cached_apartments()
                existing_dict = {apt.post_id: apt for apt in existing}
                
                # Update with new apartments
                for apt in apartments:
                    existing_dict[apt.post_id] = apt
                
                apartments = list(existing_dict.values())
                self.logger.info(f"Merged {len(apartments)} total apartments")
            
            self._write_apartments(apartments)
            self.logger.info(f"Saved {len(apartments)} apartments to cache")
            
        except Exception as e:
            self.logger.error(f"Error saving to cache: {e}", exc_info=True)
    
    def _write_apartments(self, apartments: List[Apartment]):
        """Write apartments to CSV file"""
        if not apartments:
            # Write empty file with headers only
            df = pd.DataFrame(columns=[
                'post_id', 'name', 'price', 'currency', 'location', 'description',
                'contact_phone', 'photos', 'created_date', 'watch_count', 'tags',
                'url', 'total_area', 'floor', 'total_floors', 'rooms', 'district',
                'furnished', 'scraped_at'
            ])
        else:
            data = [apt.to_dict() for apt in apartments]
            df = pd.DataFrame(data)
        
        df.to_csv(self.cache_path, index=False, encoding='utf-8')
    
    def find_new_apartments(
        self,
        current_apartments: List[Apartment],
        cached_apartments: Optional[List[Apartment]] = None
    ) -> List[Apartment]:
        """
        Find new apartments compared to cache
        
        Args:
            current_apartments: Current scraped apartments
            cached_apartments: Previously cached apartments (loaded if None)
            
        Returns:
            List of new apartments
        """
        if cached_apartments is None:
            cached_apartments = self.load_cached_apartments()
        
        cached_ids = {apt.post_id for apt in cached_apartments}
        new_apartments = [apt for apt in current_apartments if apt.post_id not in cached_ids]
        
        self.logger.info(f"Found {len(new_apartments)} new apartments")
        return new_apartments
    
    def export_to_csv(self, output_path: Path, apartments: Optional[List[Apartment]] = None):
        """
        Export apartments to CSV file
        
        Args:
            output_path: Output file path
            apartments: Apartments to export (loaded from cache if None)
        """
        try:
            if apartments is None:
                apartments = self.load_cached_apartments()
            
            if not apartments:
                self.logger.warning("No apartments to export")
                return
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = [apt.to_dict() for apt in apartments]
            df = pd.DataFrame(data)
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            self.logger.info(f"Exported {len(apartments)} apartments to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}", exc_info=True)
    
    def get_statistics(self) -> dict:
        """
        Get statistics about cached apartments
        
        Returns:
            Dictionary with statistics
        """
        apartments = self.load_cached_apartments()
        
        if not apartments:
            return {
                'total': 0,
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0,
                'locations': []
            }
        
        prices = [apt.price for apt in apartments if apt.price > 0]
        locations = list(set(apt.location for apt in apartments if apt.location))
        
        return {
            'total': len(apartments),
            'avg_price': sum(prices) / len(prices) if prices else 0,
            'min_price': min(prices) if prices else 0,
            'max_price': max(prices) if prices else 0,
            'locations': locations
        }

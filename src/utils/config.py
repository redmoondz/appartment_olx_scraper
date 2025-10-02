"""Configuration management module"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


@dataclass
class ScraperConfig:
    """Scraper configuration settings"""
    
    # URLs
    base_url: str
    search_url: str
    
    # Rate limiting
    min_requests_per_minute: int
    max_requests_per_minute: int
    default_requests_per_minute: int
    
    # Delays
    min_delay: float
    max_delay: float
    
    # Retry settings
    max_retries: int
    retry_delay: int
    
    # Cache settings
    cache_dir: str
    cache_file: str
    
    # Logging
    log_dir: str
    log_level: str
    log_max_bytes: int
    log_backup_count: int
    
    # Data export
    data_dir: str
    export_format: str
    
    # Concurrency
    max_workers: int
    
    # User Agent
    user_agent: str
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "ScraperConfig":
        """Load configuration from environment variables"""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        return cls(
            base_url=os.getenv("BASE_URL", "https://www.olx.ua"),
            search_url=os.getenv("SEARCH_URL", "https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/dnepr/"),
            min_requests_per_minute=int(os.getenv("MIN_REQUESTS_PER_MINUTE", "10")),
            max_requests_per_minute=int(os.getenv("MAX_REQUESTS_PER_MINUTE", "60")),
            default_requests_per_minute=int(os.getenv("DEFAULT_REQUESTS_PER_MINUTE", "30")),
            min_delay=float(os.getenv("MIN_DELAY", "1")),
            max_delay=float(os.getenv("MAX_DELAY", "3")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=int(os.getenv("RETRY_DELAY", "5")),
            cache_dir=os.getenv("CACHE_DIR", "cache"),
            cache_file=os.getenv("CACHE_FILE", "apartments_cache.csv"),
            log_dir=os.getenv("LOG_DIR", "logs"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_max_bytes=int(os.getenv("LOG_MAX_BYTES", "10485760")),
            log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
            data_dir=os.getenv("DATA_DIR", "data"),
            export_format=os.getenv("EXPORT_FORMAT", "csv"),
            max_workers=int(os.getenv("MAX_WORKERS", "5")),
            user_agent=os.getenv("USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0")
        )
    
    def get_cache_path(self) -> Path:
        """Get full path to cache file"""
        return Path(self.cache_dir) / self.cache_file
    
    def ensure_directories(self):
        """Create necessary directories"""
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

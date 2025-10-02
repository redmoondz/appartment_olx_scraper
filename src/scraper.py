"""Main scraper orchestrator"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn
from rich.table import Table

from src.core.olx_api import OLXClient
from src.core.cache import CacheManager
from src.models import Apartment
from src.utils.config import ScraperConfig
from src.utils.logger import setup_logger, get_logger


class ApartmentScraper:
    """Main apartment scraper orchestrator"""
    
    def __init__(self, config: ScraperConfig):
        """
        Initialize scraper
        
        Args:
            config: Scraper configuration
        """
        self.config = config
        config.ensure_directories()
        
        # Setup logging
        self.logger = setup_logger(
            log_dir=config.log_dir,
            log_level=config.log_level,
            max_bytes=config.log_max_bytes,
            backup_count=config.log_backup_count
        )
        
        # Initialize components
        self.cache_manager = CacheManager(config.get_cache_path())
        self.console = Console()
        
    async def run(
        self,
        search_url: Optional[str] = None,
        max_pages: Optional[int] = None,
        save_new_only: bool = False,
        enrich_data: bool = True,
        fetch_phones: bool = False
    ) -> List[Apartment]:
        """
        Run scraper
        
        Args:
            search_url: URL to scrape (uses config default if None)
            max_pages: Maximum pages to scrape
            save_new_only: Only save new apartments not in cache
            enrich_data: Fetch detailed information from each apartment page
            fetch_phones: Fetch contact phone numbers (requires more API calls)
            
        Returns:
            List of scraped apartments
        """
        url = search_url or self.config.search_url
        
        self.logger.info(f"Starting scraper for URL: {url}")
        self.logger.info(f"Max pages: {max_pages or 'unlimited'}")
        self.logger.info(f"Enrich data: {enrich_data}, Fetch phones: {fetch_phones}")
        
        # Incremental save callback
        async def save_page_callback(apartments, page_num):
            """Save apartments after each page"""
            try:
                self.cache_manager.save_apartments(apartments, append=True)
                self.logger.debug(f"Saved page {page_num} apartments incrementally")
            except Exception as e:
                self.logger.error(f"Error in incremental save: {e}")
        
        # Initialize client
        async with OLXClient(
            base_url=self.config.base_url,
            user_agent=self.config.user_agent,
            min_delay=self.config.min_delay,
            max_delay=self.config.max_delay,
            max_retries=self.config.max_retries
        ) as client:
            
            # Scrape apartments
            with Progress(
                SpinnerColumn(),
                *Progress.get_default_columns(),
                TimeElapsedColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task("[cyan]Scraping apartments...", total=None)
                
                apartments = await client.scrape_all_pages(
                    url, 
                    max_pages,
                    enrich_data=enrich_data,
                    fetch_phones=fetch_phones,
                    page_callback=save_page_callback  # Enable incremental saving
                )
                
                progress.update(task, completed=True)
            
            # Process results
            if save_new_only:
                new_apartments = self.cache_manager.find_new_apartments(apartments)
                self.console.print(f"\n[green]Found {len(new_apartments)} new apartments[/green]")
                
                if new_apartments:
                    # Already saved incrementally, just display
                    self._display_apartments_table(new_apartments, "New Apartments")
                    return new_apartments
                else:
                    self.console.print("[yellow]No new apartments found[/yellow]")
                    return []
            else:
                # Already saved incrementally during scraping
                self.console.print(f"\n[green]Scraped and saved {len(apartments)} apartments[/green]")
                return apartments
    
    def _display_apartments_table(self, apartments: List[Apartment], title: str = "Apartments"):
        """Display apartments in a table"""
        table = Table(title=title)
        
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Price", justify="right", style="green")
        table.add_column("Location", style="yellow")
        table.add_column("Area", justify="right", style="blue")
        
        for apt in apartments[:20]:  # Show first 20
            table.add_row(
                apt.post_id[:10],
                apt.name[:40] + "..." if len(apt.name) > 40 else apt.name,
                f"{apt.price:.0f} {apt.currency}",
                apt.location[:30] if apt.location else "N/A",
                f"{apt.total_area:.1f} м²" if apt.total_area else "N/A"
            )
        
        if len(apartments) > 20:
            table.add_row("...", "...", "...", "...", "...")
        
        self.console.print(table)
    
    def display_statistics(self):
        """Display cache statistics"""
        stats = self.cache_manager.get_statistics()
        
        table = Table(title="Cache Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Total Apartments", str(stats['total']))
        table.add_row("Average Price", f"{stats['avg_price']:.2f} UAH")
        table.add_row("Min Price", f"{stats['min_price']:.2f} UAH")
        table.add_row("Max Price", f"{stats['max_price']:.2f} UAH")
        table.add_row("Unique Locations", str(len(stats['locations'])))
        
        self.console.print(table)
    
    def export_data(self, output_file: Optional[str] = None):
        """Export cached data to file"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"apartments_{timestamp}.csv"
        
        output_path = Path(self.config.data_dir) / output_file
        self.cache_manager.export_to_csv(output_path)
        
        self.console.print(f"[green]Data exported to {output_path}[/green]")


async def main():
    """Main entry point for testing"""
    config = ScraperConfig.from_env()
    scraper = ApartmentScraper(config)
    
    apartments = await scraper.run(max_pages=2, save_new_only=True)
    scraper.display_statistics()


if __name__ == "__main__":
    asyncio.run(main())

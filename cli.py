#!/usr/bin/env python3
"""CLI interface for OLX apartment scraper"""
import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console

from src.scraper import ApartmentScraper
from src.utils.config import ScraperConfig


console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """OLX Apartment Scraper - Async scraper for OLX apartment listings"""
    pass


@cli.command()
@click.option(
    '--url',
    '-u',
    help='Custom search URL to scrape',
    default=None
)
@click.option(
    '--pages',
    '-p',
    type=int,
    help='Maximum number of pages to scrape',
    default=None
)
@click.option(
    '--new-only',
    '-n',
    is_flag=True,
    help='Only save new apartments not in cache'
)
@click.option(
    '--aggression',
    '-a',
    type=click.IntRange(1, 10),
    default=5,
    help='Scraping aggressiveness (1=slow, 10=fast)'
)
@click.option(
    '--no-details',
    is_flag=True,
    help='Skip fetching detailed information from each apartment page'
)
@click.option(
    '--fetch-phones',
    is_flag=True,
    help='Fetch contact phone numbers (slower, more API calls)'
)
@click.option(
    '--config',
    '-c',
    type=click.Path(exists=True),
    help='Path to .env configuration file'
)
def scrape(url, pages, new_only, aggression, no_details, fetch_phones, config):
    """
    Scrape apartment listings from OLX
    
    Examples:
        olx-scraper scrape                    # Scrape with default settings
        olx-scraper scrape -p 5               # Scrape first 5 pages
        olx-scraper scrape -n                 # Only save new apartments
        olx-scraper scrape -a 8               # Faster scraping
        olx-scraper scrape --fetch-phones     # Include phone numbers
        olx-scraper scrape --no-details       # Skip detailed info (faster)
    """
    # Load configuration
    cfg = ScraperConfig.from_env(config)
    
    # Adjust delays based on aggression level
    # aggression 1 = slowest, 10 = fastest
    delay_range = cfg.max_delay - cfg.min_delay
    cfg.min_delay = cfg.min_delay + (delay_range * (10 - aggression) / 10)
    cfg.max_delay = cfg.max_delay - (delay_range * (aggression - 1) / 10)
    
    console.print(f"[cyan]Starting scraper with aggression level: {aggression}[/cyan]")
    console.print(f"[cyan]Delay between requests: {cfg.min_delay:.2f}s - {cfg.max_delay:.2f}s[/cyan]")
    console.print(f"[cyan]Fetch detailed info: {not no_details}, Fetch phones: {fetch_phones}[/cyan]")
    
    # Run scraper
    scraper = ApartmentScraper(cfg)
    
    try:
        apartments = asyncio.run(scraper.run(
            search_url=url,
            max_pages=pages,
            save_new_only=new_only,
            enrich_data=not no_details,
            fetch_phones=fetch_phones
        ))
        
        if apartments:
            console.print(f"\n[green]✓ Successfully scraped {len(apartments)} apartments[/green]")
        else:
            console.print("\n[yellow]⚠ No apartments found[/yellow]")
            
    except KeyboardInterrupt:
        console.print("\n[red]✗ Scraping interrupted by user[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Error during scraping: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    '--config',
    '-c',
    type=click.Path(exists=True),
    help='Path to .env configuration file'
)
def stats(config):
    """
    Show statistics about cached apartments
    
    Example:
        olx-scraper stats
    """
    cfg = ScraperConfig.from_env(config)
    scraper = ApartmentScraper(cfg)
    
    try:
        scraper.display_statistics()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    '--output',
    '-o',
    help='Output file name (default: apartments_TIMESTAMP.csv)',
    default=None
)
@click.option(
    '--config',
    '-c',
    type=click.Path(exists=True),
    help='Path to .env configuration file'
)
def export(output, config):
    """
    Export cached apartments to CSV file
    
    Examples:
        olx-scraper export                    # Export with timestamp
        olx-scraper export -o my_data.csv     # Export to specific file
    """
    cfg = ScraperConfig.from_env(config)
    scraper = ApartmentScraper(cfg)
    
    try:
        scraper.export_data(output)
        console.print("[green]✓ Export completed[/green]")
    except Exception as e:
        console.print(f"[red]✗ Error during export: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option(
    '--config',
    '-c',
    type=click.Path(exists=True),
    help='Path to .env configuration file'
)
def clear_cache(config):
    """
    Clear the apartment cache
    
    Example:
        olx-scraper clear-cache
    """
    cfg = ScraperConfig.from_env(config)
    cache_path = cfg.get_cache_path()
    
    if not cache_path.exists():
        console.print("[yellow]Cache is already empty[/yellow]")
        return
    
    if click.confirm('Are you sure you want to clear the cache?'):
        try:
            cache_path.unlink()
            console.print("[green]✓ Cache cleared successfully[/green]")
        except Exception as e:
            console.print(f"[red]✗ Error clearing cache: {e}[/red]")
            sys.exit(1)
    else:
        console.print("[yellow]Cancelled[/yellow]")


@cli.command()
def init():
    """
    Initialize configuration file (.env)
    
    Example:
        olx-scraper init
    """
    env_file = Path('.env')
    env_example = Path('.env.example')
    
    if env_file.exists():
        if not click.confirm('.env file already exists. Overwrite?'):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    if env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        console.print("[green]✓ Configuration file created: .env[/green]")
        console.print("[cyan]Edit .env to customize your settings[/cyan]")
    else:
        console.print("[red]✗ .env.example not found[/red]")
        sys.exit(1)


if __name__ == '__main__':
    cli()

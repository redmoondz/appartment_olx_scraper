"""Example usage scripts for OLX Apartment Scraper"""

# Example 1: Basic scraping
"""
python main.py scrape
"""

# Example 2: Scrape first 5 pages with new apartments only
"""
python main.py scrape -p 5 -n
"""

# Example 3: Fast scraping with high aggression
"""
python main.py scrape -a 9 -p 10
"""

# Example 4: Custom URL with moderate speed
"""
python main.py scrape \
  --url "https://www.olx.ua/uk/nedvizhimost/kvartiry/dolgosrochnaya-arenda-kvartir/kiev/" \
  --aggression 5 \
  --pages 20
"""

# Example 5: Daily monitoring for new apartments
"""
# Run this as a daily cron job
python main.py scrape -n -a 4 && python main.py export -o daily_$(date +%Y%m%d).csv
"""

# Example 6: Full workflow
"""
# Initial full scrape
python main.py scrape -a 5

# View statistics
python main.py stats

# Export to specific file
python main.py export -o my_apartments.csv

# Next day - check for new ones
python main.py scrape -n -a 6

# Export new results
python main.py export -o new_apartments.csv
"""

# Example 7: Using with cron for automation
"""
# Add to crontab (crontab -e):
# Run every day at 10:00 AM
0 10 * * * cd /path/to/appartment_scraper && /path/to/venv/bin/python main.py scrape -n -a 5

# Run every 6 hours
0 */6 * * * cd /path/to/appartment_scraper && /path/to/venv/bin/python main.py scrape -n -a 4
"""

# Example 8: Python script integration
"""
import asyncio
from src.scraper import ApartmentScraper
from src.utils.config import ScraperConfig

async def custom_scrape():
    config = ScraperConfig.from_env()
    config.min_delay = 2.0
    config.max_delay = 4.0
    
    scraper = ApartmentScraper(config)
    
    # Scrape with custom settings
    apartments = await scraper.run(
        max_pages=10,
        save_new_only=True
    )
    
    # Process apartments
    for apt in apartments:
        if apt.price < 15000 and apt.total_area and apt.total_area > 45:
            print(f"Found: {apt.name} - {apt.price} UAH - {apt.total_area} m²")
    
    return apartments

if __name__ == "__main__":
    apartments = asyncio.run(custom_scrape())
"""

# Example 9: Filtering apartments programmatically
"""
import pandas as pd
from pathlib import Path

# Load cache
df = pd.read_csv('cache/apartments_cache.csv')

# Filter by criteria
filtered = df[
    (df['price'] >= 10000) & 
    (df['price'] <= 15000) &
    (df['total_area'] >= 40) &
    (df['total_area'] <= 60) &
    (df['district'].str.contains('Центральний|Соборний', na=False))
]

# Export filtered results
filtered.to_csv('data/filtered_apartments.csv', index=False)
print(f"Found {len(filtered)} matching apartments")
"""

# Example 10: Advanced monitoring with notifications
"""
import asyncio
from src.scraper import ApartmentScraper
from src.utils.config import ScraperConfig

async def monitor_new_apartments():
    config = ScraperConfig.from_env()
    scraper = ApartmentScraper(config)
    
    # Scrape only new apartments
    new_apartments = await scraper.run(
        max_pages=5,
        save_new_only=True
    )
    
    if new_apartments:
        # Filter by criteria
        good_apartments = [
            apt for apt in new_apartments
            if apt.price <= 15000 
            and apt.total_area and apt.total_area >= 40
        ]
        
        if good_apartments:
            # Send notification (integrate with Telegram, email, etc.)
            for apt in good_apartments:
                print(f"🔔 New apartment: {apt.name}")
                print(f"   💰 Price: {apt.price} {apt.currency}")
                print(f"   📐 Area: {apt.total_area} m²")
                print(f"   📍 Location: {apt.location}")
                print(f"   🔗 URL: {apt.url}")
                print()

if __name__ == "__main__":
    asyncio.run(monitor_new_apartments())
"""

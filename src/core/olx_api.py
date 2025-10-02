"""OLX API Client with async scraping capabilities"""
import asyncio
import random
import re
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse, parse_qs

import aiohttp
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from src.models import Apartment
from src.utils.logger import get_logger


class OLXClient:
    """Async client for scraping OLX apartment listings"""
    
    def __init__(
        self,
        base_url: str,
        user_agent: str,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        max_retries: int = 3
    ):
        """
        Initialize OLX client
        
        Args:
            base_url: Base URL for OLX
            user_agent: User agent string
            min_delay: Minimum delay between requests
            max_delay: Maximum delay between requests
            max_retries: Maximum number of retries for failed requests
        """
        self.base_url = base_url
        self.user_agent = user_agent
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.logger = get_logger()
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def start(self):
        """Start aiohttp session"""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-GPC': '1'
        }
        
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout
        )
        self.logger.info("OLX client session started")
    
    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.logger.info("OLX client session closed")
    
    async def _delay(self):
        """Add random delay between requests"""
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
    
    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize date string to dd.mm.YYYY format
        
        Args:
            date_str: Date string (e.g., "Сьогодні о 11:06", "01 жовтня 2025 р.")
            
        Returns:
            Normalized date in dd.mm.YYYY format
        """
        if not date_str:
            return datetime.now().strftime("%d.%m.%Y")
        
        now = datetime.now()
        
        # Handle "Сьогодні" (Today)
        if "Сьогодні" in date_str or "Сегодня" in date_str:
            return now.strftime("%d.%m.%Y")
        
        # Handle "Вчора" (Yesterday)
        if "Вчора" in date_str or "Вчера" in date_str:
            yesterday = datetime(now.year, now.month, now.day - 1 if now.day > 1 else 1)
            return yesterday.strftime("%d.%m.%Y")
        
        # Month name mapping (Ukrainian to number)
        months_uk = {
            'січня': 1, 'січ': 1,
            'лютого': 2, 'лют': 2,
            'березня': 3, 'бер': 3,
            'квітня': 4, 'кві': 4,
            'травня': 5, 'тра': 5,
            'червня': 6, 'чер': 6,
            'липня': 7, 'лип': 7,
            'серпня': 8, 'сер': 8,
            'вересня': 9, 'вер': 9,
            'жовтня': 10, 'жов': 10,
            'листопада': 11, 'лис': 11,
            'грудня': 12, 'гру': 12
        }
        
        # Try to parse format like "01 жовтня 2025 р."
        date_match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_str)
        if date_match:
            day = int(date_match.group(1))
            month_name = date_match.group(2).lower()
            year = int(date_match.group(3))
            
            month = months_uk.get(month_name, now.month)
            return f"{day:02d}.{month:02d}.{year}"
        
        # If can't parse, return current date
        return now.strftime("%d.%m.%Y")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def fetch_page(self, url: str) -> str:
        """
        Fetch page content with retries
        
        Args:
            url: URL to fetch
            
        Returns:
            Page HTML content
        """
        await self._delay()
        
        self.logger.debug(f"Fetching URL: {url}")
        
        async with self.session.get(url) as response:
            response.raise_for_status()
            content = await response.text()
            self.logger.debug(f"Successfully fetched {url} ({len(content)} bytes)")
            return content
    
    def parse_listing_page(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Parse listing page and extract apartment data
        
        Args:
            html: Page HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of apartment dictionaries
        """
        soup = BeautifulSoup(html, 'lxml')
        apartments = []
        
        # Find all listing cards
        cards = soup.find_all('div', {'data-cy': 'l-card'})
        self.logger.info(f"Found {len(cards)} apartment cards on page")
        
        for card in cards:
            try:
                apartment_data = self._parse_card(card, base_url)
                if apartment_data:
                    apartments.append(apartment_data)
            except Exception as e:
                self.logger.error(f"Error parsing card: {e}", exc_info=True)
                continue
        
        return apartments
    
    def _parse_card(self, card: BeautifulSoup, base_url: str) -> Optional[Dict[str, Any]]:
        """Parse individual apartment card"""
        try:
            # Extract post ID
            post_id = card.get('id')
            if not post_id:
                return None
            
            # Extract title and URL
            title_elem = card.find('h4', class_=re.compile('css-'))
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            
            # Extract URL
            link_elem = card.find('a', class_=re.compile('css-'))
            url = urljoin(base_url, link_elem['href']) if link_elem and link_elem.get('href') else ""
            
            # Extract price
            price_elem = card.find('p', {'data-testid': 'ad-price'})
            price = 0.0
            currency = "UAH"
            
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extract number from price
                price_match = re.search(r'([\d\s]+)', price_text.replace('\xa0', ''))
                if price_match:
                    price = float(price_match.group(1).replace(' ', ''))
                
                # Extract currency
                if 'грн' in price_text:
                    currency = "UAH"
                elif '$' in price_text:
                    currency = "USD"
                elif '€' in price_text:
                    currency = "EUR"
            
            # Extract location and date
            location = ""
            created_date = None
            
            location_elem = card.find('p', {'data-testid': 'location-date'})
            if location_elem:
                location_text = location_elem.get_text(strip=True)
                # Parse location (format: "Дніпро, Центральний - 01 жовтня 2025 р.")
                parts = location_text.split(' - ')
                if len(parts) >= 2:
                    location = parts[0].strip()
                    created_date = self._normalize_date(parts[1].strip())
                elif len(parts) == 1:
                    # Only location provided
                    location = parts[0].strip()
                    created_date = self._normalize_date("")
            
            # Extract area
            total_area = None
            area_elem = card.find('svg', {'data-testid': 'blueprint-card-param-icon'})
            if area_elem and area_elem.parent:
                area_text = area_elem.parent.get_text(strip=True)
                area_match = re.search(r'(\d+(?:\.\d+)?)\s*м²', area_text)
                if area_match:
                    total_area = float(area_match.group(1))
            
            # Extract district from location
            district = None
            if location:
                parts = location.split(',')
                if len(parts) >= 2:
                    district = parts[1].strip()
            
            apartment_data = {
                'post_id': post_id,
                'name': title,
                'price': price,
                'currency': currency,
                'location': location,
                'description': "",  # Will be filled from detail page
                'url': url,
                'created_date': created_date,
                'total_area': total_area,
                'district': district,
                'photos': [],
                'tags': [],
                'contact_phone': None,
                'watch_count': None,
                'floor': None,
                'total_floors': None,
                'rooms': None,
                'furnished': None
            }
            
            return apartment_data
            
        except Exception as e:
            self.logger.error(f"Error parsing card: {e}", exc_info=True)
            return None
    
    def extract_pagination_info(self, html: str, current_url: str) -> Dict[str, Any]:
        """
        Extract pagination information from page
        
        Args:
            html: Page HTML content
            current_url: Current page URL (to preserve query parameters)
            
        Returns:
            Dictionary with current page, total pages, and next page URL
        """
        soup = BeautifulSoup(html, 'lxml')
        
        pagination_info = {
            'current_page': 1,
            'total_pages': 1,
            'next_page_url': None
        }
        
        # Find pagination wrapper
        pagination = soup.find('div', {'data-testid': 'pagination-wrapper'})
        if not pagination:
            return pagination_info
        
        # Find current page
        active_page = pagination.find('li', class_=re.compile('pagination-item__active'))
        if active_page:
            current_text = active_page.get_text(strip=True)
            try:
                pagination_info['current_page'] = int(current_text)
            except ValueError:
                pass
        
        # Find last page
        page_items = pagination.find_all('li', {'data-testid': 'pagination-list-item'})
        if page_items:
            last_page_text = page_items[-1].get_text(strip=True)
            try:
                pagination_info['total_pages'] = int(last_page_text)
            except ValueError:
                pass
        
        # Find next page URL
        next_button = pagination.find('a', {'data-testid': 'pagination-forward'})
        if next_button and next_button.get('href'):
            next_href = next_button.get('href')
            if isinstance(next_href, str):
                # If href is absolute URL, use it directly
                if next_href.startswith('http://') or next_href.startswith('https://'):
                    pagination_info['next_page_url'] = next_href
                else:
                    # Otherwise, construct absolute URL from base
                    pagination_info['next_page_url'] = urljoin(self.base_url, next_href)
        
        return pagination_info
    
    async def fetch_detail_page_data(self, url: str) -> Dict[str, Any]:
        """
        Fetch detailed apartment information from detail page
        
        Args:
            url: URL of the detail page
            
        Returns:
            Dictionary with additional fields
        """
        try:
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, 'lxml')
            
            detail_data = {}
            
            # Extract description - UPDATED selector: class css-19duwlz
            desc_elem = soup.find('div', class_='css-19duwlz')
            if desc_elem:
                # Get text and preserve line breaks
                desc_text = desc_elem.get_text(separator='\n', strip=True)
                detail_data['description'] = desc_text
            
            # Extract photos
            photos = []
            photo_elems = soup.find_all('img', {'data-testid': 'swiper-image'}) + \
                         soup.find_all('img', {'data-testid': 'swiper-image-lazy'})
            for img in photo_elems:
                src = img.get('src')
                if src and src.startswith('http'):
                    photos.append(src)
            detail_data['photos'] = photos
            
            # Extract parameters - UPDATED: class css-6zsv65 with <p> tags class css-13x8d99
            params_container = soup.find('div', {'data-testid': 'ad-parameters-container', 'class': 'css-6zsv65'})
            if params_container:
                # All parameters are in <p> tags with class css-13x8d99
                params = params_container.find_all('p', class_='css-13x8d99')
                
                # Collect all tags (parameters)
                tags = []
                
                for param in params:
                    text = param.get_text(strip=True)
                    tags.append(text)
                    
                    # Extract floor
                    if 'Поверх:' in text:
                        floor_match = re.search(r'Поверх:\s*(\d+)', text)
                        if floor_match:
                            detail_data['floor'] = int(floor_match.group(1))
                    
                    # Extract total floors
                    if 'Поверховість:' in text:
                        floors_match = re.search(r'Поверховість:\s*(\d+)', text)
                        if floors_match:
                            detail_data['total_floors'] = int(floors_match.group(1))
                    
                    # Extract rooms
                    if 'Кількість кімнат:' in text:
                        rooms_match = re.search(r'(\d+)', text)
                        if rooms_match:
                            detail_data['rooms'] = int(rooms_match.group(1))
                    
                    # Extract furnished
                    if 'Меблювання:' in text:
                        detail_data['furnished'] = 'З меблями' in text or 'З меблями частково' in text
                
                # Save all parameter tags
                detail_data['tags'] = tags
            
            # Extract watch count (view count) - UPDATED selector: span class css-16uueru
            # NOTE: View count is often loaded dynamically via JavaScript and may not be
            # available in initial HTML. The selector exists but content loads asynchronously.
            watch_elem = soup.find('span', class_='css-16uueru')
            if watch_elem:
                watch_text = watch_elem.get_text(strip=True)
                # Extract number from text (might be "123 переглядів" or just number)
                watch_match = re.search(r'(\d+)', watch_text)
                if watch_match:
                    detail_data['watch_count'] = int(watch_match.group(1))
            else:
                # View count not available - likely loaded via JavaScript
                detail_data['watch_count'] = None
            
            return detail_data
            
        except Exception as e:
            self.logger.error(f"Error fetching detail page {url}: {e}", exc_info=True)
            return {}
    
    async def fetch_contact_phone(self, post_id: str) -> Optional[str]:
        """
        Fetch contact phone number using OLX API
        
        Args:
            post_id: Post ID number
            
        Returns:
            Phone number if available
        """
        try:
            # Try to fetch phone from API
            api_url = f"https://www.olx.ua/api/v1/offers/{post_id}/limited-phones/"
            
            headers = {
                'X-Client': 'DESKTOP',
                'X-Platform-Type': 'mobile-html5',
                'Version': 'v1.19',
                'Accept': '*/*'
            }
            
            async with self.session.get(api_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'data' in data and 'phones' in data['data']:
                        phones = data['data']['phones']
                        if phones:
                            return phones[0]
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Could not fetch phone for {post_id}: {e}")
            return None
    
    async def enrich_apartment_data(self, apartment: Apartment, fetch_phone: bool = False) -> Apartment:
        """
        Enrich apartment data with details from detail page
        
        Args:
            apartment: Apartment object with basic data
            fetch_phone: Whether to fetch contact phone (requires more API calls)
            
        Returns:
            Apartment with enriched data
        """
        try:
            # Fetch detail page data
            if apartment.url:
                detail_data = await self.fetch_detail_page_data(apartment.url)
                
                # Update apartment with detail data
                if 'description' in detail_data:
                    apartment.description = detail_data['description']
                if 'photos' in detail_data:
                    apartment.photos = detail_data['photos']
                if 'floor' in detail_data:
                    apartment.floor = detail_data['floor']
                if 'total_floors' in detail_data:
                    apartment.total_floors = detail_data['total_floors']
                if 'rooms' in detail_data:
                    apartment.rooms = detail_data['rooms']
                if 'furnished' in detail_data:
                    apartment.furnished = detail_data['furnished']
                if 'watch_count' in detail_data:
                    apartment.watch_count = detail_data['watch_count']
                if 'tags' in detail_data:
                    apartment.tags = detail_data['tags']
            
            # Fetch contact phone if requested
            if fetch_phone and apartment.post_id:
                phone = await self.fetch_contact_phone(apartment.post_id)
                if phone:
                    apartment.contact_phone = phone
            
            return apartment
            
        except Exception as e:
            self.logger.error(f"Error enriching apartment {apartment.post_id}: {e}", exc_info=True)
            return apartment
    
    async def scrape_listing_page(
        self, 
        url: str, 
        enrich_data: bool = False,
        fetch_phones: bool = False
    ) -> tuple[List[Apartment], Optional[str]]:
        """
        Scrape single listing page
        
        Args:
            url: URL of the listing page
            enrich_data: Whether to fetch detailed information for each apartment
            fetch_phones: Whether to fetch contact phones (only if enrich_data=True)
            
        Returns:
            Tuple of (list of apartments, next page URL)
        """
        html = await self.fetch_page(url)
        
        # Parse apartments
        apartments_data = self.parse_listing_page(html, self.base_url)
        apartments = [Apartment(**data) for data in apartments_data]
        
        # Enrich data if requested - PARALLEL processing for speed
        if enrich_data and apartments:
            # Create tasks for parallel enrichment
            enrichment_tasks = [
                self.enrich_apartment_data(apt, fetch_phone=fetch_phones)
                for apt in apartments
            ]
            
            # Execute all enrichment tasks concurrently
            apartments = await asyncio.gather(*enrichment_tasks)
        
        # Extract pagination (pass current URL to preserve query params)
        pagination = self.extract_pagination_info(html, current_url=url)
        next_url = pagination['next_page_url']
        
        # Try to extract actual page number from URL if pagination shows page 1
        actual_page = pagination['current_page']
        if actual_page == 1 and '?page=' in url:
            # Extract page number from URL
            try:
                page_match = re.search(r'[?&]page=(\d+)', url)
                if page_match:
                    actual_page = int(page_match.group(1))
            except:
                pass
        
        self.logger.info(
            f"Scraped page {actual_page}/{pagination['total_pages']}: "
            f"found {len(apartments)} apartments"
        )
        
        return apartments, next_url
    
    async def scrape_all_pages(
        self,
        start_url: str,
        max_pages: Optional[int] = None,
        enrich_data: bool = False,
        fetch_phones: bool = False,
        page_callback=None
    ) -> List[Apartment]:
        """
        Scrape all listing pages
        
        Args:
            start_url: Starting URL
            max_pages: Maximum number of pages to scrape (None for all)
            enrich_data: Whether to fetch detailed information for each apartment
            fetch_phones: Whether to fetch contact phones (only if enrich_data=True)
            page_callback: Optional callback function called after each page with (apartments, page_num)
            
        Returns:
            List of all apartments found
        """
        all_apartments = []
        current_url = start_url
        page_count = 0
        
        while current_url:
            page_count += 1
            
            if max_pages and page_count > max_pages:
                self.logger.info(f"Reached maximum page limit: {max_pages}")
                break
            
            try:
                apartments, next_url = await self.scrape_listing_page(
                    current_url, 
                    enrich_data=enrich_data,
                    fetch_phones=fetch_phones
                )
                all_apartments.extend(apartments)
                
                # Call callback if provided (for incremental saving)
                if page_callback and apartments:
                    await page_callback(apartments, page_count)
                
                current_url = next_url
                
            except Exception as e:
                self.logger.error(f"Error scraping page {current_url}: {e}", exc_info=True)
                break
        
        self.logger.info(f"Total apartments scraped: {len(all_apartments)} from {page_count} pages")
        return all_apartments

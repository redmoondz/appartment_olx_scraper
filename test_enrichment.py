"""Test enrichment functionality"""
import asyncio
import sys
sys.path.insert(0, 'src')

from core.olx_api import OLXClient
from models import Apartment


async def main():
    """Test enrichment on a few sample apartments"""
    
    # Sample apartments from cache
    test_apartments = [
        {
            'post_id': '898719171',
            'name': 'Здам 1 кім квартиру Лівобережний-3',
            'url': 'https://www.olx.ua/d/uk/obyavlenie/zdam-1-km-kvartiru-lvoberezhniy-3-IDYOWUw.html',
        },
        {
            'post_id': '901951378',
            'name': 'Сдам 2ух кв на ул.рабочая 116а свободна',
            'url': 'https://www.olx.ua/d/uk/obyavlenie/sdam-2uh-kv-na-ul-rabochaya-116a-svobodna-IDZ2uKS.html',
        },
        {
            'post_id': '782509816',
            'name': 'Сдам отличную 2 комнатную квартиру на Коммунаре возле метро',
            'url': 'https://www.olx.ua/d/uk/obyavlenie/sdam-otlichnuyu-2-komnatnuyu-kvartiru-na-kommunare-vozle-metro-IDQXky4.html',
        }
    ]
    
    # Initialize client
    client = OLXClient(
        base_url='https://www.olx.ua',
        user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        min_delay=1.0,
        max_delay=2.0,
        max_retries=3
    )
    
    async with client:
        for i, apt_data in enumerate(test_apartments, 1):
            print(f"\n{'='*80}")
            print(f"[{i}/{len(test_apartments)}] Testing: {apt_data['name']}")
            print(f"URL: {apt_data['url']}")
            print('='*80)
            
            # Create basic apartment
            apt = Apartment(
                post_id=apt_data['post_id'],
                name=apt_data['name'],
                price=0,
                currency='UAH',
                location='',
                description='',  # Will be enriched
                url=apt_data['url']
            )
            
            # Enrich
            enriched = await client.enrich_apartment_data(apt, fetch_phone=False)
            
            # Display results
            print(f"\n✓ Description ({len(enriched.description)} chars):")
            print(f"  {enriched.description[:200]}..." if enriched.description else "  EMPTY")
            
            print(f"\n✓ Photos: {len(enriched.photos)} photos")
            if enriched.photos:
                for j, photo in enumerate(enriched.photos[:3], 1):
                    print(f"  [{j}] {photo[:80]}...")
            
            print(f"\n✓ Parameters:")
            print(f"  Floor: {enriched.floor if enriched.floor else 'EMPTY'}")
            print(f"  Total Floors: {enriched.total_floors if enriched.total_floors else 'EMPTY'}")
            print(f"  Rooms: {enriched.rooms if enriched.rooms else 'EMPTY'}")
            print(f"  Furnished: {enriched.furnished if enriched.furnished is not None else 'EMPTY'}")
            
            print(f"\n✓ Statistics:")
            print(f"  Watch Count: {enriched.watch_count if enriched.watch_count else 'EMPTY'}")
            
            print(f"\n✓ Tags ({len(enriched.tags)} tags):")
            if enriched.tags:
                print(f"  {', '.join(enriched.tags)}")
            else:
                print("  EMPTY")


if __name__ == '__main__':
    asyncio.run(main())

#!/usr/bin/env python3
"""Main entry point for OLX Apartment Scraper"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cli import cli

if __name__ == '__main__':
    cli()

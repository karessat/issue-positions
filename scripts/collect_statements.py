#!/usr/bin/env python3
"""
Collect trade-related floor statements from Congressional Record.

This script:
1. Fetches Congressional Record data from GPO bulk data
2. Parses XML to extract floor speeches
3. Filters statements containing trade-related keywords
4. Associates statements with senators by name matching
5. Stores statements in the database

Usage:
    python scripts/collect_statements.py [--days 30] [--year 2024]

Data source:
    https://www.govinfo.gov/bulkdata/CREC
"""
import sys
import os
import argparse
import re
import zipfile
import io
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import time
import xml.etree.ElementTree as ET

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from dotenv import load_dotenv

from api.models import (
    SessionLocal,
    Member,
    Statement,
    Chamber,
)
from scripts.utils.metadata import update_metadata

load_dotenv(project_root / ".env")

# GPO Congressional Record base URL
GPO_BULK_BASE = "https://www.govinfo.gov/bulkdata/CREC"

# Trade-related keywords for filtering statements
TRADE_KEYWORDS = [
    # Core trade terms
    "tariff",
    "tariffs",
    "trade agreement",
    "trade deal",
    "trade policy",
    "trade war",
    "trade deficit",
    "trade surplus",
    "free trade",
    "fair trade",
    # Specific agreements/organizations
    "usmca",
    "nafta",
    "trans-pacific",
    "tpp",
    "world trade organization",
    "wto",
    # Protectionist terms
    "buy american",
    "made in america",
    "american-made",
    "domestic manufacturing",
    "protect american jobs",
    "protect american workers",
    "dumping",
    "anti-dumping",
    "countervailing",
    # Import/export
    "import duties",
    "import restrictions",
    "export controls",
    "export promotion",
    "trade barriers",
    "trade restrictions",
    # Industry specific
    "steel imports",
    "aluminum imports",
    "auto imports",
    "semiconductor",
    "supply chain",
    "reshoring",
    "nearshoring",
    "offshoring",
    "outsourcing",
    # Countries (trade context)
    "china trade",
    "chinese imports",
    "chinese goods",
]


def contains_trade_keywords(text: str) -> bool:
    """Check if text contains trade-related keywords."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in TRADE_KEYWORDS)


def get_trade_keywords_found(text: str) -> list[str]:
    """Return list of trade keywords found in text."""
    text_lower = text.lower()
    return [kw for kw in TRADE_KEYWORDS if kw in text_lower]


def fetch_crec_index(client: httpx.Client, year: int, month: int) -> list[str]:
    """Fetch list of available CREC dates for a month."""
    # GPO provides a sitemap listing available dates
    # Format: https://www.govinfo.gov/bulkdata/CREC/YYYY/MM
    url = f"{GPO_BULK_BASE}/{year}/{month:02d}"

    try:
        response = client.get(url)
        if response.status_code == 404:
            return []
        response.raise_for_status()

        # Parse HTML to find links to daily directories
        # Links look like: CREC-2024-01-15/
        dates = re.findall(r'CREC-(\d{4}-\d{2}-\d{2})', response.text)
        return sorted(set(dates))
    except Exception as e:
        print(f"  Error fetching index for {year}/{month:02d}: {e}")
        return []


def fetch_crec_day(client: httpx.Client, date_str: str) -> Optional[bytes]:
    """Fetch Congressional Record ZIP for a single day."""
    # Format: https://www.govinfo.gov/bulkdata/CREC/YYYY/MM/CREC-YYYY-MM-DD.zip
    year, month, day = date_str.split("-")
    url = f"{GPO_BULK_BASE}/{year}/{month}/CREC-{date_str}.zip"

    try:
        response = client.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"  Error fetching CREC for {date_str}: {e}")
        return None


def parse_senate_xml(xml_content: bytes, date_str: str) -> list[dict]:
    """Parse Senate section XML to extract speeches."""
    statements = []

    try:
        root = ET.fromstring(xml_content)

        # Congressional Record XML structure varies
        # Look for speaking elements with speaker info

        # Find all speaking turns
        for speaking in root.iter():
            # Look for elements that indicate a speaking turn
            if speaking.tag in ['speaking', 'speech', 'paragraph']:
                speaker = speaking.get('speaker') or speaking.get('name-id')

                # Get the text content
                text_parts = []
                for elem in speaking.iter():
                    if elem.text:
                        text_parts.append(elem.text)
                    if elem.tail:
                        text_parts.append(elem.tail)

                text = ' '.join(text_parts).strip()

                if text and len(text) > 100:  # Skip very short statements
                    statements.append({
                        'speaker': speaker,
                        'text': text,
                        'date': date_str,
                    })

        # Alternative: look for specific GPO structure
        # The CREC format uses different tags
        for record in root.findall('.//content'):
            text = record.text or ''
            if text and len(text) > 100:
                statements.append({
                    'speaker': None,
                    'text': text,
                    'date': date_str,
                })

    except ET.ParseError as e:
        print(f"  XML parse error: {e}")

    return statements


def extract_statements_from_zip(zip_content: bytes, date_str: str) -> list[dict]:
    """Extract Senate statements from CREC ZIP file."""
    statements = []

    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            # Look for Senate section files
            # Files are typically in format: CREC-YYYY-MM-DD/CREC-YYYY-MM-DD-pt1-PgSxxxx.xml
            for filename in zf.namelist():
                # Senate pages start with 'S' in page number
                if '/CREC-' in filename and '-PgS' in filename and filename.endswith('.xml'):
                    try:
                        xml_content = zf.read(filename)
                        page_statements = parse_senate_xml(xml_content, date_str)
                        for stmt in page_statements:
                            stmt['source_file'] = filename
                        statements.extend(page_statements)
                    except Exception as e:
                        continue

                # Also check for senate section files
                elif 'senate' in filename.lower() and filename.endswith('.xml'):
                    try:
                        xml_content = zf.read(filename)
                        page_statements = parse_senate_xml(xml_content, date_str)
                        for stmt in page_statements:
                            stmt['source_file'] = filename
                        statements.extend(page_statements)
                    except Exception as e:
                        continue

    except zipfile.BadZipFile:
        print(f"  Bad ZIP file for {date_str}")

    return statements


def extract_text_from_html(html_content: str) -> str:
    """Extract text from HTML content, removing tags."""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def match_speaker_to_member(
    speaker_text: str,
    text: str,
    members: list[Member]
) -> Optional[Member]:
    """Try to match a speaker reference to a database member."""
    if not speaker_text and not text:
        return None

    search_text = f"{speaker_text or ''} {text[:500]}".lower()

    for member in members:
        # Try matching last name
        if member.last_name and member.last_name.lower() in search_text:
            # Verify it looks like this senator is speaking
            name_patterns = [
                f"mr. {member.last_name.lower()}",
                f"ms. {member.last_name.lower()}",
                f"mrs. {member.last_name.lower()}",
                f"senator {member.last_name.lower()}",
                member.last_name.lower(),
            ]
            if any(p in search_text for p in name_patterns):
                return member

    return None


def collect_statements(
    days: int = 30,
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    """Main collection function."""
    db = SessionLocal()

    try:
        # Get all senators for speaker matching
        senators = db.query(Member).filter(Member.chamber == Chamber.SENATE).all()
        print(f"Loaded {len(senators)} senators for speaker matching")

        # Determine date range
        if year and month:
            # Specific month
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        else:
            # Last N days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

        print(f"Collecting statements from {start_date.date()} to {end_date.date()}")

        statements_stored = 0
        days_processed = 0

        with httpx.Client(timeout=60.0) as client:
            # Generate list of months to check
            current = start_date
            months_to_check = []
            while current <= end_date:
                months_to_check.append((current.year, current.month))
                if current.month == 12:
                    current = datetime(current.year + 1, 1, 1)
                else:
                    current = datetime(current.year, current.month + 1, 1)

            for check_year, check_month in months_to_check:
                print(f"\nChecking {check_year}/{check_month:02d}...")

                # Get available dates for this month
                available_dates = fetch_crec_index(client, check_year, check_month)
                print(f"  Found {len(available_dates)} days with records")

                for date_str in available_dates:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if date_obj < start_date or date_obj > end_date:
                        continue

                    print(f"  Processing {date_str}...")

                    # Fetch the ZIP for this day
                    zip_content = fetch_crec_day(client, date_str)
                    if not zip_content:
                        continue

                    # Extract statements
                    raw_statements = extract_statements_from_zip(zip_content, date_str)
                    print(f"    Extracted {len(raw_statements)} raw statements")

                    # Filter for trade keywords and store
                    trade_statements = 0
                    for stmt in raw_statements:
                        if not contains_trade_keywords(stmt['text']):
                            continue

                        # Try to match to a senator
                        member = match_speaker_to_member(
                            stmt.get('speaker'),
                            stmt['text'],
                            senators
                        )

                        if not member:
                            continue

                        # Check for duplicates (same member, same date, similar text start)
                        text_preview = stmt['text'][:200]
                        existing = db.query(Statement).filter(
                            Statement.member_id == member.id,
                            Statement.source_date == date_obj,
                            Statement.text.like(f"{text_preview[:100]}%")
                        ).first()

                        if existing:
                            continue

                        # Extract page number from filename
                        page_match = re.search(r'Pg(S\d+)', stmt.get('source_file', ''))
                        page = page_match.group(1) if page_match else None

                        # Create statement record
                        statement = Statement(
                            member_id=member.id,
                            text=stmt['text'],
                            source="congressional_record",
                            source_url=f"https://www.govinfo.gov/content/pkg/CREC-{date_str}/html/CREC-{date_str}.htm",
                            source_date=date_obj,
                            cr_page=page,
                            cr_section="SENATE",
                            congress=118 if date_obj.year >= 2023 else 117,
                            issue_tags=["trade-policy"],
                            analyzed=0,
                        )

                        db.add(statement)
                        trade_statements += 1
                        statements_stored += 1

                    db.commit()
                    print(f"    Stored {trade_statements} trade-related statements")
                    days_processed += 1

                    time.sleep(0.5)  # Rate limiting

        print(f"\n{'='*60}")
        print(f"Collection complete!")
        print(f"Days processed: {days_processed}")
        print(f"Trade statements stored: {statements_stored}")

        # Update metadata
        total_statements = db.query(Statement).count()
        update_metadata(
            db,
            data_type="statements",
            record_count=total_statements,
            source="congressional_record",
            notes=f"Collected from GPO bulk data ({start_date.date()} to {end_date.date()})"
        )
        print(f"Updated metadata: {total_statements} total statements")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Collect trade-related statements from Congressional Record"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=30,
        help="Number of days to look back (default: 30)"
    )
    parser.add_argument(
        "--year", "-y",
        type=int,
        help="Specific year to collect (overrides --days)"
    )
    parser.add_argument(
        "--month", "-m",
        type=int,
        help="Specific month to collect (requires --year)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Congressional Record Statement Collection")
    print("=" * 60)
    print(f"Source: GPO Bulk Data ({GPO_BULK_BASE})")
    print()

    if args.year and not args.month:
        parser.error("--year requires --month")

    collect_statements(
        days=args.days,
        year=args.year,
        month=args.month,
    )


if __name__ == "__main__":
    main()

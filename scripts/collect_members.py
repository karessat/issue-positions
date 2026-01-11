#!/usr/bin/env python3
"""
Collect and populate congressional member data.

This script fetches current Senate members from the Congress.gov API
and populates the members table.

Usage:
    python scripts/collect_members.py

Requires:
    CONGRESS_API_KEY environment variable (get free key at api.congress.gov)
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from dotenv import load_dotenv

from api.models import SessionLocal, Member, Chamber, Party
from scripts.utils.metadata import update_metadata

# Load environment variables
load_dotenv(project_root / ".env")

CONGRESS_API_BASE = "https://api.congress.gov/v3"
CURRENT_CONGRESS = 119  # 2025-2027


def get_api_key():
    """Get Congress.gov API key from environment."""
    key = os.getenv("CONGRESS_API_KEY")
    if not key:
        print("ERROR: CONGRESS_API_KEY not found in environment.")
        print("Get a free API key at: https://api.congress.gov/sign-up/")
        print("Then add it to your .env file: CONGRESS_API_KEY=your_key_here")
        sys.exit(1)
    return key


def fetch_senate_members(api_key: str) -> list[dict]:
    """Fetch current Senate members from Congress.gov API."""
    members = []
    offset = 0
    limit = 250  # Max allowed by API

    print(f"Fetching Senate members from Congress {CURRENT_CONGRESS}...")

    with httpx.Client(timeout=30.0) as client:
        while True:
            url = f"{CONGRESS_API_BASE}/member"
            params = {
                "api_key": api_key,
                "currentMember": "true",
                "format": "json",
                "limit": limit,
                "offset": offset,
            }

            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            batch = data.get("members", [])
            if not batch:
                break

            # Filter for Senate members only
            senators = [m for m in batch if _is_current_senator(m)]
            members.extend(senators)

            print(f"  Fetched {len(members)} senators so far...")

            # Check if there are more pages
            if len(batch) < limit:
                break
            offset += limit

    return members


def _is_current_senator(member: dict) -> bool:
    """Check if member is a current senator."""
    terms = member.get("terms", {}).get("item", [])
    if not terms:
        return False

    # Get most recent term
    latest_term = terms[-1] if isinstance(terms, list) else terms

    # Check if it's a Senate term
    chamber = latest_term.get("chamber", "")
    return chamber.lower() == "senate"


def parse_party(party_name: str) -> Party:
    """Parse party name to enum."""
    party_map = {
        "Democratic": Party.DEMOCRAT,
        "Democrat": Party.DEMOCRAT,
        "Republican": Party.REPUBLICAN,
        "Independent": Party.INDEPENDENT,
    }
    return party_map.get(party_name, Party.INDEPENDENT)


def get_member_details(client: httpx.Client, api_key: str, bioguide_id: str) -> dict:
    """Fetch detailed member info."""
    url = f"{CONGRESS_API_BASE}/member/{bioguide_id}"
    params = {"api_key": api_key, "format": "json"}

    response = client.get(url, params=params)
    response.raise_for_status()
    return response.json().get("member", {})


def populate_members(members_data: list[dict], api_key: str):
    """Populate the members table with fetched data."""
    db = SessionLocal()

    try:
        added = 0
        updated = 0

        with httpx.Client(timeout=30.0) as client:
            for i, member in enumerate(members_data):
                bioguide_id = member.get("bioguideId")
                if not bioguide_id:
                    continue

                # Get detailed info for each member
                print(f"  [{i+1}/{len(members_data)}] Processing {member.get('name')}...")

                try:
                    details = get_member_details(client, api_key, bioguide_id)
                except Exception as e:
                    print(f"    Warning: Could not fetch details: {e}")
                    details = member

                # Extract term info
                terms = details.get("terms", [])
                if isinstance(terms, dict):
                    terms = terms.get("item", [])
                latest_term = terms[-1] if terms else {}

                # Parse term start date
                term_start = None
                start_year = latest_term.get("startYear")
                if start_year:
                    term_start = datetime(int(start_year), 1, 3)  # Congress starts Jan 3

                # Get state from latest term or direct field
                state = latest_term.get("stateCode") or member.get("state")

                # Build member record
                member_record = {
                    "id": bioguide_id,
                    "name": details.get("directOrderName") or member.get("name"),
                    "first_name": details.get("firstName"),
                    "last_name": details.get("lastName"),
                    "state": state,
                    "party": parse_party(details.get("partyName") or member.get("partyName", "")),
                    "chamber": Chamber.SENATE,
                    "current_term_start": term_start,
                    "photo_url": details.get("depiction", {}).get("imageUrl"),
                }

                # Check if member exists
                existing = db.query(Member).filter(Member.id == bioguide_id).first()
                if existing:
                    # Update existing
                    for key, value in member_record.items():
                        if key != "id" and value is not None:
                            setattr(existing, key, value)
                    updated += 1
                else:
                    # Create new
                    db.add(Member(**member_record))
                    added += 1

            db.commit()
            print(f"\nComplete: {added} added, {updated} updated")

            # Update metadata
            total = added + updated
            update_metadata(
                db,
                data_type="members",
                record_count=total,
                source="congress_api",
                notes=f"Fetched from Congress.gov API"
            )
            print(f"Updated metadata: {total} members")

    finally:
        db.close()


def main():
    """Main function to collect and populate members."""
    print("=" * 60)
    print("Senate Member Collection")
    print("=" * 60)
    print()

    api_key = get_api_key()

    # Fetch members from API
    members = fetch_senate_members(api_key)
    print(f"\nFound {len(members)} current senators")
    print()

    if not members:
        print("No members found. Check API key and try again.")
        return

    # Populate database
    print("Populating database...")
    populate_members(members, api_key)

    # Print summary
    db = SessionLocal()
    try:
        count = db.query(Member).filter(Member.chamber == Chamber.SENATE).count()
        print(f"\nTotal senators in database: {count}")

        # Show party breakdown
        for party in Party:
            party_count = db.query(Member).filter(
                Member.chamber == Chamber.SENATE,
                Member.party == party
            ).count()
            if party_count > 0:
                print(f"  {party.name}: {party_count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

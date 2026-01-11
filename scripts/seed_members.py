#!/usr/bin/env python3
"""
Seed the database with member data from JSON file.

This script loads senators from the seed data file without requiring
an API key. Use this for initial setup and testing.

Usage:
    python scripts/seed_members.py
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.models import SessionLocal, Member, Chamber, Party


SEED_FILE = project_root / "data" / "seed" / "senators_119.json"

# Photo URL template (Congress.gov bioguide photos)
PHOTO_URL_TEMPLATE = "https://bioguide.congress.gov/bioguide/photo/{first_letter}/{bioguide_id}.jpg"


def parse_party(party_code: str) -> Party:
    """Parse party code to enum."""
    party_map = {
        "D": Party.DEMOCRAT,
        "R": Party.REPUBLICAN,
        "I": Party.INDEPENDENT,
    }
    return party_map.get(party_code, Party.INDEPENDENT)


def load_seed_data() -> dict:
    """Load seed data from JSON file."""
    if not SEED_FILE.exists():
        print(f"ERROR: Seed file not found: {SEED_FILE}")
        sys.exit(1)

    with open(SEED_FILE, "r") as f:
        return json.load(f)


def seed_members(data: dict):
    """Seed members from data."""
    db = SessionLocal()
    congress = data.get("congress", 119)
    term_start = datetime(2025, 1, 3)  # 119th Congress start date

    try:
        added = 0
        updated = 0

        for member_data in data["members"]:
            bioguide_id = member_data["id"]

            # Generate photo URL
            photo_url = PHOTO_URL_TEMPLATE.format(
                first_letter=bioguide_id[0],
                bioguide_id=bioguide_id
            )

            # Build full name
            first_name = member_data["first_name"]
            last_name = member_data["last_name"]
            full_name = f"{first_name} {last_name}"

            member_record = {
                "id": bioguide_id,
                "name": full_name,
                "first_name": first_name,
                "last_name": last_name,
                "state": member_data["state"],
                "party": parse_party(member_data["party"]),
                "chamber": Chamber.SENATE,
                "current_term_start": term_start,
                "photo_url": photo_url,
            }

            # Check if member exists
            existing = db.query(Member).filter(Member.id == bioguide_id).first()
            if existing:
                for key, value in member_record.items():
                    if key != "id":
                        setattr(existing, key, value)
                updated += 1
            else:
                db.add(Member(**member_record))
                added += 1

        db.commit()
        print(f"Seeding complete: {added} added, {updated} updated")

    finally:
        db.close()


def print_summary():
    """Print summary of members in database."""
    db = SessionLocal()
    try:
        total = db.query(Member).filter(Member.chamber == Chamber.SENATE).count()
        print(f"\nTotal senators in database: {total}")
        print()

        # Party breakdown
        print("Party breakdown:")
        for party in Party:
            count = db.query(Member).filter(
                Member.chamber == Chamber.SENATE,
                Member.party == party
            ).count()
            if count > 0:
                print(f"  {party.name}: {count}")

        # State coverage
        states = db.query(Member.state).filter(
            Member.chamber == Chamber.SENATE
        ).distinct().count()
        print(f"\nStates represented: {states}")

        # Sample members
        print("\nSample members:")
        samples = db.query(Member).filter(
            Member.chamber == Chamber.SENATE
        ).limit(5).all()
        for m in samples:
            print(f"  {m.name} ({m.party.value}-{m.state})")

    finally:
        db.close()


def main():
    """Main function."""
    print("=" * 60)
    print("Senate Member Seeding")
    print("=" * 60)
    print()

    # Load seed data
    print(f"Loading seed data from: {SEED_FILE}")
    data = load_seed_data()
    print(f"Found {len(data['members'])} senators in seed file")
    print(f"Congress: {data.get('congress', 'unknown')}")
    print()

    # Seed the database
    print("Seeding database...")
    seed_members(data)

    # Print summary
    print_summary()


if __name__ == "__main__":
    main()

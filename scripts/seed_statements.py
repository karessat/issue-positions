#!/usr/bin/env python3
"""
Seed the database with sample trade-related statements.

This script loads statement data from data/seed/statements.json
and populates the database. Used for development and testing.

Usage:
    python scripts/seed_statements.py
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.models import SessionLocal, Statement, Member
from scripts.utils.metadata import update_metadata

SEED_FILE = project_root / "data" / "seed" / "statements.json"


def load_seed_data() -> dict:
    """Load statement data from seed file."""
    if not SEED_FILE.exists():
        print(f"ERROR: Seed file not found: {SEED_FILE}")
        sys.exit(1)

    with open(SEED_FILE) as f:
        return json.load(f)


def seed_statements(data: dict):
    """Seed statements from data."""
    db = SessionLocal()

    try:
        statements = data.get("statements", [])
        print(f"Seeding {len(statements)} statements...")

        added = 0
        skipped = 0

        for stmt_data in statements:
            member_id = stmt_data["member_id"]

            # Verify member exists
            member = db.query(Member).filter(Member.id == member_id).first()
            if not member:
                print(f"  Skipping: Member {member_id} not found")
                skipped += 1
                continue

            # Parse date
            source_date = datetime.strptime(stmt_data["source_date"], "%Y-%m-%d")

            # Check for existing statement (avoid duplicates)
            existing = db.query(Statement).filter(
                Statement.member_id == member_id,
                Statement.source_date == source_date,
                Statement.cr_page == stmt_data.get("cr_page"),
            ).first()

            if existing:
                print(f"  Skipping: Statement already exists for {member.name} on {source_date.date()}")
                skipped += 1
                continue

            # Create statement
            statement = Statement(
                member_id=member_id,
                text=stmt_data["text"],
                title=stmt_data.get("title"),
                source="congressional_record",
                source_url=f"https://www.congress.gov/congressional-record/{source_date.year}",
                source_date=source_date,
                cr_page=stmt_data.get("cr_page"),
                cr_section="SENATE",
                congress=118,
                issue_tags=["trade-policy"],
                analyzed=0,
            )

            db.add(statement)
            added += 1
            print(f"  Added: {member.name} - {stmt_data.get('title', 'Untitled')[:40]}")

        db.commit()

        print(f"\nStatements seeded: {added}")
        print(f"Statements skipped: {skipped}")

        # Update metadata
        total = db.query(Statement).count()
        update_metadata(
            db,
            data_type="statements",
            record_count=total,
            source="seed_file",
            notes="Seeded from statements.json"
        )
        print(f"Total statements in database: {total}")

    finally:
        db.close()


def main():
    print("=" * 60)
    print("Statement Seeding")
    print("=" * 60)
    print(f"Seed file: {SEED_FILE}")
    print()

    data = load_seed_data()
    seed_statements(data)


if __name__ == "__main__":
    main()

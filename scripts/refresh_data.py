#!/usr/bin/env python3
"""
Check data freshness and refresh if stale (more than 30 days old).

This script:
1. Checks when each data type was last updated
2. If data is stale (>30 days), triggers a refresh from source
3. Can be run manually or scheduled via cron

Usage:
    python scripts/refresh_data.py              # Check and refresh if stale
    python scripts/refresh_data.py --force      # Force refresh all data
    python scripts/refresh_data.py --status     # Just show status, don't refresh
    python scripts/refresh_data.py --days 7     # Custom staleness threshold
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.models import SessionLocal, DataMetadata, Member, Vote, Position, Statement
from scripts.utils.metadata import get_all_metadata, is_stale, format_age, update_metadata


def print_status(db):
    """Print the current status of all data types."""
    print("=" * 70)
    print("DATA FRESHNESS STATUS")
    print("=" * 70)
    print()

    metadata_list = get_all_metadata(db)

    if not metadata_list:
        print("No data has been loaded yet.")
        print("\nRun these scripts to populate the database:")
        print("  python scripts/seed_members.py")
        print("  python scripts/seed_votes.py")
        print("  python scripts/calculate_scores.py")
        return

    # Get actual counts
    member_count = db.query(Member).count()
    vote_count = db.query(Vote).count()
    position_count = db.query(Position).count()
    statement_count = db.query(Statement).count()

    actual_counts = {
        "members": member_count,
        "votes": vote_count,
        "positions": position_count,
        "statements": statement_count,
    }

    for metadata in metadata_list:
        status = "STALE" if metadata.is_stale else "OK"
        status_color = "!" if metadata.is_stale else " "
        actual = actual_counts.get(metadata.data_type, "?")

        print(f"{status_color} {metadata.data_type.upper():12} {status:6}")
        print(f"    Last updated:  {metadata.last_updated.strftime('%Y-%m-%d %H:%M')} ({format_age(metadata.last_updated)})")
        print(f"    Record count:  {actual} (was {metadata.record_count} at last refresh)")
        print(f"    Source:        {metadata.source or 'unknown'}")
        if metadata.notes:
            print(f"    Notes:         {metadata.notes}")
        print()

    # Check for missing metadata
    expected_types = {"members", "votes", "positions", "statements"}
    existing_types = {m.data_type for m in metadata_list}
    missing = expected_types - existing_types

    if missing:
        print("MISSING DATA:")
        for data_type in missing:
            print(f"  ! {data_type} - no metadata found, needs initial load")
        print()


def refresh_members(db, use_api: bool = False):
    """Refresh member data."""
    print("\n" + "=" * 50)
    print("REFRESHING MEMBERS")
    print("=" * 50)

    if use_api:
        print("Using Congress.gov API...")
        # Import and run the API-based collection
        try:
            from scripts.collect_members import fetch_senate_members, populate_members, get_api_key
            api_key = get_api_key()
            members = fetch_senate_members(api_key)
            if members:
                populate_members(members, api_key)
            return True
        except Exception as e:
            print(f"API collection failed: {e}")
            print("Falling back to seed file...")

    # Use seed file
    print("Using seed file...")
    from scripts.seed_members import load_seed_data, seed_members
    try:
        data = load_seed_data()
        seed_members(data)
        return True
    except Exception as e:
        print(f"Seeding failed: {e}")
        return False


def refresh_votes(db, use_api: bool = False):
    """Refresh vote data."""
    print("\n" + "=" * 50)
    print("REFRESHING VOTES")
    print("=" * 50)

    if use_api:
        print("Using Congress.gov API...")
        try:
            from scripts.collect_votes import collect_votes
            collect_votes(congress=118, limit=20)
            return True
        except Exception as e:
            print(f"API collection failed: {e}")
            print("Falling back to seed file...")

    # Use seed file
    print("Using seed file...")
    from scripts.seed_votes import load_seed_data, seed_bills_and_votes
    try:
        data = load_seed_data()
        seed_bills_and_votes(data)
        return True
    except Exception as e:
        print(f"Seeding failed: {e}")
        return False


def refresh_positions(db):
    """Recalculate all positions."""
    print("\n" + "=" * 50)
    print("RECALCULATING POSITIONS")
    print("=" * 50)

    from scripts.calculate_scores import calculate_all_positions
    try:
        calculate_all_positions()
        return True
    except Exception as e:
        print(f"Position calculation failed: {e}")
        return False


def refresh_statements(db, use_api: bool = False):
    """Refresh statement data."""
    print("\n" + "=" * 50)
    print("REFRESHING STATEMENTS")
    print("=" * 50)

    if use_api:
        print("Using Congressional Record API...")
        try:
            from scripts.collect_statements import collect_statements
            collect_statements(days=30)
            return True
        except Exception as e:
            print(f"API collection failed: {e}")
            print("Falling back to seed file...")

    # Use seed file
    print("Using seed file...")
    from scripts.seed_statements import load_seed_data, seed_statements
    try:
        data = load_seed_data()
        seed_statements(data)
        return True
    except Exception as e:
        print(f"Seeding failed: {e}")
        return False


def check_and_refresh(max_age_days: int = 30, force: bool = False, use_api: bool = False):
    """Check all data types and refresh if stale."""
    db = SessionLocal()

    try:
        print()
        print_status(db)

        # Determine what needs refreshing
        needs_refresh = {
            "members": force or is_stale(db, "members", max_age_days),
            "votes": force or is_stale(db, "votes", max_age_days),
            "statements": force or is_stale(db, "statements", max_age_days),
            "positions": force or is_stale(db, "positions", max_age_days),
        }

        if not any(needs_refresh.values()):
            print("All data is fresh. No refresh needed.")
            return True

        print("=" * 70)
        print("REFRESHING STALE DATA")
        print("=" * 70)

        if force:
            print(f"Force refresh requested - refreshing all data")
        else:
            print(f"Staleness threshold: {max_age_days} days")

        print(f"\nData to refresh: {', '.join(k for k, v in needs_refresh.items() if v)}")

        # Refresh in order: members first, then votes, then positions
        success = True

        if needs_refresh["members"]:
            if not refresh_members(db, use_api):
                success = False

        if needs_refresh["votes"]:
            if not refresh_votes(db, use_api):
                success = False

        if needs_refresh["statements"]:
            if not refresh_statements(db, use_api):
                success = False

        # Always recalculate positions if members or votes changed
        if needs_refresh["members"] or needs_refresh["votes"] or needs_refresh["positions"]:
            if not refresh_positions(db):
                success = False

        print("\n" + "=" * 70)
        if success:
            print("REFRESH COMPLETE")
        else:
            print("REFRESH COMPLETED WITH ERRORS")
        print("=" * 70)

        # Show updated status
        print()
        print_status(db)

        return success

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Check data freshness and refresh if stale"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force refresh all data regardless of age"
    )
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Just show status, don't refresh"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=30,
        help="Days before data is considered stale (default: 30)"
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Try to use Congress.gov API instead of seed files"
    )

    args = parser.parse_args()

    if args.status:
        db = SessionLocal()
        try:
            print_status(db)
        finally:
            db.close()
    else:
        success = check_and_refresh(
            max_age_days=args.days,
            force=args.force,
            use_api=args.api
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

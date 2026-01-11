#!/usr/bin/env python3
"""
Seed the database with trade-related votes from JSON file.

This script loads key trade votes for testing without requiring
an API key. Use this for initial setup and development.

Usage:
    python scripts/seed_votes.py
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.models import (
    SessionLocal,
    Bill,
    Vote,
    Member,
    VoteChoice,
)

SEED_FILE = project_root / "data" / "seed" / "trade_votes.json"


def parse_vote_choice(category: str) -> VoteChoice:
    """Parse vote category to enum."""
    vote_map = {
        "yea": VoteChoice.YES,
        "nay": VoteChoice.NO,
        "not_voting": VoteChoice.NOT_VOTING,
        "abstain": VoteChoice.ABSTAIN,
    }
    return vote_map.get(category, VoteChoice.NOT_VOTING)


def load_seed_data() -> dict:
    """Load seed data from JSON file."""
    if not SEED_FILE.exists():
        print(f"ERROR: Seed file not found: {SEED_FILE}")
        sys.exit(1)

    with open(SEED_FILE, "r") as f:
        return json.load(f)


def seed_bills_and_votes(data: dict):
    """Seed bills and votes from data."""
    db = SessionLocal()

    try:
        bills_added = 0
        bills_updated = 0
        votes_added = 0
        votes_skipped = 0

        for bill_data in data["bills"]:
            bill_id = bill_data["id"]
            print(f"\nProcessing bill: {bill_id}")
            print(f"  Title: {bill_data.get('short_title', bill_data.get('title', 'N/A'))}")

            # Parse vote date
            vote_date = datetime.now()
            if bill_data.get("vote_date"):
                try:
                    vote_date = datetime.strptime(bill_data["vote_date"], "%Y-%m-%d")
                except ValueError:
                    pass

            # Check if bill exists
            existing_bill = db.query(Bill).filter(Bill.id == bill_id).first()

            if existing_bill:
                # Update existing bill
                existing_bill.title = bill_data.get("title")
                existing_bill.short_title = bill_data.get("short_title")
                existing_bill.description = bill_data.get("description")
                existing_bill.position_indicator = bill_data.get("position_indicator", 0)
                existing_bill.position_reasoning = bill_data.get("position_reasoning")
                existing_bill.issue_tags = ["trade-policy"]
                bills_updated += 1
                bill = existing_bill
            else:
                # Create new bill
                bill = Bill(
                    id=bill_id,
                    congress=bill_data.get("congress"),
                    bill_type=bill_data.get("bill_type"),
                    bill_number=bill_data.get("bill_number"),
                    title=bill_data.get("title"),
                    short_title=bill_data.get("short_title"),
                    description=bill_data.get("description"),
                    issue_tags=["trade-policy"],
                    position_indicator=bill_data.get("position_indicator", 0),
                    position_reasoning=bill_data.get("position_reasoning"),
                    introduced_date=vote_date,
                )
                db.add(bill)
                bills_added += 1

            db.commit()

            # Process votes
            votes_data = bill_data.get("votes", {})
            roll_call_id = bill_data.get("roll_call_id", f"rc-{bill_id}")

            for vote_category, member_ids in votes_data.items():
                vote_choice = parse_vote_choice(vote_category)

                for member_id in member_ids:
                    # Check if member exists in our database
                    member = db.query(Member).filter(Member.id == member_id).first()
                    if not member:
                        votes_skipped += 1
                        continue

                    # Check if vote already exists
                    existing_vote = db.query(Vote).filter(
                        Vote.member_id == member_id,
                        Vote.bill_id == bill_id,
                    ).first()

                    if existing_vote:
                        # Update vote if different
                        if existing_vote.vote != vote_choice:
                            existing_vote.vote = vote_choice
                            existing_vote.vote_date = vote_date
                    else:
                        # Create new vote
                        vote = Vote(
                            member_id=member_id,
                            bill_id=bill_id,
                            vote=vote_choice,
                            vote_date=vote_date,
                            roll_call_id=roll_call_id,
                            session=1,
                        )
                        db.add(vote)
                        votes_added += 1

            db.commit()

            # Count votes for this bill
            bill_votes = db.query(Vote).filter(Vote.bill_id == bill_id).count()
            print(f"  Position indicator: {bill_data.get('position_indicator', 0):.2f}")
            print(f"  Votes recorded: {bill_votes}")

        print(f"\n{'='*60}")
        print(f"Seeding complete!")
        print(f"Bills: {bills_added} added, {bills_updated} updated")
        print(f"Votes: {votes_added} added, {votes_skipped} skipped (member not in DB)")

    finally:
        db.close()


def print_summary():
    """Print summary of votes in database."""
    db = SessionLocal()
    try:
        total_bills = db.query(Bill).count()
        trade_bills = db.query(Bill).filter(
            Bill.issue_tags.contains(["trade-policy"])
        ).count()
        total_votes = db.query(Vote).count()

        print(f"\n{'='*60}")
        print("DATABASE SUMMARY")
        print(f"{'='*60}")
        print(f"Total bills: {total_bills}")
        print(f"Trade-related bills: {trade_bills}")
        print(f"Total votes: {total_votes}")

        # Show vote breakdown by bill
        print("\nVotes per bill:")
        bills = db.query(Bill).all()
        for bill in bills:
            vote_count = db.query(Vote).filter(Vote.bill_id == bill.id).count()
            yes_count = db.query(Vote).filter(
                Vote.bill_id == bill.id,
                Vote.vote == VoteChoice.YES
            ).count()
            no_count = db.query(Vote).filter(
                Vote.bill_id == bill.id,
                Vote.vote == VoteChoice.NO
            ).count()
            print(f"  {bill.short_title or bill.id}: {vote_count} votes ({yes_count}Y/{no_count}N)")

    finally:
        db.close()


def main():
    """Main function."""
    print("=" * 60)
    print("Trade Votes Seeding")
    print("=" * 60)
    print()

    # Load seed data
    print(f"Loading seed data from: {SEED_FILE}")
    data = load_seed_data()
    print(f"Found {len(data['bills'])} bills in seed file")
    print()

    # Seed the database
    print("Seeding database...")
    seed_bills_and_votes(data)

    # Print summary
    print_summary()


if __name__ == "__main__":
    main()

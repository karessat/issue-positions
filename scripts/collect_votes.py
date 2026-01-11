#!/usr/bin/env python3
"""
Collect trade-related votes from Congress.gov API.

This script:
1. Searches for trade-related bills using keywords
2. Fetches roll call votes on those bills
3. Stores bills with position indicators
4. Stores individual member votes

Usage:
    python scripts/collect_votes.py [--congress 118] [--limit 50]

Requires:
    CONGRESS_API_KEY environment variable
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
from dotenv import load_dotenv

from api.models import (
    SessionLocal,
    Bill,
    Vote,
    Member,
    VoteChoice,
)

load_dotenv(project_root / ".env")

CONGRESS_API_BASE = "https://api.congress.gov/v3"

# Trade-related keywords for bill search
TRADE_KEYWORDS = [
    "tariff",
    "trade agreement",
    "trade promotion",
    "import",
    "export",
    "customs",
    "USMCA",
    "TPP",
    "trade deficit",
    "trade war",
    "dumping",
    "trade remedy",
    "Buy American",
    "made in America",
    "outsourcing",
    "offshoring",
    "free trade",
    "protectionist",
    "World Trade Organization",
    "WTO",
]

# Bill subjects that indicate trade relevance
TRADE_SUBJECTS = [
    "Foreign trade and international finance",
    "Tariffs",
    "Trade agreements and negotiations",
    "Trade restrictions",
    "Customs enforcement",
    "Import restrictions",
    "Export controls",
]


def get_api_key() -> str:
    """Get Congress.gov API key from environment."""
    key = os.getenv("CONGRESS_API_KEY")
    if not key:
        print("ERROR: CONGRESS_API_KEY not found.")
        print("Get a free API key at: https://api.congress.gov/sign-up/")
        sys.exit(1)
    return key


def search_trade_bills(
    client: httpx.Client,
    api_key: str,
    congress: int,
    limit: int = 50,
) -> list[dict]:
    """Search for trade-related bills."""
    bills = []

    print(f"Searching for trade-related bills in Congress {congress}...")

    for keyword in TRADE_KEYWORDS[:5]:  # Limit keywords to avoid rate limits
        print(f"  Searching: '{keyword}'...")

        url = f"{CONGRESS_API_BASE}/bill/{congress}"
        params = {
            "api_key": api_key,
            "format": "json",
            "limit": 20,
            "sort": "updateDate+desc",
        }

        try:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            for bill in data.get("bills", []):
                # Check if bill title contains trade keywords
                title = (bill.get("title") or "").lower()
                if any(kw.lower() in title for kw in TRADE_KEYWORDS):
                    if bill not in bills:
                        bills.append(bill)

            time.sleep(0.5)  # Rate limiting

        except Exception as e:
            print(f"    Error searching: {e}")
            continue

    print(f"Found {len(bills)} potential trade-related bills")
    return bills[:limit]


def get_bill_details(
    client: httpx.Client,
    api_key: str,
    congress: int,
    bill_type: str,
    bill_number: int,
) -> Optional[dict]:
    """Get detailed bill information."""
    url = f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{bill_number}"
    params = {"api_key": api_key, "format": "json"}

    try:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("bill", {})
    except Exception as e:
        print(f"  Error fetching bill details: {e}")
        return None


def get_bill_actions(
    client: httpx.Client,
    api_key: str,
    congress: int,
    bill_type: str,
    bill_number: int,
) -> list[dict]:
    """Get bill actions to find roll call votes."""
    url = f"{CONGRESS_API_BASE}/bill/{congress}/{bill_type}/{bill_number}/actions"
    params = {"api_key": api_key, "format": "json", "limit": 100}

    try:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("actions", [])
    except Exception as e:
        print(f"  Error fetching actions: {e}")
        return []


def get_roll_call_vote(
    client: httpx.Client,
    api_key: str,
    congress: int,
    chamber: str,
    session: int,
    roll_call_number: int,
) -> Optional[dict]:
    """Get individual roll call vote details."""
    chamber_code = "senate" if chamber.lower() == "senate" else "house"
    url = f"{CONGRESS_API_BASE}/roll-call/{congress}/{chamber_code}/{session}/{roll_call_number}"
    params = {"api_key": api_key, "format": "json"}

    try:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("rollCall", {})
    except Exception as e:
        print(f"  Error fetching roll call: {e}")
        return None


def parse_vote_choice(vote_str: str) -> VoteChoice:
    """Parse vote string to enum."""
    vote_map = {
        "yea": VoteChoice.YES,
        "yes": VoteChoice.YES,
        "aye": VoteChoice.YES,
        "nay": VoteChoice.NO,
        "no": VoteChoice.NO,
        "not voting": VoteChoice.NOT_VOTING,
        "present": VoteChoice.ABSTAIN,
        "abstain": VoteChoice.ABSTAIN,
    }
    return vote_map.get(vote_str.lower(), VoteChoice.NOT_VOTING)


def determine_position_indicator(bill: dict) -> tuple[float, str]:
    """
    Determine what a YES vote on this bill indicates on the trade spectrum.

    Returns:
        (position_indicator, reasoning)
        - Positive values (+0.5 to +1.0): YES = protectionist
        - Negative values (-0.5 to -1.0): YES = free trade
        - Near zero: mixed/unclear
    """
    title = (bill.get("title") or "").lower()
    short_title = (bill.get("short_title") or "").lower()
    combined = f"{title} {short_title}"

    # Protectionist indicators (YES = protectionist, positive score)
    protectionist_keywords = [
        ("tariff", 0.7),
        ("buy american", 0.8),
        ("made in america", 0.7),
        ("anti-dumping", 0.6),
        ("import restriction", 0.7),
        ("trade enforcement", 0.5),
        ("protect domestic", 0.8),
        ("american jobs", 0.6),
    ]

    # Free trade indicators (YES = free trade, negative score)
    free_trade_keywords = [
        ("trade agreement", -0.7),
        ("trade promotion", -0.8),
        ("free trade", -0.9),
        ("reduce tariff", -0.7),
        ("trade liberalization", -0.8),
        ("export promotion", -0.5),
        ("usmca", -0.6),  # Generally considered pro-trade
        ("tpp", -0.8),
    ]

    score = 0.0
    reasons = []

    for keyword, weight in protectionist_keywords:
        if keyword in combined:
            score += weight
            reasons.append(f"Contains '{keyword}' (+{weight})")

    for keyword, weight in free_trade_keywords:
        if keyword in combined:
            score += weight  # Weight is already negative
            reasons.append(f"Contains '{keyword}' ({weight})")

    # Normalize to -1 to 1 range
    score = max(-1.0, min(1.0, score))

    reasoning = "; ".join(reasons) if reasons else "No clear trade indicators found"

    return score, reasoning


def store_bill(db, bill_data: dict, congress: int) -> Optional[Bill]:
    """Store a bill in the database."""
    bill_type = bill_data.get("type", "").lower()
    bill_number = bill_data.get("number")

    if not bill_type or not bill_number:
        return None

    bill_id = f"{bill_type}{bill_number}-{congress}"

    # Check if exists
    existing = db.query(Bill).filter(Bill.id == bill_id).first()
    if existing:
        return existing

    position_indicator, reasoning = determine_position_indicator(bill_data)

    # Parse dates
    introduced_date = None
    if bill_data.get("introducedDate"):
        try:
            introduced_date = datetime.strptime(
                bill_data["introducedDate"], "%Y-%m-%d"
            )
        except ValueError:
            pass

    bill = Bill(
        id=bill_id,
        congress=congress,
        bill_type=bill_type,
        bill_number=bill_number,
        title=bill_data.get("title"),
        short_title=bill_data.get("shortTitle"),
        description=bill_data.get("summary", {}).get("text") if isinstance(bill_data.get("summary"), dict) else None,
        issue_tags=["trade-policy"],
        position_indicator=position_indicator,
        position_reasoning=reasoning,
        introduced_date=introduced_date,
    )

    db.add(bill)
    db.commit()
    return bill


def store_vote(
    db,
    member_id: str,
    bill_id: str,
    vote_choice: VoteChoice,
    vote_date: datetime,
    roll_call_id: str,
    session: int,
) -> Optional[Vote]:
    """Store a vote in the database."""
    # Verify member exists
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        return None

    # Check if vote already exists
    existing = db.query(Vote).filter(
        Vote.member_id == member_id,
        Vote.bill_id == bill_id,
        Vote.roll_call_id == roll_call_id,
    ).first()

    if existing:
        return existing

    vote = Vote(
        member_id=member_id,
        bill_id=bill_id,
        vote=vote_choice,
        vote_date=vote_date,
        roll_call_id=roll_call_id,
        session=session,
    )

    db.add(vote)
    return vote


def collect_votes(congress: int = 118, limit: int = 50):
    """Main collection function."""
    api_key = get_api_key()
    db = SessionLocal()

    try:
        with httpx.Client(timeout=30.0) as client:
            # Search for trade bills
            bills = search_trade_bills(client, api_key, congress, limit)

            bills_stored = 0
            votes_stored = 0

            for i, bill_data in enumerate(bills):
                bill_type = bill_data.get("type", "").lower()
                bill_number = bill_data.get("number")

                print(f"\n[{i+1}/{len(bills)}] Processing {bill_type.upper()}{bill_number}...")
                print(f"  Title: {bill_data.get('title', 'N/A')[:60]}...")

                # Get full bill details
                details = get_bill_details(
                    client, api_key, congress, bill_type, bill_number
                )
                if details:
                    bill_data.update(details)

                # Store bill
                bill = store_bill(db, bill_data, congress)
                if bill:
                    bills_stored += 1
                    print(f"  Position indicator: {bill.position_indicator:.2f}")

                # Get actions to find roll calls
                actions = get_bill_actions(
                    client, api_key, congress, bill_type, bill_number
                )

                for action in actions:
                    # Look for roll call votes
                    roll_call = action.get("rollCallNumber")
                    if not roll_call:
                        continue

                    chamber = action.get("chamber", "")
                    if chamber.lower() != "senate":
                        continue  # MVP: Senate only

                    # Get roll call details
                    roll_call_data = get_roll_call_vote(
                        client, api_key, congress, chamber, 1, roll_call
                    )

                    if not roll_call_data:
                        continue

                    vote_date = datetime.now()  # Default
                    if roll_call_data.get("date"):
                        try:
                            vote_date = datetime.strptime(
                                roll_call_data["date"], "%Y-%m-%d"
                            )
                        except ValueError:
                            pass

                    # Process individual votes
                    members_votes = roll_call_data.get("members", [])
                    for mv in members_votes:
                        bioguide_id = mv.get("bioguideId")
                        vote_str = mv.get("votePosition", "")

                        if bioguide_id and vote_str and bill:
                            vote = store_vote(
                                db,
                                bioguide_id,
                                bill.id,
                                parse_vote_choice(vote_str),
                                vote_date,
                                f"s{roll_call}-{congress}",
                                1,
                            )
                            if vote:
                                votes_stored += 1

                    db.commit()

                time.sleep(1)  # Rate limiting

            print(f"\n{'='*60}")
            print(f"Collection complete!")
            print(f"Bills stored: {bills_stored}")
            print(f"Votes stored: {votes_stored}")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Collect trade-related votes")
    parser.add_argument("--congress", type=int, default=118, help="Congress number")
    parser.add_argument("--limit", type=int, default=50, help="Max bills to process")
    args = parser.parse_args()

    print("=" * 60)
    print("Trade Vote Collection Pipeline")
    print("=" * 60)
    print(f"Congress: {args.congress}")
    print(f"Limit: {args.limit} bills")
    print()

    collect_votes(args.congress, args.limit)


if __name__ == "__main__":
    main()

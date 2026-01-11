#!/usr/bin/env python3
"""
Calculate position scores for all members on trade policy.

For each senator, calculates a position score from -1.0 (free trade)
to +1.0 (protectionist) based on their voting record.

Usage:
    python scripts/calculate_scores.py
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from api.models import (
    SessionLocal,
    Member,
    Bill,
    Vote,
    Position,
    Issue,
    VoteChoice,
    Chamber,
    Party,
)
from scripts.utils.metadata import update_metadata


def calculate_vote_score(vote: Vote, bill: Bill) -> Optional[float]:
    """
    Calculate score contribution from a single vote.

    - YES vote: returns the bill's position_indicator
    - NO vote: returns the opposite of the indicator
    - NOT_VOTING/ABSTAIN: returns None (excluded from calculation)
    """
    if bill.position_indicator is None:
        return None

    if vote.vote == VoteChoice.YES:
        return bill.position_indicator
    elif vote.vote == VoteChoice.NO:
        return -bill.position_indicator
    else:
        # Not voting or abstain - exclude from calculation
        return None


def calculate_member_position(db, member: Member, issue_slug: str = "trade-policy") -> dict:
    """
    Calculate a member's position score on an issue.

    Returns dict with:
        - score: float from -1.0 to +1.0
        - confidence: float from 0.0 to 1.0
        - vote_count: number of votes used
        - votes: list of individual vote contributions
    """
    # Get all bills tagged with this issue
    bills = db.query(Bill).filter(
        Bill.issue_tags.contains([issue_slug])
    ).all()

    if not bills:
        return {"score": None, "confidence": 0, "vote_count": 0, "votes": []}

    bill_ids = [b.id for b in bills]
    bill_map = {b.id: b for b in bills}

    # Get member's votes on these bills
    votes = db.query(Vote).filter(
        Vote.member_id == member.id,
        Vote.bill_id.in_(bill_ids)
    ).all()

    # Calculate score contributions
    contributions = []
    vote_details = []

    for vote in votes:
        bill = bill_map.get(vote.bill_id)
        if not bill:
            continue

        score_contribution = calculate_vote_score(vote, bill)

        if score_contribution is not None:
            contributions.append(score_contribution)
            vote_details.append({
                "bill_id": bill.id,
                "bill_title": bill.short_title or bill.title,
                "vote": vote.vote.value,
                "bill_indicator": bill.position_indicator,
                "contribution": score_contribution,
            })

    if not contributions:
        return {"score": None, "confidence": 0, "vote_count": 0, "votes": []}

    # Calculate average score
    score = sum(contributions) / len(contributions)

    # Clamp to -1 to 1 range
    score = max(-1.0, min(1.0, score))

    # Calculate confidence based on vote count
    # More votes = higher confidence, max confidence at 5+ votes
    max_votes_for_full_confidence = 5
    confidence = min(1.0, len(contributions) / max_votes_for_full_confidence)

    return {
        "score": score,
        "confidence": confidence,
        "vote_count": len(contributions),
        "votes": vote_details,
    }


def store_position(db, member: Member, issue: Issue, position_data: dict):
    """Store or update a position in the database."""
    if position_data["score"] is None:
        return None

    # Check for existing position
    existing = db.query(Position).filter(
        Position.member_id == member.id,
        Position.issue_id == issue.id,
    ).first()

    if existing:
        existing.score = position_data["score"]
        existing.confidence = position_data["confidence"]
        existing.vote_score = position_data["score"]  # For now, only using votes
        existing.evidence_count = position_data["vote_count"]
        existing.last_updated = datetime.utcnow()
        return existing
    else:
        position = Position(
            member_id=member.id,
            issue_id=issue.id,
            score=position_data["score"],
            confidence=position_data["confidence"],
            vote_score=position_data["score"],
            evidence_count=position_data["vote_count"],
        )
        db.add(position)
        return position


def calculate_all_positions():
    """Calculate positions for all senators on trade policy."""
    db = SessionLocal()

    try:
        # Get the trade policy issue
        issue = db.query(Issue).filter(Issue.slug == "trade-policy").first()
        if not issue:
            print("ERROR: Trade policy issue not found. Run init_db.py first.")
            return

        # Get all senators
        senators = db.query(Member).filter(
            Member.chamber == Chamber.SENATE
        ).all()

        print(f"Calculating positions for {len(senators)} senators...")
        print()

        positions_calculated = 0
        positions_skipped = 0

        for member in senators:
            position_data = calculate_member_position(db, member, "trade-policy")

            if position_data["score"] is not None:
                store_position(db, member, issue, position_data)
                positions_calculated += 1
            else:
                positions_skipped += 1

        db.commit()

        print(f"Positions calculated: {positions_calculated}")
        print(f"Skipped (no votes): {positions_skipped}")

        # Update metadata
        update_metadata(
            db,
            data_type="positions",
            record_count=positions_calculated,
            source="calculated",
            notes=f"Trade policy positions for {positions_calculated} senators"
        )
        print(f"Updated metadata: {positions_calculated} positions")

    finally:
        db.close()


def display_spectrum():
    """Display the position spectrum for all senators."""
    db = SessionLocal()

    try:
        issue = db.query(Issue).filter(Issue.slug == "trade-policy").first()
        if not issue:
            return

        positions = db.query(Position).filter(
            Position.issue_id == issue.id
        ).order_by(Position.score).all()

        if not positions:
            print("No positions calculated yet.")
            return

        print()
        print("=" * 70)
        print(f"TRADE POLICY SPECTRUM: {issue.spectrum_left_label} ← → {issue.spectrum_right_label}")
        print("=" * 70)
        print()

        # Create ASCII visualization
        width = 60

        print(f"{'Free Trade':<15} {'':^30} {'Protectionist':>15}")
        print(f"-1.0{' ' * (width - 8)}+1.0")
        print("├" + "─" * width + "┤")

        # Group positions into buckets for display
        buckets = {}
        for pos in positions:
            member = db.query(Member).filter(Member.id == pos.member_id).first()
            # Map score (-1 to 1) to position (0 to width)
            x = int((pos.score + 1) / 2 * width)
            x = max(0, min(width, x))

            if x not in buckets:
                buckets[x] = []
            buckets[x].append((member, pos))

        # Draw spectrum with party colors
        line = [" "] * (width + 1)
        for x, members in buckets.items():
            # Use first letter of party for multiple members at same position
            if len(members) == 1:
                party = members[0][0].party
                line[x] = "D" if party == Party.DEMOCRAT else "R" if party == Party.REPUBLICAN else "I"
            else:
                line[x] = str(min(len(members), 9))

        print("│" + "".join(line) + "│")
        print("└" + "─" * width + "┘")
        print()
        print("Legend: D=Democrat, R=Republican, I=Independent, #=multiple senators")

        # Show distribution statistics
        print()
        print("=" * 70)
        print("DISTRIBUTION BY PARTY")
        print("=" * 70)

        for party in [Party.DEMOCRAT, Party.REPUBLICAN, Party.INDEPENDENT]:
            party_positions = [p for p in positions
                            if db.query(Member).filter(Member.id == p.member_id).first().party == party]
            if party_positions:
                scores = [p.score for p in party_positions]
                avg = sum(scores) / len(scores)
                min_s = min(scores)
                max_s = max(scores)
                print(f"\n{party.name} ({len(party_positions)} senators):")
                print(f"  Range: {min_s:+.2f} to {max_s:+.2f}")
                print(f"  Average: {avg:+.2f}")

        # Show extremes and notable positions
        print()
        print("=" * 70)
        print("POSITION DETAILS (sorted by score)")
        print("=" * 70)

        # Most free trade
        print("\nMost Free Trade (lowest scores):")
        for pos in positions[:5]:
            member = db.query(Member).filter(Member.id == pos.member_id).first()
            print(f"  {pos.score:+.2f}  {member.name} ({member.party.value}-{member.state})")

        # Most protectionist
        print("\nMost Protectionist (highest scores):")
        for pos in positions[-5:]:
            member = db.query(Member).filter(Member.id == pos.member_id).first()
            print(f"  {pos.score:+.2f}  {member.name} ({member.party.value}-{member.state})")

        # Cross-party overlap (Republicans below 0, Democrats above 0)
        print("\nCross-Party Overlap:")

        free_trade_republicans = [(p, db.query(Member).filter(Member.id == p.member_id).first())
                                   for p in positions
                                   if p.score < 0 and db.query(Member).filter(Member.id == p.member_id).first().party == Party.REPUBLICAN]

        protectionist_democrats = [(p, db.query(Member).filter(Member.id == p.member_id).first())
                                    for p in positions
                                    if p.score > 0 and db.query(Member).filter(Member.id == p.member_id).first().party == Party.DEMOCRAT]

        if free_trade_republicans:
            print(f"\n  Republicans leaning free trade ({len(free_trade_republicans)}):")
            for pos, member in sorted(free_trade_republicans, key=lambda x: x[0].score)[:5]:
                print(f"    {pos.score:+.2f}  {member.name} ({member.state})")

        if protectionist_democrats:
            print(f"\n  Democrats leaning protectionist ({len(protectionist_democrats)}):")
            for pos, member in sorted(protectionist_democrats, key=lambda x: -x[0].score)[:5]:
                print(f"    {pos.score:+.2f}  {member.name} ({member.state})")

    finally:
        db.close()


def main():
    print("=" * 70)
    print("POSITION SCORING - Trade Policy")
    print("=" * 70)
    print()

    calculate_all_positions()
    display_spectrum()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Analyze statements using Claude to extract trade policy positions.

This script:
1. Fetches unanalyzed statements from the database
2. Sends each to Claude for position extraction
3. Stores the extracted position score and reasoning
4. Creates Evidence records for position calculation

Usage:
    python scripts/analyze_statements.py [--limit 10] [--reanalyze]

Requires:
    ANTHROPIC_API_KEY environment variable
"""
import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from api.models import (
    SessionLocal,
    Statement,
    Member,
    Issue,
    Position,
    Evidence,
    EvidenceType,
)

# Check for API key
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# The prompt template for position extraction
ANALYSIS_PROMPT = """You are an expert at analyzing political statements to determine positions on trade policy.

Given a statement from a U.S. Senator, extract their position on the trade policy spectrum:

SPECTRUM:
- Score -1.0: Strongly FREE TRADE (supports trade agreements, opposes tariffs, favors open markets)
- Score 0.0: MIXED/NEUTRAL (balanced view, supports some protections and some free trade)
- Score +1.0: Strongly PROTECTIONIST (supports tariffs, Buy American, opposes trade deals, protects domestic industry)

KEY INDICATORS:
Free Trade (-1.0 to -0.5):
- Supports trade agreements (USMCA, TPP, etc.)
- Opposes tariffs or wants to reduce them
- Emphasizes benefits of open markets, lower prices
- Supports export promotion

Mixed/Moderate (-0.5 to +0.5):
- Supports "fair trade" with enforcement
- Wants targeted (not broad) protections
- Balances worker protection with market access

Protectionist (+0.5 to +1.0):
- Supports tariffs to protect American jobs
- Supports Buy American provisions
- Opposes trade deals that "ship jobs overseas"
- Emphasizes protecting domestic manufacturing

STATEMENT TO ANALYZE:
Senator: {senator_name} ({party}-{state})
Date: {date}
Statement: "{statement_text}"

Respond with a JSON object containing:
{{
  "score": <float from -1.0 to +1.0>,
  "confidence": <float from 0.0 to 1.0 indicating how clearly the statement expresses a position>,
  "reasoning": "<brief explanation of why you assigned this score>",
  "key_phrases": ["<phrase 1>", "<phrase 2>", ...]
}}

Be objective and base your analysis only on what the statement actually says, not on the senator's party or general reputation."""


def get_anthropic_client():
    """Get Anthropic client."""
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not found in environment.")
        print("Get an API key at: https://console.anthropic.com/")
        sys.exit(1)

    try:
        import anthropic
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        print("ERROR: anthropic package not installed.")
        print("Run: pip install anthropic")
        sys.exit(1)


def analyze_statement(client, statement: Statement, member: Member) -> dict:
    """
    Send a statement to Claude for analysis.

    Returns dict with score, confidence, reasoning, key_phrases.
    """
    prompt = ANALYSIS_PROMPT.format(
        senator_name=member.name,
        party=member.party.value,
        state=member.state,
        date=statement.source_date.strftime("%Y-%m-%d") if statement.source_date else "Unknown",
        statement_text=statement.text[:2000],  # Limit text length
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract the text response
        response_text = response.content[0].text

        # Parse JSON from response
        # Handle case where response might have markdown code blocks
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text

        result = json.loads(json_str.strip())

        # Validate and clamp values
        result["score"] = max(-1.0, min(1.0, float(result.get("score", 0))))
        result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
        result["reasoning"] = result.get("reasoning", "")
        result["key_phrases"] = result.get("key_phrases", [])

        return result

    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e}")
        print(f"    Response was: {response_text[:200]}...")
        return None
    except Exception as e:
        print(f"    API error: {e}")
        return None


def store_analysis(db, statement: Statement, analysis: dict):
    """Store analysis results in the statement record."""
    statement.analyzed = 1
    statement.analysis_date = datetime.utcnow()

    # Store analysis in a way we can retrieve later
    # We'll add these as JSON in the notes or create Evidence records
    db.commit()

    return analysis


def create_evidence_record(
    db,
    statement: Statement,
    analysis: dict,
    position: Position,
) -> Evidence:
    """Create an Evidence record linking the statement to a position."""

    # Check if evidence already exists for this statement
    existing = db.query(Evidence).filter(
        Evidence.position_id == position.id,
        Evidence.type == EvidenceType.STATEMENT,
        Evidence.source_url == statement.source_url,
        Evidence.source_date == statement.source_date,
    ).first()

    if existing:
        # Update existing
        existing.extracted_position = analysis["score"]
        existing.extraction_confidence = analysis["confidence"]
        existing.extraction_reasoning = analysis["reasoning"]
        return existing

    evidence = Evidence(
        position_id=position.id,
        type=EvidenceType.STATEMENT,
        source_url=statement.source_url,
        source_name="Congressional Record",
        source_date=statement.source_date,
        raw_text=statement.text[:1000],  # Store first 1000 chars
        extracted_position=analysis["score"],
        extraction_confidence=analysis["confidence"],
        extraction_reasoning=analysis["reasoning"],
        weight=1.0,
    )

    db.add(evidence)
    return evidence


def analyze_statements(limit: int = 10, reanalyze: bool = False):
    """Main analysis function."""
    client = get_anthropic_client()
    db = SessionLocal()

    try:
        # Get trade policy issue
        issue = db.query(Issue).filter(Issue.slug == "trade-policy").first()
        if not issue:
            print("ERROR: Trade policy issue not found.")
            return

        # Get statements to analyze
        query = db.query(Statement).filter(
            Statement.issue_tags.contains("trade-policy")
        )

        if not reanalyze:
            query = query.filter(Statement.analyzed == 0)

        statements = query.limit(limit).all()

        if not statements:
            print("No statements to analyze.")
            return

        print(f"Analyzing {len(statements)} statements...")
        print()

        analyzed_count = 0
        error_count = 0

        for i, statement in enumerate(statements):
            member = db.query(Member).filter(Member.id == statement.member_id).first()
            if not member:
                print(f"[{i+1}/{len(statements)}] Skipping: Member not found")
                continue

            print(f"[{i+1}/{len(statements)}] {member.name} ({member.party.value}-{member.state})")
            print(f"    Statement: {statement.text[:60]}...")

            # Analyze with Claude
            analysis = analyze_statement(client, statement, member)

            if analysis is None:
                error_count += 1
                continue

            print(f"    Score: {analysis['score']:+.2f} (confidence: {analysis['confidence']:.2f})")
            print(f"    Reasoning: {analysis['reasoning'][:80]}...")

            # Update statement record
            statement.analyzed = 1
            statement.analysis_date = datetime.utcnow()

            # Get or create position for this member
            position = db.query(Position).filter(
                Position.member_id == member.id,
                Position.issue_id == issue.id,
            ).first()

            if not position:
                # Create a new position record
                position = Position(
                    member_id=member.id,
                    issue_id=issue.id,
                    score=0.0,  # Will be recalculated
                    confidence=0.0,
                    evidence_count=0,
                )
                db.add(position)
                db.commit()

            # Create evidence record
            create_evidence_record(db, statement, analysis, position)

            analyzed_count += 1
            db.commit()

            print()

        print("=" * 60)
        print(f"Analysis complete!")
        print(f"Statements analyzed: {analyzed_count}")
        print(f"Errors: {error_count}")
        print()
        print("Run 'python scripts/calculate_scores.py' to update position scores.")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze statements using Claude for position extraction"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=10,
        help="Maximum number of statements to analyze (default: 10)"
    )
    parser.add_argument(
        "--reanalyze", "-r",
        action="store_true",
        help="Re-analyze statements that were already analyzed"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Statement Analysis Pipeline")
    print("=" * 60)
    print(f"Model: claude-sonnet-4-20250514")
    print(f"Limit: {args.limit}")
    print(f"Reanalyze: {args.reanalyze}")
    print()

    analyze_statements(limit=args.limit, reanalyze=args.reanalyze)


if __name__ == "__main__":
    main()

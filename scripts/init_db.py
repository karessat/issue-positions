#!/usr/bin/env python3
"""
Initialize the Issue Positions database.

This script:
1. Creates the SQLite database and all tables
2. Seeds the database with the Trade Policy issue (MVP)

Usage:
    python scripts/init_db.py
"""
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime
from api.models import (
    Base,
    engine,
    SessionLocal,
    Issue,
)


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")


def seed_trade_policy_issue(db):
    """Seed the Trade Policy issue for MVP."""
    # Check if already exists
    existing = db.query(Issue).filter(Issue.slug == "trade-policy").first()
    if existing:
        print("Trade Policy issue already exists, skipping.")
        return existing

    trade_policy = Issue(
        name="Trade Policy",
        slug="trade-policy",
        description=(
            "Positions on international trade agreements, tariffs, and protectionist "
            "policies. This issue often scrambles traditional left-right alignment, "
            "with populist vs. establishment splits appearing in both parties."
        ),
        spectrum_left_label="Free Trade",
        spectrum_right_label="Protectionist",
        spectrum_description=(
            "The spectrum ranges from strong support for free trade and international "
            "trade agreements (left/-1.0) to strong support for protectionist policies "
            "like tariffs and Buy American provisions (right/+1.0). Mixed or nuanced "
            "positions cluster near the center (0)."
        ),
        scoring_indicators=[
            {
                "indicator": "Support for tariffs",
                "direction": "positive",
                "description": "Higher tariff support = more protectionist (+)",
            },
            {
                "indicator": "Support for trade agreements (TPP, USMCA, etc.)",
                "direction": "negative",
                "description": "Support for trade deals = more free trade (-)",
            },
            {
                "indicator": "Buy American provisions",
                "direction": "positive",
                "description": "Support for Buy American = more protectionist (+)",
            },
            {
                "indicator": "Opposition to outsourcing",
                "direction": "positive",
                "description": "Anti-outsourcing stance = more protectionist (+)",
            },
            {
                "indicator": "Support for export promotion",
                "direction": "negative",
                "description": "Pro-export policies = more free trade oriented (-)",
            },
        ],
    )

    db.add(trade_policy)
    db.commit()
    db.refresh(trade_policy)
    print(f"Created issue: {trade_policy.name} (id={trade_policy.id})")
    return trade_policy


def main():
    """Main initialization function."""
    print("=" * 60)
    print("Issue Positions Database Initialization")
    print("=" * 60)
    print()

    # Create tables
    create_tables()
    print()

    # Seed data
    print("Seeding initial data...")
    db = SessionLocal()
    try:
        seed_trade_policy_issue(db)
        print()
        print("Database initialization complete!")
        print(f"Database location: {engine.url}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

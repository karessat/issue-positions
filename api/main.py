"""FastAPI application for Issue Positions API."""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional

from .models import (
    get_db,
    Member,
    Issue,
    Position,
    Bill,
    Vote,
    Statement,
    DataMetadata,
    Chamber,
    Party,
    VoteChoice,
)

app = FastAPI(
    title="Issue Positions API",
    description="API for congressional position data on policy issues",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Issue Positions API", "version": "0.1.0"}


@app.get("/api/issues")
def get_issues(db: Session = Depends(get_db)):
    """Get all available issues."""
    issues = db.query(Issue).all()
    return [
        {
            "id": issue.id,
            "name": issue.name,
            "slug": issue.slug,
            "description": issue.description,
            "spectrum_left_label": issue.spectrum_left_label,
            "spectrum_right_label": issue.spectrum_right_label,
        }
        for issue in issues
    ]


@app.get("/api/issues/{slug}")
def get_issue(slug: str, db: Session = Depends(get_db)):
    """Get a specific issue by slug."""
    issue = db.query(Issue).filter(Issue.slug == slug).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    return {
        "id": issue.id,
        "name": issue.name,
        "slug": issue.slug,
        "description": issue.description,
        "spectrum_left_label": issue.spectrum_left_label,
        "spectrum_right_label": issue.spectrum_right_label,
        "spectrum_description": issue.spectrum_description,
    }


@app.get("/api/issues/{slug}/positions")
def get_positions(
    slug: str,
    chamber: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get all member positions for an issue."""
    issue = db.query(Issue).filter(Issue.slug == slug).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    query = db.query(Position).filter(Position.issue_id == issue.id)

    positions = query.all()

    result = []
    for pos in positions:
        member = db.query(Member).filter(Member.id == pos.member_id).first()
        if not member:
            continue

        # Filter by chamber if specified
        if chamber:
            if chamber.lower() == "senate" and member.chamber != Chamber.SENATE:
                continue
            if chamber.lower() == "house" and member.chamber != Chamber.HOUSE:
                continue

        result.append({
            "member_id": member.id,
            "name": member.name,
            "state": member.state,
            "party": member.party.value,
            "chamber": member.chamber.value,
            "photo_url": member.photo_url,
            "score": pos.score,
            "confidence": pos.confidence,
            "evidence_count": pos.evidence_count,
        })

    # Sort by score
    result.sort(key=lambda x: x["score"])

    # Find members without positions
    positioned_ids = {p["member_id"] for p in result}

    # Get all members in the chamber
    member_query = db.query(Member)
    if chamber:
        if chamber.lower() == "senate":
            member_query = member_query.filter(Member.chamber == Chamber.SENATE)
        elif chamber.lower() == "house":
            member_query = member_query.filter(Member.chamber == Chamber.HOUSE)

    all_members = member_query.all()
    no_data = []
    for member in all_members:
        if member.id not in positioned_ids:
            no_data.append({
                "member_id": member.id,
                "name": member.name,
                "state": member.state,
                "party": member.party.value,
                "chamber": member.chamber.value,
                "photo_url": member.photo_url,
            })

    # Sort no_data by name
    no_data.sort(key=lambda x: x["name"])

    return {
        "issue": {
            "name": issue.name,
            "slug": issue.slug,
            "description": issue.description,
            "spectrum_left_label": issue.spectrum_left_label,
            "spectrum_right_label": issue.spectrum_right_label,
            "spectrum_description": issue.spectrum_description,
        },
        "positions": result,
        "no_data": no_data,
        "stats": {
            "total": len(result),
            "no_data_count": len(no_data),
            "by_party": {
                "D": len([p for p in result if p["party"] == "D"]),
                "R": len([p for p in result if p["party"] == "R"]),
                "I": len([p for p in result if p["party"] == "I"]),
            },
        },
    }


@app.get("/api/members/{member_id}")
def get_member(member_id: str, db: Session = Depends(get_db)):
    """Get detailed member information with positions and evidence."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Get positions
    positions = db.query(Position).filter(Position.member_id == member_id).all()

    # Get votes as evidence
    votes = db.query(Vote).filter(Vote.member_id == member_id).all()

    vote_evidence = []
    for vote in votes:
        bill = db.query(Bill).filter(Bill.id == vote.bill_id).first()
        if bill:
            vote_evidence.append({
                "bill_id": bill.id,
                "bill_title": bill.short_title or bill.title,
                "vote": vote.vote.value,
                "vote_date": vote.vote_date.isoformat() if vote.vote_date else None,
                "bill_position_indicator": bill.position_indicator,
            })

    return {
        "id": member.id,
        "name": member.name,
        "first_name": member.first_name,
        "last_name": member.last_name,
        "state": member.state,
        "party": member.party.value,
        "chamber": member.chamber.value,
        "photo_url": member.photo_url,
        "positions": [
            {
                "issue_id": pos.issue_id,
                "score": pos.score,
                "confidence": pos.confidence,
            }
            for pos in positions
        ],
        "evidence": {
            "votes": vote_evidence,
        },
    }


@app.get("/api/members/{member_id}/statements")
def get_member_statements(
    member_id: str,
    issue: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get statements for a specific member, optionally filtered by issue."""
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    query = db.query(Statement).filter(Statement.member_id == member_id)

    # Filter by issue if specified
    if issue:
        # Use JSON contains check (SQLite syntax)
        query = query.filter(Statement.issue_tags.contains(issue))

    # Order by date, most recent first
    statements = query.order_by(Statement.source_date.desc()).all()

    return {
        "member_id": member_id,
        "member_name": member.name,
        "statements": [
            {
                "id": stmt.id,
                "text": stmt.text,
                "title": stmt.title,
                "source": stmt.source,
                "source_url": stmt.source_url,
                "source_date": stmt.source_date.isoformat() if stmt.source_date else None,
                "cr_page": stmt.cr_page,
                "issue_tags": stmt.issue_tags,
                "analyzed": stmt.analyzed,
            }
            for stmt in statements
        ],
        "count": len(statements),
    }


@app.get("/api/statements")
def get_statements(
    issue: Optional[str] = None,
    member_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get all statements, optionally filtered by issue or member."""
    query = db.query(Statement)

    if issue:
        query = query.filter(Statement.issue_tags.contains(issue))

    if member_id:
        query = query.filter(Statement.member_id == member_id)

    # Order by date, most recent first
    statements = query.order_by(Statement.source_date.desc()).limit(limit).all()

    result = []
    for stmt in statements:
        member = db.query(Member).filter(Member.id == stmt.member_id).first()
        result.append({
            "id": stmt.id,
            "member_id": stmt.member_id,
            "member_name": member.name if member else "Unknown",
            "member_party": member.party.value if member else None,
            "member_state": member.state if member else None,
            "text": stmt.text,
            "title": stmt.title,
            "source": stmt.source,
            "source_url": stmt.source_url,
            "source_date": stmt.source_date.isoformat() if stmt.source_date else None,
            "cr_page": stmt.cr_page,
            "issue_tags": stmt.issue_tags,
        })

    return {
        "statements": result,
        "count": len(result),
        "limit": limit,
    }


@app.get("/api/metadata")
def get_metadata(db: Session = Depends(get_db)):
    """Get data freshness metadata."""
    metadata_list = db.query(DataMetadata).all()

    result = {}
    for m in metadata_list:
        result[m.data_type] = {
            "last_updated": m.last_updated.isoformat() if m.last_updated else None,
            "record_count": m.record_count,
            "source": m.source,
            "is_stale": m.is_stale,
            "age_days": m.age_days,
        }

    # Find the most recent update across all data types
    if metadata_list:
        most_recent = max(m.last_updated for m in metadata_list)
        oldest = min(m.last_updated for m in metadata_list)
        any_stale = any(m.is_stale for m in metadata_list)
    else:
        most_recent = None
        oldest = None
        any_stale = True

    return {
        "data_types": result,
        "summary": {
            "last_updated": most_recent.isoformat() if most_recent else None,
            "oldest_data": oldest.isoformat() if oldest else None,
            "any_stale": any_stale,
        },
    }

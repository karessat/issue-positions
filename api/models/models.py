"""SQLAlchemy models for the Issue Positions database."""
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Enum,
    JSON,
)
from sqlalchemy.orm import relationship
import enum

from .database import Base


class Chamber(enum.Enum):
    """Congressional chamber."""
    SENATE = "senate"
    HOUSE = "house"


class Party(enum.Enum):
    """Political party."""
    DEMOCRAT = "D"
    REPUBLICAN = "R"
    INDEPENDENT = "I"


class VoteChoice(enum.Enum):
    """Vote options."""
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"
    NOT_VOTING = "not_voting"


class EvidenceType(enum.Enum):
    """Types of evidence for positions."""
    VOTE = "vote"
    STATEMENT = "statement"
    RATING = "rating"


class Member(Base):
    """
    Congressional members (Senators and Representatives).

    The bioguide_id is the unique identifier used across Congress.gov
    and other official sources.
    """
    __tablename__ = "members"

    id = Column(String(7), primary_key=True, doc="Bioguide ID (e.g., 'S000033')")
    name = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    state = Column(String(2), nullable=False, doc="Two-letter state code")
    party = Column(Enum(Party), nullable=False)
    chamber = Column(Enum(Chamber), nullable=False)
    current_term_start = Column(DateTime)
    photo_url = Column(String(500))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    positions = relationship("Position", back_populates="member", cascade="all, delete-orphan")
    votes = relationship("Vote", back_populates="member", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Member {self.id}: {self.name} ({self.party.value}-{self.state})>"


class Issue(Base):
    """
    Policy issues that members take positions on.

    Each issue has a defined spectrum from -1.0 to +1.0 with
    labeled endpoints (e.g., "Free Trade" to "Protectionist").
    """
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, doc="URL-friendly identifier")
    description = Column(Text)

    # Spectrum definition
    spectrum_left_label = Column(String(50), doc="Label for -1.0 end (e.g., 'Free Trade')")
    spectrum_right_label = Column(String(50), doc="Label for +1.0 end (e.g., 'Protectionist')")
    spectrum_description = Column(Text, doc="Explanation of what the spectrum represents")

    # Key indicators for scoring (stored as JSON)
    scoring_indicators = Column(JSON, doc="List of indicators and their weights")

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    positions = relationship("Position", back_populates="issue", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Issue {self.id}: {self.name}>"


class Position(Base):
    """
    A member's calculated position on an issue.

    The score is a weighted composite of votes, statements, and ratings.
    Score range: -1.0 (left of spectrum) to +1.0 (right of spectrum)
    """
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(String(7), ForeignKey("members.id"), nullable=False)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)

    # Position score
    score = Column(Float, nullable=False, doc="Position score from -1.0 to +1.0")
    confidence = Column(Float, default=0.0, doc="Confidence level from 0.0 to 1.0")

    # Component scores (for transparency)
    vote_score = Column(Float, doc="Score derived from voting record")
    statement_score = Column(Float, doc="Score derived from public statements")
    rating_score = Column(Float, doc="Score derived from interest group ratings")

    # AI-generated summary
    summary = Column(Text, doc="Brief description of the member's position")

    # Metadata
    evidence_count = Column(Integer, default=0, doc="Number of evidence items")
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    member = relationship("Member", back_populates="positions")
    issue = relationship("Issue", back_populates="positions")
    evidence = relationship("Evidence", back_populates="position", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Position {self.member_id} on {self.issue_id}: {self.score:.2f}>"


class Evidence(Base):
    """
    Supporting evidence for a member's position.

    Evidence can be votes, statements, or interest group ratings.
    Each piece of evidence contributes to the overall position score.
    """
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)

    # Evidence details
    type = Column(Enum(EvidenceType), nullable=False)
    source_url = Column(String(1000))
    source_name = Column(String(255), doc="Name of the source (e.g., 'Congressional Record')")
    source_date = Column(DateTime)

    # Content
    raw_text = Column(Text, doc="Original text (for statements)")
    extracted_position = Column(Float, doc="AI-extracted position from -1.0 to +1.0")
    extraction_confidence = Column(Float, doc="AI confidence in extraction")
    extraction_reasoning = Column(Text, doc="AI explanation of the extraction")

    # Scoring
    weight = Column(Float, default=1.0, doc="How much this evidence contributes to score")

    # For vote evidence, link to the vote
    vote_id = Column(Integer, ForeignKey("votes.id"), nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    position = relationship("Position", back_populates="evidence")
    vote = relationship("Vote", back_populates="evidence")

    def __repr__(self):
        return f"<Evidence {self.id}: {self.type.value} for position {self.position_id}>"


class Bill(Base):
    """
    Congressional bills that members vote on.

    Bills are tagged with the issues they relate to for filtering.
    """
    __tablename__ = "bills"

    id = Column(String(50), primary_key=True, doc="Bill ID (e.g., 'hr1234-118')")
    congress = Column(Integer, nullable=False, doc="Congress number (e.g., 118)")
    bill_type = Column(String(10), doc="Type: hr, s, hjres, sjres, etc.")
    bill_number = Column(Integer)

    # Bill details
    title = Column(Text)
    short_title = Column(String(500))
    description = Column(Text)

    # Issue tagging (stored as JSON array of issue slugs)
    issue_tags = Column(JSON, default=list, doc="Issues this bill relates to")

    # For position scoring
    position_indicator = Column(Float, doc="What a YES vote indicates: -1.0 to +1.0")
    position_reasoning = Column(Text, doc="Why this bill is scored this way")

    # Metadata
    introduced_date = Column(DateTime)
    latest_action_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    votes = relationship("Vote", back_populates="bill", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Bill {self.id}: {self.short_title or self.title[:50]}>"


class Vote(Base):
    """
    Individual member votes on bills.

    Each vote is linked to a member and a bill, and can be
    used as evidence for positions on related issues.
    """
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(String(7), ForeignKey("members.id"), nullable=False)
    bill_id = Column(String(50), ForeignKey("bills.id"), nullable=False)

    # Vote details
    vote = Column(Enum(VoteChoice), nullable=False)
    vote_date = Column(DateTime, nullable=False)

    # Roll call information
    roll_call_id = Column(String(50), doc="Unique roll call identifier")
    session = Column(Integer, doc="Congressional session")

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    member = relationship("Member", back_populates="votes")
    bill = relationship("Bill", back_populates="votes")
    evidence = relationship("Evidence", back_populates="vote")

    def __repr__(self):
        return f"<Vote {self.member_id} on {self.bill_id}: {self.vote.value}>"

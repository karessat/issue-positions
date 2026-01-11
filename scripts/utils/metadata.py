"""Utility functions for managing data metadata."""
from datetime import datetime
from typing import Optional


def update_metadata(
    db,
    data_type: str,
    record_count: int,
    source: str,
    notes: Optional[str] = None,
):
    """
    Update the metadata for a data type after a refresh.

    Args:
        db: Database session
        data_type: Type of data ('members', 'votes', 'positions')
        record_count: Number of records updated
        source: Data source ('congress_api', 'seed_file', etc.)
        notes: Optional notes about the update
    """
    from api.models import DataMetadata

    # Check if metadata exists
    metadata = db.query(DataMetadata).filter(
        DataMetadata.data_type == data_type
    ).first()

    if metadata:
        metadata.last_updated = datetime.utcnow()
        metadata.record_count = record_count
        metadata.source = source
        metadata.notes = notes
    else:
        metadata = DataMetadata(
            data_type=data_type,
            last_updated=datetime.utcnow(),
            record_count=record_count,
            source=source,
            notes=notes,
        )
        db.add(metadata)

    db.commit()
    return metadata


def get_metadata(db, data_type: str):
    """Get metadata for a specific data type."""
    from api.models import DataMetadata
    return db.query(DataMetadata).filter(
        DataMetadata.data_type == data_type
    ).first()


def is_stale(db, data_type: str, max_age_days: int = 30) -> bool:
    """
    Check if data is stale (older than max_age_days).

    Returns True if:
    - No metadata exists for this data type
    - Data is older than max_age_days
    """
    from datetime import timedelta

    metadata = get_metadata(db, data_type)
    if not metadata:
        return True

    age = datetime.utcnow() - metadata.last_updated
    return age > timedelta(days=max_age_days)


def get_all_metadata(db) -> list:
    """Get all metadata records."""
    from api.models import DataMetadata
    return db.query(DataMetadata).all()


def format_age(last_updated: datetime) -> str:
    """Format the age of data in a human-readable way."""
    age = datetime.utcnow() - last_updated
    days = age.days

    if days == 0:
        hours = age.seconds // 3600
        if hours == 0:
            minutes = age.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif days == 1:
        return "yesterday"
    elif days < 7:
        return f"{days} days ago"
    elif days < 30:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        months = days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"

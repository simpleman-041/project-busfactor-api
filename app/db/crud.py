import json 
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AnalysisCache, RefreshControl
from app.schemas.busfactor import ContributorOut

def get_valid_analysis_cache(
    db: Session,
    owner: str, # ownerは文字通りのowner
    repo: str,
    window_days: int,
    failure_threshold: float,
    now: datetime,
) -> AnalysisCache | None:
    """
    有効期限内の analysis_cache を取得する。
    """
    stmt = (
        select(AnalysisCache)
        .where(AnalysisCache.owner == owner)
        .where(AnalysisCache.repo == repo)
        .where(AnalysisCache.window_days == window_days)
        .where(AnalysisCache.failure_threshold == failure_threshold)
        .where(AnalysisCache.expires_at > now)
    )
    return db.scalar(stmt)

def get_analysis_cache_by_key(
    db: Session,
    owner: str,
    repo: str,
    window_days: int,
    failure_threshold: float,
) -> AnalysisCache | None:
    """
    analysis_cache を一意キーで取得する。
    """
    stmt = (
        select(AnalysisCache)
        .where(AnalysisCache.owner == owner)
        .where(AnalysisCache.repo == repo )
        .where(AnalysisCache.window_days == window_days)
        .where(AnalysisCache.failure_threshold == failure_threshold)
    )
    return db.scalar(stmt)

def upsert_analysis_cache(
    db: Session,
    owner: str,
    repo: str,
    window_days: int,
    failure_threshold: float,
    bus_factor: int,
    contributors: list[ContributorOut],
    total_contributions: int,
    analyzed_at: datetime,
    expires_at: datetime,
) -> AnalysisCache:
    """
    analysis_cache を insert / update する。
    """
    record = get_analysis_cache_by_key(
        db=db,
        owner=owner,
        repo=repo,
        window_days=window_days,
        failure_threshold=failure_threshold,
    )
    contributors_json = json.dumps(
        [contributor.model_dump() for contributor in contributors],
        ensure_ascii=False,
    )
    
    if record is None:
        record = AnalysisCache(
            owner=owner,
        repo=repo,
        window_days=window_days,
        failure_threshold=failure_threshold,
        bus_factor=bus_factor,
        contributors_json=contributors_json,
        total_contributions=total_contributions,
        analyzed_at=analyzed_at,
        expires_at=expires_at,
        )
        db.add(record)
    else:
        record.bus_factor = bus_factor
        record.contributors_json= contributors_json
        record.total_contributions = total_contributions
        record.analyzed_at = analyzed_at
        record.expires_at = expires_at
    
    db.commit()
    db.refresh(record)
    return record

def get_refresh_control(
    db: Session,
    owner: str,
    repo: str,
) -> RefreshControl | None:
    """
    refresh_control を owner/repo で取得。
    """
    stmt = (
        select(RefreshControl)
        .where(RefreshControl.owner == owner)
        .where(RefreshControl.repo == repo)
    )
    return db.scalar(stmt)

def upsert_refresh_control(
    db: Session,
    owner: str,
    repo: str,
    now: datetime,
) -> RefreshControl:
    """
    refresh_control を insert / update する。
    """
    record = get_refresh_control(db=db, owner=owner, repo=repo)
    
    if record is None:
        record = RefreshControl(
            owner=owner,
            repo=repo,
            last_refresh_at=now,
        )
        db.add(record)
    else:
        record.last_refresh_at = now
    
    db.commit()
    db.refresh(record)
    return record
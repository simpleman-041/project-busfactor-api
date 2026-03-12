import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select # SQLのSELECTをイメージしてもらって
from sqlalchemy.orm import Session

from app.clients.github_client import GitHubClient
from app.core.config import settings
from app.db.models import AnalysisCache, RefreshControl
from app.schemas.busfactor import BusFactorResponse,  ContributorOut

class RepositoryNotFoundError(Exception):
    """
    指定リポジトリが見つからないときのエラー
    """

class  RefreshCooldownError(Exception):
    """
    refresh クールダウン中。
    """
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__("Refresh cooldown active")
        
@dataclass
class AnalysisResult:
    """
    内部計算用の中間結果
    """
    bus_factor: int
    risk_level: str
    contributors: list[ContributorOut]
    total_contributions: int
    
class BusFactorService:
    """
    Bus Factor API の業務ロジック本体
    """
    
    def __init__(self, db: Session, github_client: GitHubClient | None = None) -> None:
        self.db = db
        self.github_client = github_client or GitHubClient()
        
    def analyze_repository(
        self,
        owner: str,
        repo: str,
        window_days: int = settings.default_window_days,
        failure_threshold: float = settings.default_failure_threshold,
        refresh: bool = False, # refreshはキャッシュを無視して再計算するか？を表す。
    ) -> BusFactorResponse:
        """
        リポジトリ分析の公開メソッド
        """
        # _validateは引数に取る値が正常値か確認。
        self._validate_inputs(window_days=window_days, failure_threshold=failure_threshold)
        # 時差の影響を排除したUTCでの現在時刻を返す。
        now = self._now_utc()
        
        if not refresh:
            cache = self._find_valid_cache(
                owner=owner,
                repo=repo,
                window_days=window_days,
                failure_threshold=failure_threshold,
                now=now,
            )
            if cache is not None:
                return self._build_response_from_cache(cache)
        
        if refresh:
            self._check_refresh_cool_down(owner=owner, repo=repo, now=now)
        
        self._ensure_repository_exsists(owner=owner, repo=repo)
        
        result = self._run_analysis(
            owner=owner,
            repo=repo,
            window_days=window_days,
            failure_threshold=failure_threshold,
            now=now,
        )
        
        self._upsert_analysis_cache(
            owner=owner,
            repo=repo,
            window_days=window_days,
            failure_threshold=failure_threshold,
            result=result,
            analyzed_at=now,
            expires_at=now + timedelta(hours=settings.cache_ttl_hours)
        )
        
        if refresh:
            self._upsert_refresh_control(owner=owner,repo=repo, now=now)
            
        return BusFactorResponse(
            repository=f"{owner}/{repo}",
            bus_factor=result.bus_factor,
            risk_level=result.risk_level,
            failure_threshold=failure_threshold,
            window_days=window_days,
            cached=False,
            contributors=result.contributors,
        )
    
    def _validate_inputs(self, window_days: int, failure_threshold: float) -> None:
        if window_days <= 0:
            raise ValueError("window_days must be greater than 0")

        if not 0.0 < failure_threshold <= 1.0:
            raise ValueError("failure_threshold must be in the range (0, 1]")
    
    def _find_valid_cache(
        self,
        owner: str,
        repo: str,
        window_days: int,
        failure_threshold: float,
        now: datetime,
    ) -> AnalysisCache | None:
        stmt = (
            select(AnalysisCache)
            .where(AnalysisCache.owner == owner)
            .where(AnalysisCache.repo == repo)
            .where(AnalysisCache.window_days == window_days)
            .where(AnalysisCache.failure_threshold == failure_threshold)
            .where(AnalysisCache.expires_at > now)
        )
        return self.db.scalar(stmt)
    
    def _build_response_from_chache(self, cache: AnalysisCache) -> BusFactorResponse:
        raw_contributors = json.loads(cache.contributors_json)
        contributors = [ContributorOut(**item) for item in raw_contributors]
        
        return BusFactorResponse(
            repository=f"{cache.owner}/{cache.repo}",
            bus_factor=cache.bus_factor,
            risk_level=cache.risk_level,
            failure_threshold=cache.failure_threshold,
            window_days=cache.window_days,
            cached=True,
            contributors=contributors,
        )
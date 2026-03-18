import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import exp
import httpx
from sqlalchemy.orm import Session

from app.clients.github_client import GitHubClient
from app.core.config import settings
from app.db.models import AnalysisCache
from app.schemas.busfactor import BusFactorResponse,  ContributorOut

from app.db.crud import (
    get_refresh_control,
    get_valid_analysis_cache,
    upsert_analysis_cache,
    upsert_refresh_control,    
)

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
            self._check_refresh_cooldown(owner=owner, repo=repo, now=now)
        
        self._ensure_repository_exists(owner=owner, repo=repo)
        
        result = self._run_analysis(
            owner=owner,
            repo=repo,
            window_days=window_days,
            failure_threshold=failure_threshold,
            now=now,
        )
        
        upsert_analysis_cache(
            db=self.db,
            owner=owner,
            repo=repo,
            window_days=window_days,
            failure_threshold=failure_threshold,
            bus_factor=result.bus_factor,
            risk_level=result.risk_level,
            contributors=result.contributors,
            total_contributions=result.total_contributions,
            analyzed_at=now,
            expires_at=now + timedelta(hours=settings.cache_ttl_hours),
        )
        
        if refresh:
            upsert_refresh_control(
                db=self.db,
                owner=owner,
                repo=repo,
                now=now,
            )
            
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
        return get_valid_analysis_cache(
            db=self.db,
            owner=owner,
            repo=repo,
            window_days=window_days,
            failure_threshold=failure_threshold,
            now=now,
        )
    
    def _build_response_from_cache(self, cache: AnalysisCache) -> BusFactorResponse:
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
        
    def _check_refresh_cooldown(self, owner: str, repo: str, now: datetime) -> None:
        
        record = get_refresh_control(
            db=self.db,
            owner=owner,
            repo=repo,
        )
        
        if record is None:
            return
        
        cooldown = timedelta(minutes=settings.refresh_cooldown_minutes)
        available_at = record.last_refresh_at + cooldown
        
        if now < available_at:
            retry_after = int((available_at - now).total_seconds)
            raise RefreshCooldownError(retry_after_seconds=max(retry_after,1))
    
    def _ensure_repository_exists(self, owner: str, repo: str) -> None:
        try:
            self.github_client.get_repository(owner=owner, repo=repo)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise RepositoryNotFoundError(f"Repository not found: {owner}/{repo}")
            raise
    
    def _run_analysis(
        self,
        owner: str,
        repo: str,
        window_days: int,
        failure_threshold: float,
        now: datetime,
    ) -> AnalysisResult:
        since = now - timedelta(days=window_days)
        
        commits = self.github_client.get_commits(
            owner=owner,
            repo=repo,
            since=since,
            until=now,
            max_pages=max(1, settings.max_commits // 100),
            )
        commits = commits[: settings.max_commits] # リストの最初からsettings.の分だけ取り出す。スライスね。
        
        contribution_map = self._aggregate_commit_authors(commits)
        
        if not contribution_map:
            fallback_contributors = self.github_client.get_contributors(
                owner=owner,
                repo=repo,
                include_anonymous=False,
                max_pages=max(1, settings.max_commits // 100),
            )
            contribution_map = self._aggregate_contributors(fallback_contributors)
        
        total_contributions = sum(contribution_map.values())
        if total_contributions <= 0:
            contributors: list[ContributorOut] = []
            return AnalysisResult(
                bus_factor=0,
                risk_level="high",
                contributors=[],
                total_contributions=0,
            )
            
        contributors = self._build_contributor_outputs(contribution_map, total_contributions)
        bus_factor = self._calculate_bus_factor(contributors, failure_threshold)
        risk_level = self._determine_risk_level(bus_factor)
        
        return AnalysisResult(
            bus_factor=bus_factor,
            risk_level=risk_level,
            contributors=contributors,
            total_contributions=total_contributions,
        )
        
    def _calculate_weight(self, days_ago: int, decay_rate: float = 0.01) -> float:
        return exp(-decay_rate * days_ago) # expは指数関数。日数経過に伴い、滑らかに減っていく。
    
    def _aggregate_commit_authors(self, commits: list[dict]) -> dict[str, float]:
        """
        commit 一覧から author.login ベースで contributions を集計する。
        """
        counts: dict[str, float] = {}
        
        for commit in commits:
            author = commit.get("author")
            date_str = commit["commit"]["author"]["date"]
            
            if not isinstance(author, dict):
                continue
            
            commit_dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            days_ago = (now - commit_dt).days
            
            login = author.get("login")
            if not isinstance(login, str) or not login:
                continue
            
            weight = self._calculate_weight(days_ago)
            counts[login] = counts.get(login, 0.0) + weight
        
        return counts
    
    def _aggregate_contributors(self, contributors: list[dict]) -> dict[str, int]:
        """
        contributors API の結果を集計する。
        """
        counts: dict[str, int] = {}
        
        for contributor in contributors:
            login = contributor.get("login")
            contributions = contributor.get("contributions", 0)
            
            if not isinstance(login, str) or not login:
                continue
            if not isinstance(contributions, int) or contributions < 0:
                continue
            
            counts[login] = counts.get(login, 0) + contributions
            
        return counts
    
    def _build_contributor_outputs(
        self,
        contribution_map: dict[str, int],
        total_contributions: int,
    ) -> list[ContributorOut]:
        sorted_itms = sorted(
            contribution_map.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        
        return [
            ContributorOut(
                login=login,
                contributions=contributions,
                ownership=contributions / total_contributions
            )
            for login, contributions in sorted_itms
        ]
        
    def _calculate_bus_factor(
        self,
        contributors: list[ContributorOut],
        failure_threshold: float,
    ) -> int:
        """
        ownership  の大きい順に除外し、累計喪失率が thresholdに達した人物を返す。
        """
        cumulative_loss = 0.0
        
        for index, contributor in enumerate(contributors, start=1):
            cumulative_loss += contributor.ownership
            if cumulative_loss >= failure_threshold:
                return index
            
        return len(contributors)
    
    def _determine_risk_level(self, bus_factor: int) -> str:
        """
        0,1:high
        2:medium
        3以上: low
        ここは後ほどより効果的な区分に設定する。
        """
        if bus_factor <= 1:
            return "high"
        if bus_factor == 2:
            return "medium"
        return "low"
        
    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)
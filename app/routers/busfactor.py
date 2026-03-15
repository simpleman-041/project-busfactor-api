import httpx
from fastapi import APIRouter, Depends, HTTPException, Query # Queryはクエリパラメータにバリデーション、追加設定を行うためのもの
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.busfactor import BusFactorResponse
from app.schemas.common import ErrorResponse
from app.services.busfactor_service import (
    BusFactorService,
    RefreshCooldownError,
    RepositoryNotFoundError,
)

router = APIRouter(tags=["busfactor"])
@router.get(
    "/busfactor/{owner}/{repo}",
    response_model=BusFactorResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid paraameters"},
        404: {"model": ErrorResponse, "description": "Repository not found"},
        429: {"model": ErrorResponse, "description": "Rate limited"},
        503: {"model": ErrorResponse, "description": "Github API unavailable"},
    },
)
def get_bus_factor(
    owner: str,
    repo: str,
    window_days: int = Query(180, ge=1),
    failure_threshold: float = Query(0.5, gt=0.0, le=1.0),
    refresh: bool = Query(False),
    db: Session = Depends(get_db),
) -> BusFactorResponse:
    """
    指定リポジトリの BusFactor を返す。
    """
    service = BusFactorService(db=db)
    
    try:
        return service.analyze_repository(
            owner=owner,
            repo=repo,
            window_days=window_days,
            failure_threshold=failure_threshold,
            refresh=refresh,
        )
    
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc 
        
    except RepositoryNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc 
    
    except RefreshCooldownError as exc:
        minutes = max(1, exc.retry_after_seconds // 60)
        raise HTTPException(
            status_code=429,
            detail=f"Refresh allowed once every 15 minutes. Retry in about {minutes} minute(s)."
        ) from exc
    
    # GitHub側の403は429として、通信障害は503に寄せる。
    except RepositoryNotFoundError as exc:
        if exc.response.status_code == 403:
            raise HTTPException(
                status_code=429,
                detail="GitHub API rate limit exceed",
            ) from exc 
        
        raise HTTPException(
            status_code=503,
            detail="GitHub API unavailable",
        ) from exc
        
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="GitHub API unavailable",
        ) from exc
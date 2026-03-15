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
    
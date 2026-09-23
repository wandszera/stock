import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analytics.datasets import build_weekly_demand_series
from app.analytics.forecasting import temporal_backtest
from app.core.database import get_db
from app.core.security import ensure_store_access, get_current_user, require_roles
from app.models.analytics import ForecastBacktestRun
from app.models.product import ProductVariant
from app.models.user import User
from app.schemas.analytics import BacktestCreate, BacktestListResponse, BacktestResponse
from app.services.audit import record_audit_event


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/backtests", response_model=BacktestResponse)
def create_backtest(
    payload: BacktestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "manager")),
):
    ensure_store_access(current_user, payload.store_id)
    if not db.query(ProductVariant.id).filter(ProductVariant.id == payload.variant_id).first():
        raise HTTPException(status_code=404, detail="Variante nao encontrada.")

    demand = build_weekly_demand_series(
        db, store_id=payload.store_id, variant_id=payload.variant_id
    )
    try:
        results = temporal_backtest(
            demand.tolist(),
            horizon=payload.horizon,
            minimum_train_periods=payload.minimum_train_periods,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    run = ForecastBacktestRun(
        store_id=payload.store_id,
        variant_id=payload.variant_id,
        status="completed",
        frequency="weekly",
        horizon=payload.horizon,
        minimum_train_periods=payload.minimum_train_periods,
        winner_model=results[0]["model"],
        results=results,
        created_by=current_user.id,
    )
    db.add(run)
    db.flush()
    record_audit_event(
        db,
        action="analytics.backtest_completed",
        entity_type="forecast_backtest",
        entity_id=run.id,
        store_id=run.store_id,
        actor_id=current_user.id,
        metadata={
            "winner_model": run.winner_model,
            "period_count": len(demand),
            "winner_wape": results[0]["wape"],
        },
    )
    db.commit()
    db.refresh(run)
    return run


@router.get("/backtests", response_model=BacktestListResponse)
def list_backtests(
    store_id: uuid.UUID | None = Query(default=None),
    variant_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ForecastBacktestRun)
    if store_id is not None:
        ensure_store_access(current_user, store_id)
        query = query.filter(ForecastBacktestRun.store_id == store_id)
    elif current_user.role != "admin":
        query = query.filter(ForecastBacktestRun.store_id == current_user.store_id)
    if variant_id is not None:
        query = query.filter(ForecastBacktestRun.variant_id == variant_id)
    items = query.order_by(ForecastBacktestRun.created_at.desc()).limit(limit).all()
    return {"items": items, "total": query.count()}


@router.get("/backtests/{run_id}", response_model=BacktestResponse)
def get_backtest(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    run = db.query(ForecastBacktestRun).filter(ForecastBacktestRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Backtest nao encontrado.")
    ensure_store_access(current_user, run.store_id)
    return run

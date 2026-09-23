import uuid

import pandas as pd
from sqlalchemy.orm import Session

from app.models.sale import Sale, SaleItem


def build_weekly_demand_series(
    db: Session, *, store_id: uuid.UUID, variant_id: uuid.UUID
) -> pd.Series:
    rows = (
        db.query(Sale.sold_at, SaleItem.quantity)
        .join(SaleItem, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.store_id == store_id,
            Sale.status == "completed",
            SaleItem.variant_id == variant_id,
        )
        .order_by(Sale.sold_at.asc())
        .all()
    )
    if not rows:
        return pd.Series(dtype="float64", name="demand")
    frame = pd.DataFrame(rows, columns=["sold_at", "quantity"])
    frame["sold_at"] = pd.to_datetime(frame["sold_at"], utc=True)
    series = frame.set_index("sold_at")["quantity"].resample("W-MON").sum().astype(float)
    full_index = pd.date_range(series.index.min(), series.index.max(), freq="W-MON", tz="UTC")
    return series.reindex(full_index, fill_value=0.0).rename("demand")

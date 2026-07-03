from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.categories import router as categories_router
from app.api.routes.counts import router as counts_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.inventory import router as inventory_router
from app.api.routes.products import router as products_router
from app.api.routes.variants import router as variants_router
from app.api.routes.sales import router as sales_router
from app.api.routes.stores import router as stores_router
from app.api.routes.users import router as users_router



api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(categories_router)
api_router.include_router(dashboard_router)
api_router.include_router(stores_router)
api_router.include_router(users_router)
api_router.include_router(products_router)
api_router.include_router(variants_router)
api_router.include_router(inventory_router)
api_router.include_router(counts_router)
api_router.include_router(sales_router)

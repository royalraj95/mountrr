from fastapi import APIRouter
from mountrr.models import HealthResponse
from mountrr import __version__

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)

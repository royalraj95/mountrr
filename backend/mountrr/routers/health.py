from fastapi import APIRouter

from mountrr import __version__
from mountrr.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)

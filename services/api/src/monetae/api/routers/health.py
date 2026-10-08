from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/api/v1", tags=["health"])


class Health(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    status: Literal["ok"]


@router.get("/health", response_model=Health, operation_id="health")
def health() -> Health:
    return Health(status="ok")

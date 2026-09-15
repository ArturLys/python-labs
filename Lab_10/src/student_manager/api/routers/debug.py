"""Endpoints that misbehave on purpose, so the client's timeout and retry can be demonstrated and tested."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/slow", summary="Відповідає через `seconds` секунд")
async def slow(seconds: Annotated[float, Query(ge=0, le=10)] = 1.0) -> dict[str, float]:
    await asyncio.sleep(seconds)
    return {"slept": seconds}


@router.get("/flaky", summary="Перші `failures` викликів відповідають 503, далі 200")
async def flaky(request: Request, response: Response, failures: Annotated[int, Query(ge=0)] = 2) -> dict[str, int]:
    state = request.app.state
    state.flaky_calls = getattr(state, "flaky_calls", 0) + 1
    if state.flaky_calls <= failures:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"call": state.flaky_calls}

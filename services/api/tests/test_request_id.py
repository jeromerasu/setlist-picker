from __future__ import annotations

import uuid

from httpx import AsyncClient


async def test_request_id_header_round_trips(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    request_id = response.headers.get("x-request-id")
    assert request_id is not None
    uuid.UUID(request_id)  # validates it's a valid UUID


async def test_request_id_echoes_provided_value(client: AsyncClient) -> None:
    provided = str(uuid.uuid4())
    response = await client.get("/healthz", headers={"x-request-id": provided})
    assert response.headers["x-request-id"] == provided

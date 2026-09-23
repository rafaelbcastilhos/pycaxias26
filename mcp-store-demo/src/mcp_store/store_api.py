"""Cliente HTTP da API local da loja PyCaxias."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mcp_store.domain.errors import (
    InsufficientStock,
    InvalidOrderState,
    OrderNotFound,
    ProductInactive,
    ProductNotFound,
    StoreError,
)

_ERRORS: dict[str, type[StoreError]] = {
    "product_not_found": ProductNotFound,
    "order_not_found": OrderNotFound,
    "insufficient_stock": InsufficientStock,
    "invalid_order_state": InvalidOrderState,
    "product_inactive": ProductInactive,
}


class StoreApiClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    async def search_products(self, query: str, limit: int) -> list[dict[str, Any]]:
        from urllib.parse import urlencode

        return await self._request("GET", f"/v1/products?{urlencode({'query': query, 'limit': limit})}")

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/orders/{order_id}")

    async def create_order(self, sku: str, quantity: int, idempotency_key: str) -> dict[str, Any]:
        return await self._request(
            "POST", "/v1/orders", {"sku": sku, "quantity": quantity}, idempotency_key
        )

    async def pay_order(self, order_id: str, idempotency_key: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/v1/orders/{order_id}/payment", None, idempotency_key
        )

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        return await self._request("POST", f"/v1/orders/{order_id}/cancellation")

    async def restock_product(self, sku: str, units: int) -> dict[str, Any]:
        return await self._request("POST", f"/v1/products/{sku}/restock", {"units": units})

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        return await asyncio.to_thread(self._request_sync, method, path, payload, idempotency_key)

    def _request_sync(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        idempotency_key: str | None,
    ) -> Any:
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key

        request = Request(f"{self._base_url}{path}", data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                return json.loads(response.read())
        except HTTPError as exc:
            try:
                response = json.loads(exc.read())
                error = response["error"]
                error_type = _ERRORS.get(error.get("code"), StoreError)
                raise error_type(error.get("message", "A operacao nao pode ser concluida.")) from exc
            except (json.JSONDecodeError, KeyError, TypeError):
                raise RuntimeError("Resposta invalida da API da loja.") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError("API local da loja indisponivel.") from exc

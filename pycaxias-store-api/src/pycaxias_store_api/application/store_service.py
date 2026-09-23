"""Casos de uso; nenhuma dependência de HTTP ou Flask."""

from __future__ import annotations

import uuid

from pycaxias_store_api.domain.entities import Order, OrderStatus, Product, now_utc
from pycaxias_store_api.domain.errors import (
    InsufficientStock,
    InvalidOrderState,
    OrderNotFound,
    ProductInactive,
    ProductNotFound,
)
from pycaxias_store_api.infrastructure.in_memory_store import InMemoryStore

_ALLOWED_TRANSITIONS = {
    OrderStatus.PENDING: frozenset({OrderStatus.PAID, OrderStatus.CANCELLED}),
    OrderStatus.PAID: frozenset({OrderStatus.CANCELLED}),
    OrderStatus.CANCELLED: frozenset(),
}


class StoreService:
    def __init__(self, store: InMemoryStore, max_units_per_order: int = 10) -> None:
        self._store = store
        self._max_units_per_order = max_units_per_order

    def search_products(self, query: str, limit: int) -> list[dict[str, str | int]]:
        needle = query.strip().casefold()
        products = (
            product
            for product in self._store.products.values()
            if product.active
            and (
                not needle
                or needle in product.sku.casefold()
                or needle in product.name.casefold()
                or needle in product.description.casefold()
            )
        )
        return [product.as_public_dict() for product in sorted(products, key=lambda p: p.sku)[:limit]]

    def get_order(self, order_id: str) -> dict[str, str | int]:
        return self._order(order_id).as_public_dict()

    def create_order(self, sku: str, quantity: int, idempotency_key: str) -> dict[str, str | int]:
        with self._store.lock:
            replay = self._store.create_keys.get(idempotency_key)
            if replay:
                return self._store.orders[replay].as_public_dict()
            product = self._product_for_sale(sku)
            if quantity > self._max_units_per_order:
                raise InvalidOrderState(f"Quantidade maxima por pedido e {self._max_units_per_order} unidades.")
            if product.stock < quantity:
                raise InsufficientStock(f"Estoque insuficiente para {sku}: pedido {quantity}, disponivel {product.stock}.")
            product.stock -= quantity
            order = Order(f"ORD-{uuid.uuid4().hex[:16]}", OrderStatus.PENDING, product.sku, product.name, quantity, product.price_cents, product.currency)
            self._store.orders[order.order_id] = order
            self._store.create_keys[idempotency_key] = order.order_id
            return order.as_public_dict()

    def pay_order(self, order_id: str, idempotency_key: str) -> dict[str, str | int]:
        with self._store.lock:
            replay = self._store.pay_keys.get(idempotency_key)
            if replay:
                return self._store.orders[replay].as_public_dict()
            order = self._order(order_id)
            self._transition(order, OrderStatus.PAID)
            order.status, order.updated_at = OrderStatus.PAID, now_utc()
            self._store.pay_keys[idempotency_key] = order.order_id
            return order.as_public_dict()

    def cancel_order(self, order_id: str) -> dict[str, str | int]:
        with self._store.lock:
            order = self._order(order_id)
            self._transition(order, OrderStatus.CANCELLED)
            self._store.products[order.sku].stock += order.quantity
            order.status, order.updated_at = OrderStatus.CANCELLED, now_utc()
            return order.as_public_dict()

    def restock_product(self, sku: str, units: int) -> dict[str, str | int]:
        with self._store.lock:
            product = self._store.products.get(sku)
            if product is None:
                raise ProductNotFound(f"Produto {sku} nao encontrado no catalogo.")
            product.stock += units
            return {"sku": product.sku, "name": product.name, "stock": product.stock}

    def _order(self, order_id: str) -> Order:
        order = self._store.orders.get(order_id)
        if order is None:
            raise OrderNotFound(f"Pedido {order_id} nao encontrado.")
        return order

    def _product_for_sale(self, sku: str) -> Product:
        product = self._store.products.get(sku)
        if product is None:
            raise ProductNotFound(f"Produto {sku} nao encontrado no catalogo.")
        if not product.active:
            raise ProductInactive(f"Produto {sku} nao esta disponivel para venda.")
        return product

    @staticmethod
    def _transition(order: Order, target: OrderStatus) -> None:
        if target not in _ALLOWED_TRANSITIONS[order.status]:
            raise InvalidOrderState(f"Pedido {order.order_id} esta {order.status.value}; transicao para {target.value} nao e permitida.")

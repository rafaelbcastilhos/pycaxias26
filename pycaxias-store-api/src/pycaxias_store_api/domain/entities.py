"""Entidades da loja e suas projeções públicas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


def now_utc() -> datetime:
    return datetime.now(UTC)


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


@dataclass
class Product:
    sku: str
    name: str
    description: str
    price_cents: int
    stock: int
    currency: str = "BRL"
    active: bool = True

    def as_public_dict(self) -> dict[str, str | int]:
        return {
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "price": f"{self.price_cents / 100:.2f}",
            "currency": self.currency,
            "stock": self.stock,
        }


@dataclass
class Order:
    order_id: str
    status: OrderStatus
    sku: str
    product_name: str
    quantity: int
    unit_price_cents: int
    currency: str = "BRL"
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)

    def as_public_dict(self) -> dict[str, str | int]:
        return {
            "order_id": self.order_id,
            "status": self.status.value,
            "sku": self.sku,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": f"{self.unit_price_cents / 100:.2f}",
            "total": f"{self.unit_price_cents * self.quantity / 100:.2f}",
            "currency": self.currency,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

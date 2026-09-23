"""Armazenamento em memória, apropriado apenas para a demonstração local."""

from __future__ import annotations

import threading

from pycaxias_store_api.domain.entities import Product


SEED_CATALOG: tuple[Product, ...] = (
    Product("CAM-2001", "Camiseta PyCaxias 2026", "Algodao penteado, unissex, tamanhos P ao GG", 7990, 12),
    Product("ADE-2002", "Cartela de adesivos", "12 adesivos vinilicos, resistentes a agua", 1500, 57),
    Product("CAN-2003", "Caneca PyCaxias", "Ceramica 325ml, logo nos dois lados", 4500, 4),
    Product("BON-2004", "Bone PyCaxias", "Aba curva, ajustavel, logo bordado", 5990, 0),
)


class InMemoryStore:
    def __init__(self) -> None:
        self.products = {product.sku: Product(**product.__dict__) for product in SEED_CATALOG}
        self.orders = {}
        self.create_keys: dict[str, str] = {}
        self.pay_keys: dict[str, str] = {}
        self.lock = threading.Lock()

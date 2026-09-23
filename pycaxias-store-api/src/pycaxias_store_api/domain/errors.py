"""Erros de negócio seguros para exposição na borda HTTP."""


class StoreError(Exception):
    code = "store_error"


class ProductNotFound(StoreError):
    code = "product_not_found"


class OrderNotFound(StoreError):
    code = "order_not_found"


class InsufficientStock(StoreError):
    code = "insufficient_stock"


class InvalidOrderState(StoreError):
    code = "invalid_order_state"


class ProductInactive(StoreError):
    code = "product_inactive"

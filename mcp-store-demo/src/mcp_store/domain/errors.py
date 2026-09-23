"""Erros de dominio.

CWE-209 (Error Message Containing Sensitive Information): o dominio levanta
erros com mensagens *curadas*, seguras para devolver ao chamador. Qualquer
excecao inesperada e convertida em mensagem genarica na borda (server/tools.py)
— stack trace e detalhe interno ficam apenas no log do servidor.
"""

from __future__ import annotations


class StoreError(Exception):
    """Erro de negocio previsto, com mensagem segura para exposicao."""

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

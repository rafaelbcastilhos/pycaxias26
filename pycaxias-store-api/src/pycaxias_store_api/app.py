"""Borda HTTP da loja. Não há endpoints administrativos ou auxiliares."""

from __future__ import annotations

import re

from flask import Flask, jsonify, request
from pydantic import BaseModel, Field, ValidationError

from pycaxias_store_api.application.store_service import StoreService
from pycaxias_store_api.domain.errors import StoreError
from pycaxias_store_api.infrastructure.in_memory_store import InMemoryStore


class CreateOrderBody(BaseModel):
    sku: str = Field(pattern=r"^[A-Z]{3}-[0-9]{4}$")
    quantity: int = Field(ge=1, le=100)


class RestockBody(BaseModel):
    units: int = Field(ge=1, le=1000)


class InvalidRequest(Exception):
    """Erro de formato que pode ser devolvido ao cliente sem detalhes internos."""


def create_app() -> Flask:
    app = Flask(__name__)
    service = StoreService(InMemoryStore())

    @app.after_request
    def allow_local_frontend(response):
        """Permite somente frontends HTTP locais, inclusive preflight do navegador."""
        origin = request.headers.get("Origin", "")
        if re.fullmatch(r"http://(127\.0\.0\.1|localhost)(?::\d+)?", origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Idempotency-Key"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Private-Network"] = "true"
            response.headers["Vary"] = "Origin"
        return response

    @app.errorhandler(StoreError)
    def store_error(error: StoreError):
        status = 404 if error.code in {"product_not_found", "order_not_found"} else 409
        return jsonify(error={"code": error.code, "message": str(error)}), status

    @app.errorhandler(ValidationError)
    def validation_error(error: ValidationError):
        return jsonify(error={"code": "invalid_request", "message": "Requisicao invalida."}), 400

    @app.errorhandler(InvalidRequest)
    def invalid_request(error: InvalidRequest):
        return jsonify(error={"code": "invalid_request", "message": "Requisicao invalida."}), 400

    def body(model: type[BaseModel]) -> BaseModel:
        return model.model_validate(request.get_json(silent=True) or {})

    def idempotency_key() -> str:
        key = request.headers.get("Idempotency-Key", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", key):
            raise InvalidRequest
        return key

    @app.get("/v1/products")
    def search_products():
        query = request.args.get("query", "")
        limit = request.args.get("limit", default=5, type=int)
        if len(query) > 100 or limit is None or not 1 <= limit <= 20:
            return jsonify(error={"code": "invalid_request", "message": "Requisicao invalida."}), 400
        return jsonify(service.search_products(query, limit))

    @app.get("/v1/orders/<order_id>")
    def get_order(order_id: str):
        return jsonify(service.get_order(order_id))

    @app.post("/v1/orders")
    def create_order():
        data = body(CreateOrderBody)
        return jsonify(service.create_order(data.sku, data.quantity, idempotency_key())), 201

    @app.post("/v1/orders/<order_id>/payment")
    def pay_order(order_id: str):
        return jsonify(service.pay_order(order_id, idempotency_key()))

    @app.post("/v1/orders/<order_id>/cancellation")
    def cancel_order(order_id: str):
        return jsonify(service.cancel_order(order_id))

    @app.post("/v1/products/<sku>/restock")
    def restock_product(sku: str):
        data = body(RestockBody)
        return jsonify(service.restock_product(sku, data.units))

    return app

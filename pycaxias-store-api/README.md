# API da loja PyCaxias

API HTTP local que concentra o catálogo, estoque e pedidos usados pelo MCP.

```bash
poetry install
poetry run pycaxias-store-api
```

Ela escuta em `http://127.0.0.1:5000` por padrão. Configure `PYCAXIAS_STORE_API_HOST`
e `PYCAXIAS_STORE_API_PORT` quando necessário.

Os únicos endpoints são os que correspondem às operações da loja:

- `GET /v1/products?query=&limit=` — buscar produtos
- `GET /v1/orders/<order_id>` — consultar pedido
- `POST /v1/orders` — criar pedido (`sku`, `quantity`; cabeçalho `Idempotency-Key`)
- `POST /v1/orders/<order_id>/payment` — pagar pedido (cabeçalho `Idempotency-Key`)
- `POST /v1/orders/<order_id>/cancellation` — cancelar pedido
- `POST /v1/products/<sku>/restock` — repor estoque (`units`)

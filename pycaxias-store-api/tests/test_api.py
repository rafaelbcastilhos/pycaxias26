from pycaxias_store_api.app import create_app


def test_operacoes_da_loja_sao_expostas_por_http() -> None:
    client = create_app().test_client()

    catalog = client.get("/v1/products?query=adesivo&limit=5")
    assert catalog.status_code == 200
    assert catalog.json[0]["sku"] == "ADE-2002"

    created = client.post(
        "/v1/orders",
        json={"sku": "ADE-2002", "quantity": 2},
        headers={"Idempotency-Key": "api-create-001"},
    )
    assert created.status_code == 201
    order = created.json

    assert client.get(f"/v1/orders/{order['order_id']}").json["status"] == "PENDING"
    assert client.post(
        f"/v1/orders/{order['order_id']}/payment",
        headers={"Idempotency-Key": "api-payment-001"},
    ).json["status"] == "PAID"
    assert client.post(f"/v1/orders/{order['order_id']}/cancellation").json["status"] == "CANCELLED"
    assert client.post("/v1/products/ADE-2002/restock", json={"units": 3}).json["stock"] == 60


def test_chave_de_idempotencia_e_obrigatoria() -> None:
    response = create_app().test_client().post("/v1/orders", json={"sku": "ADE-2002", "quantity": 1})
    assert response.status_code == 400
    assert response.json["error"]["code"] == "invalid_request"


def test_api_permite_consumo_pelo_frontend_local() -> None:
    response = create_app().test_client().options(
        "/v1/products", headers={"Origin": "http://127.0.0.1:8000"}
    )
    assert response.headers["Access-Control-Allow-Origin"] == "http://127.0.0.1:8000"
    assert "Idempotency-Key" in response.headers["Access-Control-Allow-Headers"]
    assert response.headers["Access-Control-Allow-Private-Network"] == "true"

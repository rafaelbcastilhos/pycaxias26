"""Teste ponta a ponta pelo protocolo: cliente MCP -> servidor MCP.

Sobe o servidor como subprocesso (transporte stdio), faz o handshake e chama as
ferramentas de verdade. Nao envolve LLM — e o protocolo sob teste, nao o modelo.
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from typing import Any

import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult


def server_parameters() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_store.server"],
    )


def _payload(result: CallToolResult) -> Any:
    if result.structured_content is not None:
        return result.structured_content
    text = "\n".join(b.text for b in result.content if getattr(b, "type", None) == "text")
    return json.loads(text)


@asynccontextmanager
async def mcp_session():
    """Sessao MCP aberta e fechada dentro da MESMA task.

    Nao use fixture async-generator aqui: o `stdio_client` do MCP usa cancel
    scopes do anyio, que precisam ser abertos e fechados na mesma task. Uma
    fixture entra na task de setup e sai na de teardown, e o anyio aborta.
    """
    async with stdio_client(server_parameters()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def test_servidor_declara_annotations_em_todas_as_ferramentas() -> None:
    async with mcp_session() as session:
        listed = await session.list_tools()

        assert len(listed.tools) == 6
        for tool in listed.tools:
            assert tool.annotations is not None, f"{tool.name} sem annotations"
            assert tool.annotations.read_only_hint is not None
            assert tool.annotations.destructive_hint is not None
            assert tool.annotations.idempotent_hint is not None
            assert tool.annotations.open_world_hint is not None


async def test_fluxo_de_compra_pelo_protocolo() -> None:
    suffix = uuid.uuid4().hex[:12]
    async with mcp_session() as session:
        busca = await session.call_tool("search_products", {"query": "adesivo", "limit": 5})
        itens = _payload(busca)
        itens = itens["result"] if isinstance(itens, dict) and "result" in itens else itens
        assert any(i["sku"] == "ADE-2002" for i in itens)
        estoque_antes = next(i["stock"] for i in itens if i["sku"] == "ADE-2002")

        criado = await session.call_tool(
            "create_order",
            {"sku": "ADE-2002", "quantity": 2, "idempotency_key": f"e2e-create-{suffix}"},
        )
        order = _payload(criado)
        assert order["status"] == "PENDING"
        assert order["total"] == f"{15.00 * 2:.2f}"

        pago = await session.call_tool(
            "pay_order",
            {"order_id": order["order_id"], "idempotency_key": f"e2e-pay-{suffix}"},
        )
        assert _payload(pago)["status"] == "PAID"

        depois = _payload(await session.call_tool("search_products", {"query": "ADE-2002"}))
        depois = depois["result"] if isinstance(depois, dict) and "result" in depois else depois
        assert depois[0]["stock"] == estoque_antes - 2


async def test_input_invalido_e_recusado_na_borda() -> None:
    async with mcp_session() as session:
        """SKU fora do padrao nao chega ao dominio: Pydantic barra antes."""
        result = await session.call_tool(
            "create_order",
            {"sku": "../../etc/passwd", "quantity": 1, "idempotency_key": "e2e-bad-01"},
        )
        assert result.is_error


async def test_quantidade_acima_do_teto_e_recusada() -> None:
    async with mcp_session() as session:
        result = await session.call_tool(
            "create_order",
            {"sku": "ADE-2002", "quantity": 999, "idempotency_key": "e2e-bad-02"},
        )
        assert result.is_error


async def test_erro_de_negocio_nao_vaza_stack_trace() -> None:
    async with mcp_session() as session:
        result = await session.call_tool("get_order", {"order_id": "ORD-0000000000000000"})
        text = "\n".join(b.text for b in result.content if getattr(b, "type", None) == "text")

        assert result.is_error
        assert "Traceback" not in text
        assert "mcp_store" not in text

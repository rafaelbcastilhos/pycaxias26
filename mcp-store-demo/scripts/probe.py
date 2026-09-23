"""Chama uma ferramenta do MCP Server direto, sem LLM.

E o multimetro da demo: serve para conferir o servidor antes de subir o
modelo, e para reproduzir um bug sem gastar chamada de API.

    poetry run python scripts/probe.py                      # lista ferramentas
    poetry run python scripts/probe.py search_products
    poetry run python scripts/probe.py search_products '{"query": "caneca"}'
    poetry run python scripts/probe.py create_order \
        '{"sku": "ADE-2002", "quantity": 2, "idempotency_key": "probe-0001"}'

Cada execucao sobe um servidor novo, entao o estado (estoque, pedidos) comeca
do zero. Para encadear operacoes num mesmo processo, passe varias chamadas:

    poetry run python scripts/probe.py \
        create_order '{"sku":"ADE-2002","quantity":2,"idempotency_key":"probe-0001"}' \
        create_order '{"sku":"ADE-2002","quantity":2,"idempotency_key":"probe-0001"}' \
        search_products '{"query":"adesivo"}'
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def server_parameters() -> StdioServerParameters:
    """Parâmetros constantes para iniciar o servidor local de teste."""
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_store.server"],
    )


async def main(argv: list[str]) -> int:
    async with stdio_client(server_parameters()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            available = {t.name for t in listed.tools}

            if not argv:
                for tool in listed.tools:
                    print(tool.name)
                return 0

            # Pares (nome, json-opcional). O nome e conferido contra a lista
            # anunciada pelo servidor — allowlist, nao texto livre.
            for name, raw_args in _parse(argv):
                if name not in available:
                    print(
                        f"ferramenta '{name}' nao existe. Disponiveis: "
                        f"{', '.join(sorted(available))}",
                        file=sys.stderr,
                    )
                    return 2

                arguments = json.loads(raw_args) if raw_args else {}
                result = await session.call_tool(name, arguments)

                marker = "ERRO" if result.is_error else "ok"
                print(f"\n[{marker}] {name} {arguments}")
                if result.structured_content is not None:
                    print(json.dumps(result.structured_content, indent=2, ensure_ascii=False))
                else:
                    for block in result.content:
                        if getattr(block, "type", None) == "text":
                            print(block.text)
    return 0


def _parse(argv: list[str]) -> list[tuple[str, str | None]]:
    calls: list[tuple[str, str | None]] = []
    i = 0
    while i < len(argv):
        name = argv[i]
        if i + 1 < len(argv) and argv[i + 1].lstrip().startswith("{"):
            calls.append((name, argv[i + 1]))
            i += 2
        else:
            calls.append((name, None))
            i += 1
    return calls


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv[1:])))

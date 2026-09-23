"""Entrypoint do MCP Server (transporte stdio).

poetry run store-server
# ou
poetry run python -m mcp_store.server
"""

from __future__ import annotations

# O import registra as ferramentas na instancia `mcp` via decorator.
from mcp_store.server import tools  # noqa: F401
from mcp_store.server.app import logger, mcp


def main() -> None:
    logger.info("MCP server 'store' iniciando no transporte stdio")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

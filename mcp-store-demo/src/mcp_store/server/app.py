"""Instancia do MCP Server e o estado que as ferramentas compartilham."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from mcp_store import __version__
from mcp_store.logging_setup import configure_logging
from mcp_store.settings import settings
from mcp_store.store_api import StoreApiClient

logger = configure_logging(settings.log_level, "mcp_store.server")

mcp = MCPServer(
    name="store",
    version=__version__,
    instructions=(
        "Servidor da loja de produtos do PyCaxias. Expõe consulta de catálogo, "
        "criação e pagamento de pedidos, cancelamento e entrada de estoque. "
        "Preços e limites são decididos pelo servidor: informe apenas SKU e "
        "quantidade."
    ),
)

# O domínio e o estado vivem na API Flask; o MCP é somente a camada de tools.
store = StoreApiClient(settings.store_api_base_url, settings.store_api_timeout_seconds)

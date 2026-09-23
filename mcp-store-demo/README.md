# pycaxias-loja MCP

Uma loja do PyCaxias exposta como um **MCP Server** via stdio.
Clientes compatíveis, como Claude Code e Codex, iniciam o processo do servidor e
descobrem suas ferramentas pelo protocolo MCP.

## Instalação

```bash
poetry install
```

## Rodar localmente

Em outro terminal, inicie a API da loja antes do MCP:

```bash
cd ../pycaxias-store-api
poetry install
poetry run pycaxias-store-api
```

Depois, no diretório deste projeto, inicie o servidor MCP:

O servidor MCP usa stdio e aguarda um cliente compatível:

```bash
poetry run store-server
```

Para conferir as ferramentas e chamar operações sem Claude ou Codex, use a
sonda local de protocolo:

```bash
poetry run python scripts/probe.py
poetry run python scripts/probe.py search_products '{"query": "caneca"}'
```

## Ferramentas

- `search_products`: busca produtos no catálogo.
- `get_order`: consulta um pedido.
- `create_order`: reserva estoque e cria um pedido pendente.
- `pay_order`: confirma o pagamento de um pedido.
- `cancel_order`: cancela um pedido e devolve o estoque quando aplicável.
- `restock_product`: repõe estoque.

As ferramentas declaram `ToolAnnotations` para que cada cliente MCP possa
apresentar e tratar operações de leitura, escrita e destrutivas conforme a sua
própria política de aprovação. O servidor continua sendo a fonte de verdade
para validação de entrada, regras de negócio, idempotência e transições de
estado.

## Configurar no Claude Code

Use o executável absoluto do ambiente virtual:

```bash
claude mcp add pycaxias-loja -s user -- /Users/rcastilhos/Documents/mcp/mcp-store-demo/.venv/bin/store-server
```

Confira a conexão:

```bash
claude mcp list
```

## Configurar no Codex

```bash
codex mcp add pycaxias-loja -- /Users/rcastilhos/Documents/mcp/mcp-store-demo/.venv/bin/store-server
```

## Testes

```bash
poetry run pytest -v
```

`tests/test_mcp_integration.py` valida o servidor pelo protocolo MCP contra a
API local. As regras de negócio são testadas no projeto `pycaxias-store-api`.

## Configuração

| Variável | Padrão | Finalidade |
|---|---:|---|
| `STORE_API_BASE_URL` | `http://127.0.0.1:5000` | URL da API Flask local. |
| `STORE_API_TIMEOUT_SECONDS` | `5` | Timeout de chamada à API, em segundos. |
| `STORE_LOG_LEVEL` | `INFO` | Nível de log do servidor. |

Para uma implantação remota, não exponha ferramentas de escrita sem
autenticação e autorização fornecidas pelo transporte confiável. A identidade
nunca deve vir dos argumentos da ferramenta.

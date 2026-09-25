# PyCaxias 2026

Projeto de demonstração de uma loja simples, dividido em três componentes: uma API HTTP, um frontend web e um servidor MCP. O frontend e o servidor MCP usam a mesma API para consultar produtos e operar pedidos e estoque.

## Projetos

| Diretório | Função | Tecnologias |
|---|---|---|
| [`pycaxias-store-api/`](pycaxias-store-api/) | API local que concentra catálogo, estoque e pedidos. | Python 3.11+, Flask e Pydantic |
| [`pycaxias-store-frontend/`](pycaxias-store-frontend/) | Interface web estática para a loja; também registra ferramentas WebMCP em navegadores compatíveis. | HTML, CSS e JavaScript |
| [`mcp-store-demo/`](mcp-store-demo/) | Servidor MCP via stdio que expõe as operações da loja para clientes compatíveis, como Codex e Claude Code. | Python 3.11+ e MCP SDK |

## Executar localmente

São necessários Python 3.11 ou superior e Poetry para os projetos Python. Inicie cada componente em um terminal separado.

### 1. Inicie a API

```bash
cd pycaxias-store-api
poetry install
poetry run pycaxias-store-api
```

A API fica disponível em `http://127.0.0.1:5000` por padrão.

### 2. Inicie o frontend

```bash
cd pycaxias-store-frontend
python3 -m http.server 8000
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000). Para apontar o frontend para outra URL da API, use o parâmetro `?api=URL`, por exemplo `http://127.0.0.1:8000/?api=http://127.0.0.1:5000`.

### 3. Inicie o servidor MCP (opcional)

Com a API em execução, abra outro terminal:

```bash
cd mcp-store-demo
poetry install
poetry run store-server
```

O servidor MCP usa stdio e deve ser iniciado por um cliente compatível. Para instruções de configuração no Codex ou Claude Code e para consultar as ferramentas disponíveis, veja o [README do servidor MCP](mcp-store-demo/README.md).

## Operações disponíveis

A loja permite buscar produtos, consultar pedidos, criar pedidos pendentes, confirmar pagamentos, cancelar pedidos e repor estoque. A API é a fonte das regras de negócio e do estado da loja; tanto o frontend quanto as ferramentas MCP consomem suas operações.

## Documentação

- [API da loja](pycaxias-store-api/README.md): execução, configuração de host e porta e endpoints HTTP.
- [Frontend](pycaxias-store-frontend/README.md): execução local e detalhes de WebMCP.
- [Servidor MCP](mcp-store-demo/README.md): configuração de clientes, ferramentas, variáveis de ambiente e sonda local.

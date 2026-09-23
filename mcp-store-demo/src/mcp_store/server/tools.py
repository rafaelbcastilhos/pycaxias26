"""As ferramentas MCP da loja.

Duas coisas para olhar aqui, porque sao o que diferencia um MCP Server
publicavel de um script:

**1. `ToolAnnotations` em toda ferramenta.**
As quatro flags declaram o raio de acao da ferramenta e sao lidas pelo *cliente*
antes de executar qualquer coisa:

* `readOnlyHint`   — a ferramenta escreve algo?
* `destructiveHint`— a escrita e reversivel?
* `idempotentHint` — repetir a chamada tem o mesmo efeito?
* `openWorldHint`  — sai para a internet ou fica no dominio interno?

Uma ferramenta sem annotations forca o cliente a tratar tudo como potencialmente
destrutivo — e quem revisa o codigo nao tem como saber se `update_x` apaga
dados. As flags precisam refletir o comportamento **real**: declarar
`readOnlyHint=True` em algo que muta estado e pior do que nao declarar nada,
porque desliga a confirmacao do usuario no cliente.

**2. Validacao na borda, com Pydantic.**
Cada parametro carrega restricao explicita (`ge`, `le`, `max_length`, `pattern`).
O argumento de um tool call vem de um LLM, que por sua vez leu texto de terceiros
— e input externo como qualquer corpo de request HTTP. A validacao acontece antes
de a chamada alcancar o dominio.

E o que **nao** esta na assinatura tambem e uma decisao: nenhuma ferramenta
aceita `price`, `total` ou `user_id`. Preco vem do catalogo; identidade viria do
transporte autenticado. Aceitar esses campos e o convite para manipulacao de
regra de negocio (CWE-841).
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from mcp_store.domain.errors import StoreError
from mcp_store.domain.models import SKU_PATTERN
from mcp_store.server.app import logger, mcp, store

# Allowlist para a chave de idempotencia: alfanumerico, `-` e `_`, 8 a 64 chars.
IDEMPOTENCY_KEY_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"

SkuArg = Annotated[
    str,
    Field(pattern=SKU_PATTERN, description="SKU do produto, formato ABC-1234"),
]

IdempotencyKeyArg = Annotated[
    str,
    Field(
        pattern=IDEMPOTENCY_KEY_PATTERN,
        description=(
            "Chave unica desta operacao (8-64 chars, [A-Za-z0-9_-]). "
            "Ao repetir a MESMA operacao apos um erro, reenvie a MESMA chave: "
            "o servidor devolve o resultado original em vez de duplicar."
        ),
    ),
]

_GENERIC_FAILURE = "A operacao nao pode ser concluida. Tente novamente."


def _fail(tool: str, exc: Exception) -> ToolError:
    """Converte excecao em erro seguro para o chamador.

    CWE-209: `StoreError` tem mensagem curada e pode sair. Qualquer outra
    excecao vira mensagem genarica — o detalhe (e o traceback) fica so no log
    do servidor, que o chamador nao le.
    """
    if isinstance(exc, StoreError):
        return ToolError(str(exc))
    logger.exception("erro inesperado na ferramenta %s", tool)
    return ToolError(_GENERIC_FAILURE)


# ---------------------------------------------------------------------- leitura


@mcp.tool(
    annotations=ToolAnnotations(
        title="Buscar produtos",
        readOnlyHint=True,  # so consulta o catalogo
        destructiveHint=False,  # nao altera nada
        idempotentHint=True,  # mesma busca, mesmo resultado
        openWorldHint=False,  # catalogo interno, sem chamada externa
    )
)
async def search_products(
    query: Annotated[
        str,
        Field(default="", max_length=100, description="Texto livre: nome, descricao ou SKU"),
    ] = "",
    limit: Annotated[
        int,
        Field(default=5, ge=1, le=20, description="Maximo de itens no resultado"),
    ] = 5,
) -> list[dict]:
    """Busca produtos no catalogo por nome, descricao ou SKU.

    Retorna SKU, nome, preco e estoque disponivel. Use antes de criar um pedido
    para descobrir o SKU e confirmar que ha estoque.
    """
    try:
        products = await store.search_products(query=query, limit=limit)
    except Exception as exc:
        raise _fail("search_products", exc) from exc

    logger.info("search_products query_len=%d hits=%d", len(query), len(products))
    return products


@mcp.tool(
    annotations=ToolAnnotations(
        title="Consultar pedido",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def get_order(
    order_id: Annotated[
        str,
        Field(pattern=r"^ORD-[0-9a-f]{16}$", description="Id do pedido, formato ORD-<hex16>"),
    ],
) -> dict:
    """Retorna a situacao atual de um pedido: status, item, quantidade e total."""
    try:
        order = await store.get_order(order_id)
    except Exception as exc:
        raise _fail("get_order", exc) from exc

    logger.info("get_order order_id=%s status=%s", order["order_id"], order["status"])
    return order


# ---------------------------------------------------------------------- escrita


@mcp.tool(
    annotations=ToolAnnotations(
        title="Criar pedido (reserva estoque)",
        readOnlyHint=False,  # reserva estoque: muta estado
        destructiveHint=False,  # cria um recurso novo, nada e perdido
        idempotentHint=True,  # protegido por idempotency_key
        openWorldHint=False,
    )
)
async def create_order(
    sku: SkuArg,
    quantity: Annotated[
        int,
        Field(ge=1, le=100, description="Unidades desejadas (o servidor aplica o teto por pedido)"),
    ],
    idempotency_key: IdempotencyKeyArg,
) -> dict:
    """Cria um pedido em PENDING e reserva o estoque.

    O preco unitario e lido do catalogo e congelado no pedido; o total e
    calculado pelo servidor. Reservar aqui — e nao no pagamento — garante que
    duas compras simultaneas nao vendam a mesma unidade.

    Depois de criar, chame `pay_order` para confirmar. Um pedido PENDING mantem
    o estoque reservado ate ser pago ou cancelado.
    """
    try:
        order = await store.create_order(
            sku=sku, quantity=quantity, idempotency_key=idempotency_key
        )
    except Exception as exc:
        raise _fail("create_order", exc) from exc

    logger.info(
        "create_order order_id=%s sku=%s qty=%d status=%s",
        order["order_id"],
        order["sku"],
        order["quantity"],
        order["status"],
    )
    return order


@mcp.tool(
    annotations=ToolAnnotations(
        title="Pagar pedido",
        readOnlyHint=False,  # transiciona PENDING -> PAID
        destructiveHint=False,  # nao apaga nada; e reversivel por cancel_order
        idempotentHint=True,  # protegido por idempotency_key
        openWorldHint=False,  # gateway simulado; com gateway real seria True
    )
)
async def pay_order(
    order_id: Annotated[
        str,
        Field(pattern=r"^ORD-[0-9a-f]{16}$", description="Id do pedido a pagar"),
    ],
    idempotency_key: IdempotencyKeyArg,
) -> dict:
    """Confirma o pagamento de um pedido PENDING, levando-o a PAID.

    Falha se o pedido ja estiver pago ou cancelado. Reenviar a mesma
    `idempotency_key` devolve o pedido original em vez de cobrar de novo.
    """
    try:
        order = await store.pay_order(order_id=order_id, idempotency_key=idempotency_key)
    except Exception as exc:
        raise _fail("pay_order", exc) from exc

    logger.info(
        "pay_order order_id=%s status=%s total_cents=%d",
        order["order_id"],
        order["status"],
        int(float(order["total"]) * 100),
    )
    return order


@mcp.tool(
    annotations=ToolAnnotations(
        title="Cancelar pedido",
        readOnlyHint=False,
        destructiveHint=True,  # encerra o pedido; nao ha caminho de volta
        idempotentHint=False,  # a segunda chamada falha (ja cancelado)
        openWorldHint=False,
    )
)
async def cancel_order(
    order_id: Annotated[
        str,
        Field(pattern=r"^ORD-[0-9a-f]{16}$", description="Id do pedido a cancelar"),
    ],
) -> dict:
    """Cancela um pedido e devolve ao estoque as unidades reservadas.

    Operacao irreversivel: CANCELLED e estado terminal. Cancelar um pedido ja
    cancelado falha, em vez de devolver estoque duas vezes.
    """
    try:
        order = await store.cancel_order(order_id)
    except Exception as exc:
        raise _fail("cancel_order", exc) from exc

    logger.info(
        "cancel_order order_id=%s sku=%s qty_restored=%d",
        order["order_id"],
        order["sku"],
        order["quantity"],
    )
    return order


@mcp.tool(
    annotations=ToolAnnotations(
        title="Repor estoque",
        readOnlyHint=False,
        destructiveHint=False,  # soma unidades, nao remove
        idempotentHint=False,  # chamar duas vezes soma duas vezes
        openWorldHint=False,
    )
)
async def restock_product(
    sku: SkuArg,
    units: Annotated[
        int,
        Field(ge=1, le=1000, description="Unidades a acrescentar ao estoque"),
    ],
) -> dict:
    """Acrescenta unidades ao estoque de um produto.

    NAO e idempotente: duas chamadas com os mesmos argumentos somam duas vezes.
    Se a chamada falhar sem resposta, consulte o estoque com `search_products`
    antes de repetir.
    """
    try:
        product = await store.restock_product(sku=sku, units=units)
    except Exception as exc:
        raise _fail("restock_product", exc) from exc

    logger.info("restock_product sku=%s units=+%d stock=%d", product["sku"], units, product["stock"])
    return product

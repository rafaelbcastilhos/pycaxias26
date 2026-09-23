"""Logging estruturado.

Dois cuidados:

1. **stderr, nunca stdout.** No transporte stdio do MCP, stdout e o canal
   JSON-RPC. Um `print()` no servidor corrompe o protocolo. Todo log vai para
   stderr.
2. **CWE-532 (Sensitive Information in Logs).** Logamos identificadores de
   recurso (sku, order_id), quantidades e nome da ferramenta. Nao logamos
   chaves de API, `idempotency_key` do chamador nem payloads inteiros.

Em uma aplicacao Fury, troque por `melitk-logging` (e
`python_data_privacy_toolkit` quando algo sensivel precisar ir para o log).
"""

from __future__ import annotations

import logging
import sys


def configure_logging(level: str, name: str) -> logging.Logger:
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s | %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    return logging.getLogger(name)

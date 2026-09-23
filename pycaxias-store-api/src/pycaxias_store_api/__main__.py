"""Entrypoint da API Flask local."""

from __future__ import annotations

import os

from pycaxias_store_api.app import create_app


def main() -> None:
    create_app().run(
        host=os.getenv("PYCAXIAS_STORE_API_HOST", "127.0.0.1"),
        port=int(os.getenv("PYCAXIAS_STORE_API_PORT", "5000")),
        debug=False,
    )


if __name__ == "__main__":
    main()

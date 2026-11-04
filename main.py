from __future__ import annotations

import os

import uvicorn

from creator_app.api import create_app
from creator_app.control_universe import install_control_universe

app = create_app()
install_control_universe(app)


def main() -> None:
    uvicorn.run(
        app,
        host=os.getenv("CKNEXUS_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
    )


if __name__ == "__main__":
    main()

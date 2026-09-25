"""Run the Telegram bot and Flask Mini App server."""

from __future__ import annotations

import os
import threading

from flask import Flask

from .bot import run


def run_flask() -> None:
    """Run Flask server."""
    from server import app

    port = int(
        os.environ.get(
            "PORT",
            "5000",
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    flask_thread = threading.Thread(
        target=run_flask,
        daemon=True,
    )

    flask_thread.start()

    run()

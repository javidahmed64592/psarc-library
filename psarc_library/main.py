"""Main entry point for the Psarc library server."""

from psarc_library.server import PsarcLibraryServer


def run() -> None:
    """Serve the FastAPI application using uvicorn.

    :raise SystemExit: If configuration fails to load or SSL certificate files are missing
    """
    server = PsarcLibraryServer()
    server.run()

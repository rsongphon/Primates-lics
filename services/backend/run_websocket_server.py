#!/usr/bin/env python3
"""
LICS WebSocket Server

Standalone Socket.IO server for real-time communication.
Runs on port 8001 alongside the main HTTP API server.
"""

import asyncio
import uvicorn
from app.websocket.server import get_sio_app
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

def main():
    """Start the WebSocket server."""
    logger.info("Starting LICS WebSocket Server...")
    logger.info(f"WebSocket Host: {settings.WEBSOCKET_HOST}")
    logger.info(f"WebSocket Port: {settings.WEBSOCKET_PORT}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Get the Socket.IO ASGI app
    socket_app = get_sio_app()

    # Configure uvicorn for WebSocket server
    config = uvicorn.Config(
        app=socket_app,
        host=settings.WEBSOCKET_HOST,
        port=settings.WEBSOCKET_PORT,
        log_level="info" if settings.DEBUG else "warning",
        access_log=settings.DEBUG,
        ws_ping_interval=settings.WEBSOCKET_PING_INTERVAL,
        ws_ping_timeout=settings.WEBSOCKET_PING_TIMEOUT,
    )

    # Start the server
    server = uvicorn.Server(config)

    logger.info(f"WebSocket server starting on {settings.WEBSOCKET_HOST}:{settings.WEBSOCKET_PORT}")
    server.run()

if __name__ == "__main__":
    main()
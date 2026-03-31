import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.client_sessions: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_sessions.setdefault(client_id, set())
        logger.info(f"Client connected: {client_id}")

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        self.client_sessions.pop(client_id, None)
        logger.info(f"Client disconnected: {client_id}")

    async def send_json(self, client_id: str, data: dict):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(data)

    async def send_text(self, client_id: str, text: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(text)

    async def broadcast(self, data: dict, exclude: str = None):
        for client_id, ws in self.active_connections.items():
            if client_id != exclude:
                try:
                    await ws.send_json(data)
                except Exception as e:
                    logger.error(f"Broadcast failed to {client_id}: {e}")

    async def send_audio(self, client_id: str, audio_data: bytes):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_bytes(audio_data)

    def get_active_clients(self) -> list[str]:
        return list(self.active_connections.keys())

    def is_connected(self, client_id: str) -> bool:
        return client_id in self.active_connections

"""Asyncio websocket client. Runs a background receive loop that pushes
parsed ServerMessage objects onto a queue for the render loop to consume.
"""
from __future__ import annotations

import asyncio
import json

import websockets

from shared.models import ClientMessage, ServerMessage, parse_server_message


class NetworkClient:
    def __init__(self, websocket) -> None:
        self._ws = websocket
        self.incoming: asyncio.Queue[ServerMessage] = asyncio.Queue()
        self._recv_task: asyncio.Task | None = None

    @classmethod
    async def connect(cls, uri: str) -> "NetworkClient":
        ws = await websockets.connect(uri)
        client = cls(ws)
        client._recv_task = asyncio.create_task(client._receive_loop())
        return client

    async def _receive_loop(self) -> None:
        async for raw in self._ws:
            data = json.loads(raw)
            msg = parse_server_message(data)
            await self.incoming.put(msg)

    async def send(self, action: ClientMessage) -> None:
        await self._ws.send(action.model_dump_json())

    async def close(self) -> None:
        if self._recv_task:
            self._recv_task.cancel()
        await self._ws.close()

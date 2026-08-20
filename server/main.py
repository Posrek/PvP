"""WebSocket server entrypoint. Pairs incoming connections two at a time and
runs a GameSession for each pair.
"""
from __future__ import annotations

import asyncio
import logging

from websockets.asyncio.server import ServerConnection, serve

from server.session import GameSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

HOST = "0.0.0.0"
PORT = 8765

_lock = asyncio.Lock()
_waiting: ServerConnection | None = None
_waiting_future: asyncio.Future | None = None


async def handler(websocket: ServerConnection) -> None:
    global _waiting, _waiting_future

    async with _lock:
        if _waiting is None:
            _waiting = websocket
            _waiting_future = asyncio.get_running_loop().create_future()
            my_future = _waiting_future
            am_first = True
        else:
            partner = _waiting
            partner_future = _waiting_future
            _waiting = None
            _waiting_future = None
            session = GameSession([partner, websocket])
            partner_future.set_result((session, 0))
            session_result = (session, 1)
            am_first = False

    logger.info("Player connected: %s", websocket.remote_address)

    if am_first:
        session, idx = await my_future
    else:
        session, idx = session_result
        await session.broadcast_state()

    logger.info("Game session active for player index %d", idx)
    await session.listen(idx)
    logger.info("Player disconnected: %s", websocket.remote_address)


async def main() -> None:
    async with serve(handler, HOST, PORT) as server:
        logger.info("Server listening on ws://%s:%d", HOST, PORT)
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

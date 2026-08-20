"""Pygame client entrypoint. Runs the pygame render loop and the asyncio
websocket network loop together on one event loop.
"""
from __future__ import annotations

import asyncio
import sys

import pygame

from client.network import NetworkClient
from client.ui.render import HEIGHT, WIDTH, ClientState, draw
from shared.models import (
    GameOver,
    OpponentLocked,
    PlayCardAction,
    PlayerView,
    ReadyAction,
    TurnResolved,
    UnqueueCardAction,
)

FPS = 60
DEFAULT_URI = "ws://localhost:8765"


async def run(uri: str) -> None:
    pygame.init()
    pygame.display.set_caption("PvP Card Game")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    small_font = pygame.font.SysFont("consolas", 14)
    font = pygame.font.SysFont("consolas", 20)
    big_font = pygame.font.SysFont("consolas", 42, bold=True)

    state = ClientState()
    network = await NetworkClient.connect(uri)
    state.connected = True

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                _handle_click(event.pos, state, network)

        while not network.incoming.empty():
            msg = network.incoming.get_nowait()
            _apply_message(state, msg)

        draw(screen, font, small_font, big_font, state)
        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(0)

    await network.close()
    pygame.quit()


def _handle_click(pos, state: ClientState, network: NetworkClient) -> None:
    if state.status != "choosing" or state.your_locked:
        return

    if state.ready_button_rect is not None and state.ready_button_rect.collidepoint(pos):
        asyncio.create_task(network.send(ReadyAction()))
        return

    for card_id, rect in state.queue_card_rects.items():
        if rect.collidepoint(pos):
            asyncio.create_task(network.send(UnqueueCardAction(card_id=card_id)))
            return

    for card_id, rect in state.hand_card_rects.items():
        if rect.collidepoint(pos):
            asyncio.create_task(network.send(PlayCardAction(card_id=card_id)))
            return


def _apply_message(state: ClientState, msg) -> None:
    if isinstance(msg, PlayerView):
        state.your_hand = msg.your_hand
        state.your_health = msg.your_health
        state.your_queue = msg.your_queue
        state.your_locked = msg.your_locked
        state.your_budget_remaining = msg.your_budget_remaining
        state.your_equipped = msg.your_equipped
        state.opponent_hand_count = msg.opponent_hand_count
        state.opponent_health = msg.opponent_health
        state.opponent_queue_count = msg.opponent_queue_count
        state.opponent_locked = msg.opponent_locked
        state.opponent_equipped = msg.opponent_equipped
        state.status = msg.status
        state.turn_number = msg.turn_number
    elif isinstance(msg, OpponentLocked):
        state.opponent_locked = True
    elif isinstance(msg, TurnResolved):
        state.last_reveal = msg
    elif isinstance(msg, GameOver):
        state.game_over = msg


def main() -> None:
    uri = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URI
    asyncio.run(run(uri))


if __name__ == "__main__":
    main()

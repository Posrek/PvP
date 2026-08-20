"""Pure rendering helpers for the pygame client. Takes the current
ClientState and draws it to the given surface; no networking or game logic
lives here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pygame

from shared.game_rules import TURN_BUDGET
from shared.models import ArmorCard, AttackCard, EquippedGear, GameOver, ItemCard, TurnResolved, WeaponCard

WIDTH, HEIGHT = 1000, 700
CARD_W, CARD_H = 80, 120
QUEUE_CARD_W, QUEUE_CARD_H = 60, 90
GEAR_W, GEAR_H = 60, 60

BG_COLOR = (24, 28, 38)
CARD_COLOR = (235, 235, 240)
CARD_BACK_COLOR = (70, 80, 110)
CARD_BORDER = (10, 10, 15)
QUEUE_BORDER = (120, 140, 220)
LOCKED_BORDER = (90, 200, 120)
GEAR_COLOR = (60, 70, 50)
TEXT_COLOR = (230, 230, 235)
ACCENT = (250, 210, 90)
HEALTH_COLOR = (200, 60, 60)
HEALTH_BG = (60, 20, 20)


@dataclass
class ClientState:
    connected: bool = False
    your_hand: list = field(default_factory=list)
    your_health: int = 0
    your_queue: list = field(default_factory=list)  # list[QueuedCard]
    your_locked: bool = False
    your_budget_remaining: int = TURN_BUDGET
    your_equipped: Optional[EquippedGear] = None
    opponent_hand_count: int = 0
    opponent_health: int = 0
    opponent_queue_count: int = 0
    opponent_locked: bool = False
    opponent_equipped: Optional[EquippedGear] = None
    status: str = "waiting_for_opponent_join"
    turn_number: int = 1
    last_reveal: Optional[TurnResolved] = None
    game_over: Optional[GameOver] = None
    hand_card_rects: dict = field(default_factory=dict)  # card_id -> pygame.Rect
    queue_card_rects: dict = field(default_factory=dict)  # card_id -> pygame.Rect
    ready_button_rect: Optional[pygame.Rect] = None


def draw(surface: pygame.Surface, font: pygame.font.Font, small_font: pygame.font.Font, big_font: pygame.font.Font, state: ClientState) -> None:
    surface.fill(BG_COLOR)

    _draw_text(surface, font, f"Turn {state.turn_number}", (20, 12), ACCENT)

    _draw_health_bar(surface, font, state.opponent_health, (WIDTH - 260, 12), label="Opponent")
    _draw_health_bar(surface, font, state.your_health, (20, HEIGHT - 34), label="You")

    _draw_equipped(surface, small_font, state.opponent_equipped, (WIDTH - 20 - 4 * (GEAR_W + 8), 50), label="Opponent gear")
    _draw_equipped(surface, small_font, state.your_equipped, (20, HEIGHT - 34 - GEAR_H - 40), label="Your gear")

    _draw_opponent_queue(surface, small_font, state)
    _draw_your_queue(surface, small_font, state)
    _draw_your_hand(surface, font, state)
    _draw_status(surface, font, state)
    _draw_ready_button(surface, font, state)

    if state.last_reveal is not None:
        _draw_reveal(surface, small_font, state.last_reveal)

    if state.game_over is not None:
        _draw_game_over(surface, big_font, font, state.game_over)

    if not state.connected:
        _draw_text(surface, big_font, "Connecting...", (WIDTH // 2 - 120, HEIGHT // 2 - 20), ACCENT)


def _draw_text(surface, font, text, pos, color=TEXT_COLOR) -> None:
    surface.blit(font.render(text, True, color), pos)


def _draw_health_bar(surface: pygame.Surface, font: pygame.font.Font, health: int, pos, label: str) -> None:
    x, y = pos
    w, h = 220, 20
    max_health = 30  # matches shared.game_rules.START_HEALTH; purely cosmetic if it changes
    pygame.draw.rect(surface, HEALTH_BG, (x, y, w, h), border_radius=4)
    fill_w = max(0, min(w, int(w * health / max_health)))
    pygame.draw.rect(surface, HEALTH_COLOR, (x, y, fill_w, h), border_radius=4)
    pygame.draw.rect(surface, CARD_BORDER, (x, y, w, h), width=2, border_radius=4)
    _draw_text(surface, font, f"{label}: {health} HP", (x + 6, y + 1), TEXT_COLOR)


def _gear_label(card) -> str:
    if isinstance(card, WeaponCard):
        return f"{card.name}\ndmg {card.damage} dur {card.durability}"
    if isinstance(card, ArmorCard):
        return f"{card.name}\ndef {card.defense}"
    if isinstance(card, ItemCard):
        return f"{card.name}\ndur {card.durability}"
    return card.name


def _draw_equipped(surface: pygame.Surface, font: pygame.font.Font, gear: Optional[EquippedGear], pos, label: str) -> None:
    x, y = pos
    _draw_text(surface, font, label, (x, y - 16), ACCENT)
    slots = []
    if gear is not None:
        slots = [gear.weapon, gear.armor_head, gear.armor_torso, gear.item]
    for i in range(4):
        rect = pygame.Rect(x + i * (GEAR_W + 8), y, GEAR_W, GEAR_H)
        card = slots[i] if i < len(slots) else None
        pygame.draw.rect(surface, GEAR_COLOR if card else (40, 40, 46), rect, border_radius=6)
        pygame.draw.rect(surface, CARD_BORDER, rect, width=2, border_radius=6)
        if card is not None:
            for j, line in enumerate(_gear_label(card).split("\n")):
                surf = font.render(line, True, TEXT_COLOR)
                surface.blit(surf, surf.get_rect(center=(rect.centerx, rect.centery - 8 + j * 14)))


def _draw_opponent_queue(surface: pygame.Surface, font: pygame.font.Font, state: ClientState) -> None:
    total_w = state.opponent_queue_count * (QUEUE_CARD_W + 8)
    start_x = WIDTH // 2 - total_w // 2
    y = 130
    for i in range(state.opponent_queue_count):
        rect = pygame.Rect(start_x + i * (QUEUE_CARD_W + 8), y, QUEUE_CARD_W, QUEUE_CARD_H)
        pygame.draw.rect(surface, CARD_BACK_COLOR, rect, border_radius=6)
        pygame.draw.rect(surface, CARD_BORDER, rect, width=2, border_radius=6)
    if state.opponent_locked:
        border = (start_x - 8, y - 8, max(total_w, 1) + 16, QUEUE_CARD_H + 16)
        pygame.draw.rect(surface, LOCKED_BORDER, border, width=3, border_radius=10)
    hand_total_w = state.opponent_hand_count * 14
    _draw_text(surface, font, f"Opponent hand: {state.opponent_hand_count}", (WIDTH // 2 - hand_total_w, 100), TEXT_COLOR)


def _card_stat_line(card) -> str:
    if isinstance(card, AttackCard):
        return f"atk {card.direction}"
    if isinstance(card, WeaponCard):
        return f"dmg {card.damage}"
    if isinstance(card, ArmorCard):
        return f"def {card.defense} {card.direction}"
    if isinstance(card, ItemCard):
        return f"dur {card.durability}"
    return "action"


def _draw_card(surface, font, rect, card, border_color) -> None:
    pygame.draw.rect(surface, CARD_COLOR, rect, border_radius=8)
    pygame.draw.rect(surface, border_color, rect, width=3, border_radius=8)
    name_surf = font.render(card.name[:10], True, (20, 20, 25))
    surface.blit(name_surf, name_surf.get_rect(center=(rect.centerx, rect.top + 16)))
    stat_surf = font.render(_card_stat_line(card), True, (20, 20, 25))
    surface.blit(stat_surf, stat_surf.get_rect(center=(rect.centerx, rect.centery + 4)))
    cost_surf = font.render(f"cost {card.cost}", True, (20, 20, 25))
    surface.blit(cost_surf, cost_surf.get_rect(center=(rect.centerx, rect.bottom - 14)))


def _draw_your_queue(surface: pygame.Surface, font: pygame.font.Font, state: ClientState) -> None:
    state.queue_card_rects.clear()
    total_w = len(state.your_queue) * (QUEUE_CARD_W + 8)
    start_x = WIDTH // 2 - total_w // 2
    y = HEIGHT - CARD_H - QUEUE_CARD_H - 60
    for i, queued in enumerate(state.your_queue):
        rect = pygame.Rect(start_x + i * (QUEUE_CARD_W + 8), y, QUEUE_CARD_W, QUEUE_CARD_H)
        _draw_card(surface, font, rect, queued.card, QUEUE_BORDER)
        sec_surf = font.render(f"t={queued.second}s", True, (20, 20, 25))
        surface.blit(sec_surf, sec_surf.get_rect(center=(rect.centerx, rect.top + 30)))
        state.queue_card_rects[queued.card.id] = rect
    if state.your_locked:
        border = (start_x - 8, y - 8, max(total_w, 1) + 16, QUEUE_CARD_H + 16)
        pygame.draw.rect(surface, LOCKED_BORDER, border, width=3, border_radius=10)


def _draw_your_hand(surface: pygame.Surface, font: pygame.font.Font, state: ClientState) -> None:
    state.hand_card_rects.clear()
    total_w = len(state.your_hand) * (CARD_W + 10)
    start_x = WIDTH // 2 - total_w // 2
    y = HEIGHT - CARD_H - 30
    for i, card in enumerate(state.your_hand):
        rect = pygame.Rect(start_x + i * (CARD_W + 10), y, CARD_W, CARD_H)
        _draw_card(surface, font, rect, card, CARD_BORDER)
        state.hand_card_rects[card.id] = rect


def _draw_status(surface: pygame.Surface, font: pygame.font.Font, state: ClientState) -> None:
    if state.status == "waiting_for_opponent_join":
        msg = "Waiting for opponent to join..."
    elif state.status == "choosing":
        if state.your_locked and state.opponent_locked:
            msg = "Resolving turn..."
        elif state.your_locked:
            msg = "Waiting for opponent..."
        else:
            msg = f"Budget left: {state.your_budget_remaining}/{TURN_BUDGET} — click a card to queue it"
    elif state.status == "game_over":
        msg = "Game over"
    else:
        msg = ""
    _draw_text(surface, font, msg, (20, HEIGHT - CARD_H - QUEUE_CARD_H - 90), ACCENT)


def _draw_ready_button(surface: pygame.Surface, font: pygame.font.Font, state: ClientState) -> None:
    if state.status != "choosing" or state.your_locked:
        state.ready_button_rect = None
        return
    rect = pygame.Rect(WIDTH - 140, HEIGHT - CARD_H - QUEUE_CARD_H - 90, 120, 36)
    state.ready_button_rect = rect
    pygame.draw.rect(surface, (60, 140, 90), rect, border_radius=6)
    pygame.draw.rect(surface, CARD_BORDER, rect, width=2, border_radius=6)
    text_surf = font.render("Ready", True, TEXT_COLOR)
    surface.blit(text_surf, text_surf.get_rect(center=rect.center))


def _draw_reveal(surface: pygame.Surface, font: pygame.font.Font, reveal: TurnResolved) -> None:
    y = HEIGHT // 2 - 60
    _draw_text(surface, font, f"Turn {reveal.turn_number} resolved:", (20, y), ACCENT)
    your_names = ", ".join(c.name for c in reveal.your_cards) or "(nothing)"
    opp_names = ", ".join(c.name for c in reveal.opponent_cards) or "(nothing)"
    _draw_text(surface, font, f"You played: {your_names}", (20, y + 22), TEXT_COLOR)
    _draw_text(surface, font, f"Opponent played: {opp_names}", (20, y + 44), TEXT_COLOR)
    _draw_text(surface, font, f"Health — you: {reveal.your_health}  opponent: {reveal.opponent_health}", (20, y + 66), TEXT_COLOR)


def _draw_game_over(surface: pygame.Surface, big_font: pygame.font.Font, font: pygame.font.Font, result: GameOver) -> None:
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))
    title = {"you": "You win!", "opponent": "You lose!", "tie": "It's a tie!"}[result.winner]
    title_surf = big_font.render(title, True, ACCENT)
    surface.blit(title_surf, title_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
    hp_surf = font.render(f"Final HP — you: {result.your_health}  opponent: {result.opponent_health}", True, TEXT_COLOR)
    surface.blit(hp_surf, hp_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

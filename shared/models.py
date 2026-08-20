"""Shared data models for messages passed between client and server.

Server holds the authoritative GameState; each client only ever receives a
PlayerView, which hides the opponent's hand contents (but not their equipped
gear or turn-queue state, which is public board info).
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

PlayerId = str


class Card(BaseModel): #+ editiramo base class
    id: str
    name: str
    cost: int
    description: str

class AttackCard(Card):
    direction: str
    status: Optional[str] = None

class BlockCard(Card):
    defense: int
    status: Optional[str] = None

class ItemCard(Card):
    durability: int
    status: Optional[str] = None

class ActionCard(Card):
    status: Optional[str] = None

class WeaponCard(Card):
    damage: int
    durability: int
    status: Optional[str] = None

class ArmorCard(Card):
    defense: int
    direction: str
    status: Optional[str] = None


class EquippedGear(BaseModel):
    """A player's currently-equipped gear. Public board state — sent for
    both players, unlike hand contents."""
    weapon: Optional[WeaponCard] = None
    armor_head: Optional[ArmorCard] = None
    armor_torso: Optional[ArmorCard] = None
    item: Optional[ItemCard] = None


class QueuedCard(BaseModel):
    """A card queued for this turn, with its computed execution second."""
    card: Card
    second: int


# ---------------------------------------------------------------------------
# Server -> Client
# ---------------------------------------------------------------------------

class PlayerView(BaseModel):
    """What a single player is allowed to see."""
    type: Literal["state"] = "state"
    turn_number: int
    your_hand: list[Card]
    your_health: int
    your_queue: list[QueuedCard]
    your_locked: bool
    your_budget_remaining: int
    your_equipped: EquippedGear
    opponent_hand_count: int
    opponent_health: int
    opponent_queue_count: int
    opponent_locked: bool
    opponent_equipped: EquippedGear
    status: Literal["waiting_for_opponent_join", "choosing", "resolving", "game_over"]


class OpponentLocked(BaseModel):
    """Sent the moment the opponent locks in their queue for the turn,
    before resolution. Reveals only that they're ready, not what they queued.
    """
    type: Literal["opponent_locked"] = "opponent_locked"


class TurnResolved(BaseModel):
    """Sent to both clients once a turn resolves; reveals both plays."""
    type: Literal["turn_resolved"] = "turn_resolved"
    turn_number: int
    your_cards: list[Card]
    opponent_cards: list[Card]
    your_health: int
    opponent_health: int


class GameOver(BaseModel):
    type: Literal["game_over"] = "game_over"
    winner: Literal["you", "opponent", "tie"]
    your_health: int
    opponent_health: int


class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str


ServerMessage = PlayerView | OpponentLocked | TurnResolved | GameOver | ErrorMessage


# ---------------------------------------------------------------------------
# Client -> Server
# ---------------------------------------------------------------------------

class PlayCardAction(BaseModel):
    """Add a card from hand into this turn's queue."""
    type: Literal["play_card"] = "play_card"
    card_id: str


class UnqueueCardAction(BaseModel):
    """Take a card back out of this turn's queue, before locking in."""
    type: Literal["unqueue_card"] = "unqueue_card"
    card_id: str


class ReadyAction(BaseModel):
    """Lock in the current queue for this turn."""
    type: Literal["ready"] = "ready"


ClientMessage = PlayCardAction | UnqueueCardAction | ReadyAction


def parse_server_message(raw: dict) -> ServerMessage:
    kind = raw.get("type")
    mapping: dict[str, type[BaseModel]] = {
        "state": PlayerView,
        "opponent_locked": OpponentLocked,
        "turn_resolved": TurnResolved,
        "game_over": GameOver,
        "error": ErrorMessage,
    }
    model = mapping.get(kind)
    if model is None:
        raise ValueError(f"Unknown server message type: {kind!r}")
    return model.model_validate(raw)


def parse_client_message(raw: dict) -> ClientMessage:
    kind = raw.get("type")
    mapping: dict[str, type[BaseModel]] = {
        "play_card": PlayCardAction,
        "unqueue_card": UnqueueCardAction,
        "ready": ReadyAction,
    }
    model = mapping.get(kind)
    if model is None:
        raise ValueError(f"Unknown client message type: {kind!r}")
    return model.model_validate(raw)

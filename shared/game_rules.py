"""Card dealing for testing.

There's no real deckbuilding yet (limited copies, draw piles, etc). For now
every player is dealt one independent copy of every card defined in
shared/cards.py, so every card type can be exercised while combat rules are
being designed.

resolve_turn (durability, damage, status, defense, direction, cost) is not
implemented yet — that's the next step, designed together once the core
mechanics are pinned down.
"""
from __future__ import annotations

from shared.cards import ALL_CARDS
from shared.models import Card

HAND_SIZE = len(ALL_CARDS)

# Combat tuning constants — placeholders, adjust freely.
TURN_BUDGET = 5  # max total card cost a player can queue in one turn (turn is a 5-second timeline)
UNARMED_DAMAGE = 1  # damage an AttackCard deals when the attacker has no weapon equipped
START_HEALTH = 30


def deal_hand(player_index: int) -> list[Card]:
    """Every player gets their own independent copy of every card, since
    per-card state (durability, etc) will mutate independently per player
    once combat logic exists.
    """
    return [card.model_copy(deep=True) for card in ALL_CARDS]

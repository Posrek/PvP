"""Authoritative game session for exactly two connected players.

Holds the real GameState (both hands, equipped gear, health). Each player
only ever receives a PlayerView (shared.models) built for them, which hides
the opponent's hand contents — but not their equipped gear or queue/lock
state, which is public board info.

Turn structure: each player queues cards (in any order) up to a total cost
of TURN_BUDGET seconds, then locks in with ReadyAction. Once both are
locked, both queues are merged into one timeline by each card's computed
timestamp and resolved in chronological order (ties broken by player index).
"""
from __future__ import annotations

import json

from websockets.asyncio.server import ServerConnection
from websockets.exceptions import ConnectionClosed

from shared.game_rules import START_HEALTH, TURN_BUDGET, UNARMED_DAMAGE, deal_hand
from shared.models import (
    ArmorCard,
    AttackCard,
    Card,
    EquippedGear,
    ErrorMessage,
    GameOver,
    ItemCard,
    OpponentLocked,
    PlayCardAction,
    PlayerView,
    QueuedCard,
    ReadyAction,
    TurnResolved,
    UnqueueCardAction,
    WeaponCard,
    parse_client_message,
)


def _slot_for(card: Card) -> str | None:
    """Which equip slot a card goes into, or None if it isn't equipment."""
    if isinstance(card, WeaponCard):
        return "weapon"
    if isinstance(card, ArmorCard):
        return "armor_head" if card.direction == "head" else "armor_torso"
    if isinstance(card, ItemCard):
        return "item"
    return None


class GameSession:
    def __init__(self, connections: list[ServerConnection]):
        self.connections = connections  # index 0 and 1
        self.hands = {0: deal_hand(0), 1: deal_hand(1)}
        self.health = {0: START_HEALTH, 1: START_HEALTH}
        self.equipped: dict[int, dict[str, Card]] = {0: {}, 1: {}}
        self.queue: dict[int, list[Card]] = {0: [], 1: []}
        self.locked = {0: False, 1: False}
        self.turn_number = 1
        self.status = "choosing"
        self.game_over = False

    def other(self, idx: int) -> int:
        return 1 - idx

    async def send(self, idx: int, msg) -> None:
        try:
            await self.connections[idx].send(msg.model_dump_json())
        except ConnectionClosed:
            pass

    def _equipped_view(self, idx: int) -> EquippedGear:
        slots = self.equipped[idx]
        return EquippedGear(
            weapon=slots.get("weapon"),
            armor_head=slots.get("armor_head"),
            armor_torso=slots.get("armor_torso"),
            item=slots.get("item"),
        )

    def build_view(self, idx: int) -> PlayerView:
        other = self.other(idx)

        your_queue_view: list[QueuedCard] = []
        running = 0
        for card in self.queue[idx]:
            running += card.cost
            your_queue_view.append(QueuedCard(card=card, second=running))

        return PlayerView(
            turn_number=self.turn_number,
            your_hand=self.hands[idx],
            your_health=self.health[idx],
            your_queue=your_queue_view,
            your_locked=self.locked[idx],
            your_budget_remaining=TURN_BUDGET - sum(c.cost for c in self.queue[idx]),
            your_equipped=self._equipped_view(idx),
            opponent_hand_count=len(self.hands[other]),
            opponent_health=self.health[other],
            opponent_queue_count=len(self.queue[other]),
            opponent_locked=self.locked[other],
            opponent_equipped=self._equipped_view(other),
            status=self.status,
        )

    async def broadcast_state(self) -> None:
        for idx in (0, 1):
            await self.send(idx, self.build_view(idx))

    async def listen(self, idx: int) -> None:
        ws = self.connections[idx]
        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                    action = parse_client_message(data)
                except (ValueError, json.JSONDecodeError) as exc:
                    await self.send(idx, ErrorMessage(message=str(exc)))
                    continue
                await self.handle_action(idx, action)
        except ConnectionClosed:
            pass

    async def handle_action(self, idx: int, action) -> None:
        if self.game_over or self.locked[idx]:
            return
        if isinstance(action, PlayCardAction):
            await self._handle_play(idx, action)
        elif isinstance(action, UnqueueCardAction):
            await self._handle_unqueue(idx, action)
        elif isinstance(action, ReadyAction):
            await self._handle_ready(idx)

    async def _handle_play(self, idx: int, action: PlayCardAction) -> None:
        hand = self.hands[idx]
        card = next((c for c in hand if c.id == action.card_id), None)
        if card is None:
            await self.send(idx, ErrorMessage(message="Invalid card id"))
            return

        queued_cost = sum(c.cost for c in self.queue[idx])
        if queued_cost + card.cost > TURN_BUDGET:
            await self.send(idx, ErrorMessage(message="Not enough turn budget remaining"))
            return

        hand.remove(card)
        self.queue[idx].append(card)
        await self.broadcast_state()

    async def _handle_unqueue(self, idx: int, action: UnqueueCardAction) -> None:
        queue = self.queue[idx]
        card = next((c for c in queue if c.id == action.card_id), None)
        if card is None:
            await self.send(idx, ErrorMessage(message="Card not in queue"))
            return

        queue.remove(card)
        self.hands[idx].append(card)
        await self.broadcast_state()

    async def _handle_ready(self, idx: int) -> None:
        self.locked[idx] = True
        await self.send(self.other(idx), OpponentLocked())
        await self.broadcast_state()

        if all(self.locked.values()):
            await self.resolve_turn()

    def _resolve_attack(self, attacker_idx: int, defender_idx: int, card: AttackCard) -> None:
        weapon = self.equipped[attacker_idx].get("weapon")
        damage = weapon.damage if weapon is not None else UNARMED_DAMAGE

        armor_slot = "armor_head" if card.direction == "head" else "armor_torso"
        armor = self.equipped[defender_idx].get(armor_slot)
        if armor is not None:
            damage = max(0, damage - armor.defense)

        self.health[defender_idx] = max(0, self.health[defender_idx] - damage)

    async def resolve_turn(self) -> None:
        idx_a, idx_b = 0, 1

        # Merge both players' queues into one timeline: (second, player_idx, card).
        # Sorting by (second, player_idx) gives player 0 priority on ties.
        events: list[tuple[int, int, Card]] = []
        for idx in (idx_a, idx_b):
            running = 0
            for card in self.queue[idx]:
                running += card.cost
                events.append((running, idx, card))
        events.sort(key=lambda e: (e[0], e[1]))

        played_cards: dict[int, list[Card]] = {idx_a: [], idx_b: []}

        for _second, idx, card in events:
            played_cards[idx].append(card)
            slot = _slot_for(card)
            if slot is not None:
                self.equipped[idx][slot] = card
            elif isinstance(card, AttackCard):
                self._resolve_attack(idx, self.other(idx), card)
            # ActionCard: no generic effect yet (bespoke per-card rules, TODO).

        # End-of-turn upkeep: equipped gear wears down every turn, regardless of use.
        for idx in (idx_a, idx_b):
            weapon = self.equipped[idx].get("weapon")
            if weapon is not None:
                weapon.durability -= 1
                if weapon.durability <= 0:
                    self.equipped[idx]["weapon"] = None

            for slot in ("armor_head", "armor_torso"):
                armor = self.equipped[idx].get(slot)
                if armor is not None:
                    armor.defense -= 1
                    if armor.defense <= 0:
                        self.equipped[idx][slot] = None

        for idx in (idx_a, idx_b):
            other = self.other(idx)
            await self.send(
                idx,
                TurnResolved(
                    turn_number=self.turn_number,
                    your_cards=played_cards[idx],
                    opponent_cards=played_cards[other],
                    your_health=self.health[idx],
                    opponent_health=self.health[other],
                ),
            )

        self.queue = {0: [], 1: []}
        self.locked = {0: False, 1: False}
        self.turn_number += 1

        if self.health[idx_a] <= 0 or self.health[idx_b] <= 0:
            self.game_over = True
            self.status = "game_over"
            for idx in (idx_a, idx_b):
                other = self.other(idx)
                my_dead = self.health[idx] <= 0
                opp_dead = self.health[other] <= 0
                if my_dead and opp_dead:
                    winner = "tie"
                elif opp_dead:
                    winner = "you"
                else:
                    winner = "opponent"
                await self.send(
                    idx,
                    GameOver(
                        winner=winner,
                        your_health=self.health[idx],
                        opponent_health=self.health[other],
                    ),
                )
            for ws in self.connections:
                await ws.close()
        else:
            self.status = "choosing"
            await self.broadcast_state()

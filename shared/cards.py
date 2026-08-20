"""Concrete card definitions for each character's deck.

shared/models.py defines the *shape* of a card (the classes); this file
defines the actual *content* — every specific card that exists in the game.
"""
from shared.models import ActionCard, ArmorCard, AttackCard, Card, ItemCard, WeaponCard

# --- Warrior ---

tempo = AttackCard(
    id="a1tempo",
    name="Tempo",
    cost=2,
    description="Attack opponent in the torso",
    direction="torso",
)

pretres = AttackCard(
    id="a2pretres",
    name="Pretres mozganov",
    cost=3,
    description="Napadi nasprotnika v glavo." \
    "Ce uspesno napadas s topim orozjem in nasprotnik prejme skodo nasprotnik pocaka eno sekundo",
    direction="head",
)

britvica = WeaponCard(
    id="w1britvica",
    name="Britvica norcev",
    cost=2,
    description="Ko nataknes britvico norcev prejmi eno tocko skode",
    status="deal 1 dmg to self",
    damage=3,
    durability=2
)

deska = ArmorCard(
    id="s1deska",
    name="Deska",
    cost=1,
    description="Shield - ocitno se borimo zraven deskarne",
    status="draw 1 card",
    defense=2,
    direction="torso",
)

kocka = ArmorCard(
    id="s2kocka",
    name="Kocka",
    cost=4,
    description="Helmet - tvoji napadi naredijo eno tocko skode manj",
    status="-1 dmg to self",
    defense=6,
    direction="head",
)

zelezni = ItemCard(
    id="i1zelezni",
    name="Zelezni prstan",
    durability=4,
    cost=1,
    description="Vsa tvoja oprema ima eno dodatno tocko trpeznosti"
)

darilo = ActionCard(
    id="c1darilo",
    name="Darilo",
    cost=1,
    description="Nadani kos opreme na sebi nasprotniku",
    status="durability ALL +1"
)

embargo = ActionCard(
    id="c2embargo",
    name="Embargo",
    cost=1,
    description="Prepovej nasprotniku uporabiti svoje opreme",
    status="enemy cannot use WeaponCards & ActionCards"
)

# --- Mage ---
# ... define your own cards here, following the same pattern. Use
# BlockCard / WeaponCard / ArmorCard / ActionCard from shared.models as
# needed. Every card's `id` must be unique across the whole file.

# Every card that exists in the game. Add new cards to this list as you
# define them above — game_rules.py uses this to build the test deck.
ALL_CARDS: list[Card] = [
    tempo,
    pretres,
    britvica,
    deska,
    kocka,
    zelezni,
    darilo,
    embargo,
]

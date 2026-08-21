# PvP Card Game

An online 2-player card game. Each player runs a desktop client and connects
to a shared server. Hands are private — you only ever see your own cards in
full; your opponent's hand shows only as a card count. Turns are
**simultaneous**: both players pick a card, and nothing is revealed until
both have committed, at which point the turn resolves for both at once.


## How it works

```
        ┌─────────────┐        ┌─────────────┐
        │  Client A   │        │  Client B   │
        │ (pygame-ce) │        │ (pygame-ce) │
        └──────┬──────┘        └──────┬──────┘
               │  websocket           │  websocket
               └──────────┬───────────┘
                    ┌──────▼──────┐
                    │   Server    │
                    │ (authority) │
                    └─────────────┘
```

The server is the only process that ever holds the full truth (both hands).
Each client receives a **filtered view**: your own hand in full, the
opponent's hand as a count only. This is what makes hidden information
actually secure — a client can't leak what it was never sent.

**Turn flow:**
1. Server deals hands and sends each client its filtered view.
2. You click a card → client sends `play_card` to the server.
3. Server marks you "submitted" and tells your opponent's client that you've
   committed a move (without revealing what it was), so they see something
   happened on their screen.
4. Once **both** players have submitted, the server resolves the turn
   (applies the game rules), updates scores, and sends both clients the
   reveal — what each player played and who won that turn.
5. Repeat until hands are empty; server sends a final `game_over` message
   with the result.

## Project structure

```
PvP/
  shared/
    models.py      # Card + every message type exchanged between client and server (pydantic)
    game_rules.py   # the actual game logic — deck/hand dealing, turn resolution
  server/
    session.py       # one match: holds both hands, tracks submissions, resolves turns
    main.py           # entrypoint — pairs incoming connections, starts sessions
  client/
    network.py        # websocket connection + background receive loop
    ui/render.py       # pygame drawing: hands, cards, status, reveals, game-over screen
    main.py             # entrypoint — pygame window + game loop + input handling
  pyproject.toml   # dependencies: pygame-ce, websockets, pydantic
  .venv/            # local Python virtual environment (not committed)
```

### Why each piece exists

- **`shared/`** exists so client and server agree on the exact same message
  shapes — if you add a new message type, you define it once here and both
  sides import it.
- **`server/session.py`** is the only place both hands ever exist together.
  It refuses to resolve a turn until both players have submitted, which is
  what enforces "simultaneous" turns instead of one player being able to
  react to the other.
- **`client/ui/render.py`** is deliberately just drawing — it takes a
  `ClientState` snapshot and paints it. No network or game logic lives here,
  so you can change how the board looks without touching how the game works.
- **`client/network.py`** keeps networking off the render loop's back: it
  just drops incoming messages into a queue that `client/main.py` drains
  once per frame, so a slow network never freezes the window.

## Running it locally

Two players on the same machine, for testing:

```
# Terminal 1 — start the server
.venv\Scripts\python.exe -m server.main

# Terminal 2 — first player's window
.venv\Scripts\python.exe -m client.main

# Terminal 3 — second player's window
.venv\Scripts\python.exe -m client.main
```

Both client windows connect to `ws://localhost:8765` by default. Click a
card in your hand to play it; you'll see "Waiting for opponent..." until
both players commit, then both windows reveal the result together.

## Running it over the internet

The server needs to be reachable by both players, so it has to run
somewhere both can connect to (a VPS, Fly.io, Railway, etc. — see the
project plan for details), not on either player's own machine (unless you
port-forward). Once deployed:

```
.venv\Scripts\python.exe -m client.main ws://<server-address>:8765
```

Each client takes the server URI as an optional first argument.

## Replacing the game rules

`shared/game_rules.py` is the only file that knows the actual rules of the
game (what cards exist, what a turn resolution means, when the game ends).
Everything else — networking, hidden-info filtering, simultaneous
resolution — is generic and shouldn't need to change. To build your real
game:

1. Replace `deal_hand` with your actual card pool and dealing logic.
2. Replace `resolve_turn` with your actual resolution rules (may need more
   than two cards' values compared — extend `shared/models.py`'s `Card` and
   `PlayCardAction` if a "play" becomes more than a single card ID).
3. `server/session.py` calls into this module — update it if a turn starts
   needing more state than "one card ID per player" (e.g. targeting,
   multiple cards per turn, mana/resource costs).

## Known gaps (v1)

- No reconnect handling — if a client disconnects mid-game, the match is
  effectively stuck. Fine for early development, worth fixing before real
  use.
- No matchmaking beyond "first two connections get paired" — no lobbies,
  no rematch, no player identity/accounts.

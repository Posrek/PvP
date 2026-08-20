"""
from __future__ import annotations

Stores every type annotation in a file as a raw string instead of evaluating
it at definition time. Enables forward references and skips the runtime
cost of evaluating annotation expressions.
"""

## Why it's needed — forward reference example

```python
class Foo:
    def bar(self) -> Foo:  # Foo doesn't exist yet while this line is compiling
        ...
```

- **Without** `from __future__ import annotations`: raises `NameError: name 'Foo' is not defined`.
  The annotation `-> Foo` is evaluated immediately, but `Foo` itself is still
  being defined (its class body hasn't finished executing), so the name
  doesn't exist yet.
- **With** the import: no error. `-> Foo` is stored as the literal string
  `"Foo"` and never evaluated unless something later calls
  `typing.get_type_hints()`.

## Performance note

Not a Big-O / algorithmic win — annotation evaluation is O(1) per annotation
either way, it doesn't scale with input size. The saving is a constant-factor
one: skips the actual evaluation work (name lookups, `__getitem__` calls for
things like `list[Card]`) for every annotation, every time the module loads,
for annotations that in most programs are never even read at runtime.

# `typing` module

Standard library module (`typing.py`) providing type-hint constructs. On
their own, these do nothing at runtime — plain Python never checks
annotations. It's tools like pydantic that read them and enforce anything.

## `Optional`

**The one-sentence answer:** `Optional[str]` tells pydantic (not Python) two
things about a field: "this value is allowed to be `None`, in addition to
being a `str`." Nothing more. It's a declaration read by pydantic's
validation logic — it doesn't add any new syntax or capability to Python
itself.

## `Literal`

<!-- TODO: add later -->

# `asyncio`

## TL;DR

Standard library module for running many I/O-bound tasks concurrently on a
**single thread**, using an event loop instead of OS threads/processes.
Coroutines (`async def`) voluntarily yield control at each `await`, so
waiting on a socket/file/timer never blocks other tasks — cheaper than
threads (no OS thread overhead, no GIL contention) and simpler than
processes (no IPC needed, shared memory by default).

**Core pieces used in this project** ([server/main.py](../server/main.py)):
- `asyncio.run(main())` — creates the event loop, runs one coroutine to
  completion, tears the loop down. The single entry point.
- `async def` / `await` — defines a suspendable coroutine / suspends at an
  I/O point, handing control back to the loop.
- `asyncio.Lock()` — mutex for coroutines, used with `async with` to protect
  shared state (`_waiting`) from being read/written by two coroutines
  interleaved at the same `await` point.
- `asyncio.Future` — a one-shot mailbox: one coroutine `await`s it (suspends
  until filled), another coroutine calls `.set_result(...)` on it (fills it,
  waking the first). Used to hand a freshly created `GameSession` from the
  second matched player's coroutine to the first (waiting) player's
  coroutine, without polling.

**Not real parallelism** — CPU-bound work still blocks the single thread.
Only useful for I/O-bound concurrency (network, disk, timers).

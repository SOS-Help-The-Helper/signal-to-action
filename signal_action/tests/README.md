# Tests — signal_action.capture + signal_action.provenance

Synthetic fixtures only. No real PII, no secrets, no live capture, no DB touches.

## Running

From the distill root:

```
python3 -m signal_action.tests.test_end_to_end
python3 -m signal_action.tests.test_reasoning_stream
python3 -m signal_action.tests.test_retrieval
python3 -m signal_action.tests.test_loops
```

(`python3 -m` — not `python3 path/to/test.py` — so the `signal_action`
package resolves without any `sys.path` hacks.)

## The key-literal rule (why fixtures look odd)

The environment's file-write pipeline **redacts key literals on sight**
(anything shaped like `sk-...`, `ghp_...`, `AKIA...`, `xai-...`, `sk-ant-...`,
`xox[baprs]-...`, `sk_live_...`, JWTs). That is the correct safety behavior —
but it means key-shaped secrets must never be written literally into
fixtures or source files, or they vanish from the test corpus silently.

So this suite splits key testing in two, exactly as the lab tests do:

1. **Fixtures** carry `<redacted>` placeholders where a key-shaped value
   would sit in context (e.g. `"key": "<redacted>"`). Placeholders verify
   the parsing path (tool_use collapse, no raw input leakage) without ever
   containing a key shape.
2. **Tests build real key shapes at runtime** via the `_mk(prefix, body)`
   helper (e.g. `_mk("sk-", "TestKeyAbc123Def456Ghi789jkl")`) and probe the
   scrubber + `assert_clean` with them inside realistic sentences.

Coverage is NOT lost: every key shape the scrubber handles (`RUNTIME_SECRETS`
in `test_end_to_end.py`, plus a runtime-built key inside a thinking block in
`test_reasoning_stream.py::test_runtime_key_in_thinking`) is exercised with a
genuinely shaped value. `assert_clean` is additionally run against the
standalone shapes, since shape-based leaks need no context.

**Rule for future edits:** never paste a literal key-shaped string into a
fixture or a `.py` file in this package. Build it with `_mk` at runtime.
If the write pipeline eats something you wrote, assume it was a key shape
and rebuild the test accordingly — do not weaken the assertion.

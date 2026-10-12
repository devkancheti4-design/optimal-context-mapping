# PROTOCOL_VALUE8: does the kit author the fix's location? (fixed before any request)

The user's claim: for any novel question, the kit, given just the right data, decides the fix, and the model only
writes it. Testable form: on a bug the kit has never seen, with no teaching, the kit's readout alone is enough for
Claude to write a passing fix in one pass, with no search.

**Data:** PROTOCOL_VALUE5's 19 evaluable django issues (value/w_eval.json), the same checkouts at each base commit,
and the same scoring by Django's own tests.

**The kit's readout:** from a fresh copy of swe/ws_base (the 4a72da7 snapshot, nothing taught), for the issue text,
through `ocm.loop.readout` (the first readout, plus the next when the first is the taught lane). Learning is off: every
bug stays novel.

**Arms:** the model gets the issue, the readout and three tools:
- `read_file`, restricted to the files the readout names, read from the issue's base checkout;
- `edit_file` (exact unique replacement);
- `finish`.

There is no search and no file listing, at most 8 tool calls, and `max_tokens` 16000.
- KH: claude-haiku-5-5.
- KS: claude-sonnet-5-5.

**Baseline:** V5's ALONE (claude-sonnet-5-5 exploring with search, read, list and edit): 16 of 19 resolved,
$0.197 per resolved issue.

**Predictions (the user's claim)**
- A1: KS resolves at least ALONE's count less 2 (≥ 14 of 19).
- A2: KS's cost per resolved issue is at least 2x lower than ALONE's.
- A3: KH resolves at least ALONE's count less 4 (≥ 12 of 19).
- A4: KH's cost per resolved issue is at least 10x lower than ALONE's.

Also reported: how often a file the readout named is the file the official fix changed (the kit's location hit rate).

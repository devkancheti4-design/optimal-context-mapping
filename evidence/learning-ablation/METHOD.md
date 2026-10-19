# The learned law, forced on (written 2026-10-19, before any readout; an exploratory ablation prompted by review)

**The question:** how much does the learned law itself contribute, as opposed to taught pointers in the vector law?
During the Django team year its prequential gate never let it on.

**A. Coverage workspace** (`vs-graphify/ws/dj_cover`: 23,770 taught questions; the gate let the law on):
- The 288 Django 2022 questions, query `q`, code scope, are read twice: with the learned law as it is (on), and
  forced off.

**B. The team year, replayed offline:**
- Start from `team-year/ws/base` (cold). Take the 288 kept fixes in commit order.
- For each fix: read its question first, then teach the line its real Sonnet exploration submitted (`rows_md.jsonl`,
  `where`, on the teach path), exactly as the product did.
- Two arms, identical teaching:
  - **gate:** the law as shipped (it switches on only when it wins prequentially);
  - **forced on:** the law in use whenever the search has found any non-trivial law.

**Measures:**
- right file first, and right file in the top 5 (the readout's files; gold is the fix's files);
- the readouts the learned law reordered.
- Exact McNemar on paired right-first.

No model calls.

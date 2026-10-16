# A team's year, arm three: Model D with the relation gate on learned-first answers (written 2026-10-16, before any gated call)

## Why
The ten-year replay and the first 30 questions of PROTOCOL_TEAM_YEAR show the same limit. As novelty falls, the learned
shortcut fires more often, but its first pick is often wrong, and the strict reader then answers from the wrong code
instead of falling back. The relation gate (Plane and SigNoz study, RELATION_RESULTS.md) lets learned code go first only
when the nearest taught question explains the new one better than any code text does, by at least one sd of chance
agreement (37 bits). There it kept 85–86% of learned-first answers right.

## Arm
**Model D, gated.** Everything as the Model D arm of PROTOCOL_TEAM_YEAR: same stream, questions, snapshot, product loop,
models, code scope and caps. The one difference is the workspace server, which runs `optimal-context-mapping` at
`relation-limit` (5c3d911, which is main plus that one commit) with `ocm.router.lanes.CERT_MIN_OVER_OWN = 37`.
- Its own copy of the cold snapshot workspace, sequential, learning only from its own explorations.
- Cap $10.

## Predictions (fixed now), against the ungated Model D arm and the alone arm of PROTOCOL_TEAM_YEAR
- **G1, precision:** the share of read-path answers that are right is higher gated than ungated.
- **G2, the work:** gated right count ≥ alone right count − 3% of questions.
- **G3, the bill:** gated total ≤ alone total / 1.5.
- **G4, the price of safety:** gated total ≤ ungated total × 1.25.

The same analysis applies (`scripts/analyse.py`, with the gated rows in place of the Model D rows). Every number is
reported.

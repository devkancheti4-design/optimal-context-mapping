# PROTOCOL_VALUE6b: the warm kit with the strict reader (fixed before any request; V6's failures stand)

V6 taught the kit Django's pre-2019 fix history. The read path then fired 9x more often (18 per run against 2), but
only 14 of 36 reads were right, and accuracy fell by 11. V7 found that a strict reader prompt, which says NEED_SEARCH
unless the code covers the whole question, restores accuracy. This tests the two together.

**Setup**
- Workspace: value/ws_warm_base (V6's warm workspace), a fresh copy per run, learning on.
- Data: E1's 114 reports, in order. Two runs.
- MODEL D as in V7's variant S: claude-haiku-5-5 with the STRICT prompt for reads, and the shipped teach step on
  claude-sonnet-5-5.
- Baselines: V6's ALONE and cold MODEL D (E1, F1 runs 2 and 3), with V6's statistics.

**Predictions**
- K5: right per run within 5 of ALONE's.
- K6: cost saving against ALONE of at least 1.4x.
- K7: cheaper per bug than cold MODEL D (point estimate below cold's).

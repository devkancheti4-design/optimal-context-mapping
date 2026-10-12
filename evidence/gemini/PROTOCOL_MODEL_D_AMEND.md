# Amendment to PROTOCOL_MODEL_D.md: the kit takes every decision

Written after the user's direction that in Model D the core decisions are the kit's and the LLM only perceives and acts.
Disclosure: the reference fixes (QuixBugs correct_python_programs) for the six programs neo4d found were viewed before
this amendment was written.

- **AMBIGUOUS bugs.** The brain picks, not the eyes. The rule is the first verified candidate in neo4d's own order: the
  shipped fix classes before the self-mutation neurons, then by line. The pick is applied with 0 model calls and checked
  by the program's tests. The eyes-pick runs stay as a comparison.
- **Questions.** Unchanged. The brain chooses the code (the taught lane's readout). The eyes only read it and phrase the
  answer; NEED_SEARCH is the eyes reporting that the answer is not visible, and the brain then sends the task to the body.
- **Added measure D5:** the brain's picks on REPAIRED and AMBIGUOUS bugs pass the tests with 0 model calls, and each
  matches the reference fix's behaviour (exact edit, or an equivalent one).

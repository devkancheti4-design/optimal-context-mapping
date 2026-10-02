## Team workspace (add this to CLAUDE.md or your agent's rules)

This team shares a workspace memory over our code and docs, with notes teammates taught. Use it like this:

1. Before searching the code for something, call `workspace_ask` with the question in plain words. If the readout
   answers it, answer from it; no search needed. If not, try `workspace_next` once, then search as usual.
2. Keep a short note for every question you answered: the answer in one to three sentences and where it is (files and
   lines).
3. At the END of your work, call `workspace_teach` ONCE with all your notes (one item per question). Do not teach note
   by note: one call for everything keeps the cost down.

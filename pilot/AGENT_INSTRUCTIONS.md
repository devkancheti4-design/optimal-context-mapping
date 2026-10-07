## Team workspace (add this to CLAUDE.md or your agent's rules)

This team shares a workspace over our code and docs: vectors and laws that rank the code for a question, and that
learn from the questions teammates answered. Use it like this:

1. Before searching the code for something, call `workspace_ask` with the question in plain words. If the readout
   answers it, answer from it; no search needed. If not, try `workspace_next` once, then search as usual.
2. For every question you answered, keep the line its answer is on, as path:line.
3. At the END of your work, call `workspace_teach` ONCE with every question and its path:line. Do not teach one at a
   time: one call for everything keeps the cost down.

With the Claude Code hooks (README, step 4) there is nothing to call: the readout comes with each request, and the
reply's `TEACH: <question> | <path>:<line>` lines are taught for you.

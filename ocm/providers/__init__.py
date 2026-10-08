"""Model adapters for the hybrid (ocm/hybrid.py). Each has read(system, question, code) -> text and
teach(system, question, code, tools, run_tool, max_calls) -> (answer, path:line, requests)."""

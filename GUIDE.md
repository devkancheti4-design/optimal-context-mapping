# Using Model D well

Everything here comes from a measured test (the evidence is in `evidence/`), including the settings that did not pay.

## 1. One workspace for the whole team
The saving comes from not paying twice for the same search. One engineer's exploration teaches the workspace, and the
next engineer's agent reads what was learned. With a workspace per laptop, each person only saves on their own repeats.
- Run one server (`docker compose up -d` or `modeld serve`, DEPLOY.md).
- Point every engineer at it: `modeld install --team http://<server>:7700`.

## 2. Put it in the loop, not in the toolbox
Model D decides where to look before the model runs. Offered as a tool the agent may call, it cost more requests than
it saved, because the agent called it and then searched anyway.

Use the hooks (`modeld init all`) or the hybrid (`modeld hybrid`). Both hand the readout in with the request.

## 3. Code scope for code questions
For bug reports, stack traces and "where is X" questions, use `--scope code` (or `OCM_SCOPE=code` on the server).
- In full repositories, documentation filled about half the top five.
- With code scope, the fixed file was in the top five for 176 of 285 issues, against 117 without.

## 4. Clear the session between tasks
In one long session, every readout stays in the transcript, so billed input grows. Clearing between tasks kept the
saving steady (1.26x and 1.24x across the halves of 100 questions). The workspace keeps what was learned, so nothing is
lost.

## 5. Rebuild with the cache
After large code changes:

```bash
modeld build . --out modeld-out --cache ~/.cache/modeld/embed.sqlite
```

The rebuild carries every lesson, and re-finds its line even after the code moves (38 of 38 across 400 commits). With
`--cache`, it embeds only the code that changed, and gives the same workspace bit for bit.

## 5b. Teach it the whole codebase once
`modeld cover` has Claude Haiku write one question for each piece of non-test code and teaches each as a pointer to
that code. It costs about $1 for 24k pieces. It helps from day one, before the team has asked anything: on Django the
right file came first 28% more often. Run it again after a rebuild, and it writes questions only for new or changed
code.

## 6. When a wrong answer costs more than a search
By default, learned code goes first whenever the router law trusts it, which is the cheapest policy. If your team would
rather pay a little more for fewer wrong first picks, set:

```bash
OCM_CERT_MIN_OVER_OWN=37 modeld serve /srv/modeld
```

Learned code then goes first only when the nearest taught question explains the new one better than any code does, by
one standard deviation of chance agreement (37 bits).

## 7. Where it pays, and where it does not

| work | saving vs the agent alone |
|---|---|
| a team asking about the same codebase: onboarding, support, Q&A, research | 2.3–2.8x; 5–10x on repeats |
| a team's real stream of fixes on one codebase | see `evidence/team-year` |
| brand-new, scattered bugs | about 1.35x |
| code review | small: reviewers barely search |
| writing fixes | not proven cheaper |

The more your team works the same code, the more it saves. The learning law, S = A / ((1 − ν)·E + ν·K), says by how
much:
- ν: the share of questions that are new;
- E: a learned read, about $0.0005;
- K: a first exploration with the kit's readout;
- A: the agent alone.

## 8. Measure it on your own bill
Claude Code keeps a transcript per session under `~/.claude/projects/<project>/`. Run a week without Model D and a week
with it, then:

```bash
modeld measure compare <transcripts, week without> <transcripts, week with>
```

It prints requests, billed input (cache-weighted, as the API prices it) and tool calls per session for both, with their
ratios. Nothing is sent anywhere. That is the number that matters for your team.

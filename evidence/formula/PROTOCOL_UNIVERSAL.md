# Protocol: one universal formula for the saving, built from what was observed, tested out of sample

Fixed before any prediction is computed; its SHA-256 goes in prereg_hashes.json. The formula's structure was derived from
the observations listed below (PROTOCOL_FORMULA.md and its results). This protocol tests it in two ways:
- **Leave-one-out:** every constant is fitted without the case being predicted.
- **Prospectively:** on two models the formula has never seen, predicted before their kit runs exist.

## The universal formula (UF)

**The agent alone works a session of q questions in r_a turns.** Each turn re-sends the whole context. Turn j processes
P + g·(j − 1) tokens:
- P is the fixed prompt: harness, tools and question;
- g is what each turn adds.

So a session costs

    T(r, P) = r·P + g·r·(r − 1)/2

**The laws make the search decisions in bits.** They remove a share φ of the agent's search turns, the turns beyond the
one answering turn per question, and add the readout to the prompt:

    r_K = q + (1 − φ)·(r_a − q)
    P_K = P_a + Δ·(q + 1)/2        (Δ = tokens of the kit text per question; with q questions, on average half of the
                                     readouts are already in the context)
    K   = T(r_K, P_K)               (g unchanged: the agent's own steps add the same per turn)

**Learning: the hybrid (Model D).** A share 1 − ν of the questions is answered by one cheap read E (the taught lane). The
rest go to the laws plus the agent: a K session with q = 1. If the cheap read first declines, that question costs E + K₁.

    cost per question = (1 − ν)·E + ν·K₁   (plus E for each question the cheap read passed on)

**The saving:**

    S = A / cost,    A = what the agent alone spends

**Limits that follow:**
- With a heavy fixed prompt (P ≫ g·r), S → r_a / r_K: the turn saving.
- With a lean prompt (g·r ≫ P), S → (r_a / r_K)²: every skipped turn also saves all the re-sending after it.
- As ν → 0, S → A / E.

## Inputs, by source
- **From the agent alone (a company's current logs):** r_a, P_a, g (the within-session slope of tokens on turn index), A,
  q.
- **From the kit and the model's tokenizer (offline):**
  - Δ: the first-turn prompt difference between kit and alone in a single-question case of the same model family. For
    Claude this is C1 (Sonnet), for Gemini C2 (Flash). It is scaled to each case by mean readout characters.
  - ν and the paths: the kit's routing per question.
- **Behavioural constants, always fitted leaving the predicted case out:**
  - φ: the mean over laws cases of (r_a − r_K)/(r_a − q), measured. For the hybrid cases, C3 is excluded, since it
    shares their ALONE runs.
  - E: the mean tokens of one cheap-read call in the other hybrid runs.

## Cases (all existing; observables in universal/cases.json)
- **Laws:**
  - C1: Sonnet 5.5, 114 real bugs.
  - C2: Gemini 2.5 Flash, the same bugs.
  - C3: Gemini 2.5 Flash, 60-question stream (3 runs × 6 sessions of 10).
  - C4: Opus 5.5, 60-question stream.
  - C5: Sonnet 5.5, 60-question stream.
- **Hybrid end to end:** C6–C8, Gemini 2.5 Flash, runs 1–3, 60 questions each.

## Measures
- **Per case:** S_pred and S_meas, in tokens. Laws cases: A = mean ALONE tokens per session, against mean KIT tokens per
  session. Hybrid cases: per question, against Model D's tokens per question.
- **Error:** S_pred / S_meas − 1.
- **Baselines**, also leave-one-out:
  - B1: S = the mean S_meas of the other cases of the same kind.
  - B2 (laws cases): S = 1/(1 − φ), the turn intuition with no token structure.
- **Comparison score:** mean |log(S_pred / S_meas)|.

## Predictions
- **U1.** UF is within ±25% of the measured saving on every one of the 8 cases (leave-one-out).
- **U2.** UF's mean |log error| is lower than both B1's and B2's.
- **U3 (prospective).** Claude Haiku 5.5 and Claude Opus 5.5 are new to this test, as agents on the 114 real bugs.
  - **Order:** each model's ALONE arm runs first. UF's predicted KIT saving is then computed from its ALONE profile, with
    φ from C1–C5 and Δ from C1, and its hash is written to prereg_hashes.json. Only then does the KIT arm run.
  - **Runs:** both arms run as workflow subagents with the same prompt; requests are API-equivalent as in
    PROTOCOL_SWE_SONNET.md.
  - **Prediction:** the measured token saving is within ±25% of the prediction, for both models.

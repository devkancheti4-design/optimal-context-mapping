# SWR-Bench, the learning test: does Model D's review bill fall as it learns a codebase? (written 2026-10-16, before any stream readout or review)

## The claim (from the Model D site)
"When something is new, the place it was found is learned, so the next engineer's question costs less." And: "the saving
grew as the team taught it." Here the team's knowledge is where its reviewers flagged problems on earlier PRs.

## Stream
- **PRs:** scikit-learn's newest 100 SWR-Bench PRs, from 2021-12-01 to 2025-04-15 (64 with issues, 36 clean), in
  creation order. Each PR is reviewed at its own `base_commit`.
- **Lessons:** every inline review comment (timeline events of type `review_comment` that are not replies), from all 255
  scikit-learn PRs in the benchmark:
  - question: "<that PR's title>: <the comment, first 200 characters>";
  - place: the commented line, the last line of the comment's `diff_hunk` (a deleted line or an empty line gives no
    lesson).
- **For PR k,** the lessons taught are only those whose comment was written before PR k was created, and never from PR k
  itself. PR k's own review is its ground truth and is never taught.

## Per PR (`scripts/prep_stream.py`)
1. Leak check as in the pilot: none of the PR's commits, or introducing or resolving commits, is an ancestor of
   `base_commit`.
2. Model D workspace at `base_commit`: Model D's own build, behind the embedding cache.
3. **Cold readout:** Model D's served readout, code scope, for the PR's title then description cut to 400 characters.
4. **Teach:** every allowed lesson goes through the workspace's own `teach`, at the first line in the commented file
   (matched by path tail) whose stripped text equals the commented line. A lesson whose line no longer exists is not
   placed, and the count is reported.

   This re-teaches the accumulated lessons into each fresh build. It has the same effect as the product's carry across
   rebuilds (Life re-found by line text), done explicitly.
5. **Learned readout:** the same question, on the taught workspace, read fresh from disk.

## Arms (the agent of PROTOCOL_SWR_AGENTIC.md, unchanged: Sonnet 5.5, Model D's tools, 15 calls, caching)
- **C-s:** agent alone.
- **D-cold:** agent plus the cold readout.
- **D-learn:** agent plus the learned readout.

Judged by Claude Haiku 5.5 (`judge_claude.py`), as all other arms.

## Predictions (fixed now)
- **L1, learning lowers the bill:** dollars per PR, D-learn ≤ D-cold over the stream. The gap is larger on the newer
  half (PRs 51–100) than on the older half.
- **L2, quality holds:** F1(D-learn) ≥ F1(D-cold) − 0.02.
- **L3, learned ground grows:** the share of PRs whose learned readout is led by taught code is higher in the newer half
  than in the older half.
- **L4, against the agent alone:** dollars per PR, D-learn ≤ C-s / 1.25, with F1(D-learn) ≥ F1(C-s) − 0.02.

## Caps and reporting
- Caps: C-s $7, D-cold $6, D-learn $6, judge $1.
- Reported:
  - lessons available, placed and not placed per PR;
  - every number, whichever way it comes out, with deviations listed below.

## Deviations
(none yet)

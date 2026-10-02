"""THE CMLM ROUTER LAW -- Python equivalent of router.c, same authored lanes.

THRESHOLDS (part of the law, chosen once from the geometry, never swept):
  TAU = 8 bits    one tripling's worth of crowding; a smaller lead is noise
  NEAR = 8, C = 3 sentences within NEAR of the best
  GAP = 74 bits   2 sd of the chance distribution (sd = 37, measured)
  DELTA = 8       the taught cue's required lead, same unit as TAU
  THETA           the IDF cut for RARE, set so RARE fires on ~44% of questions
  KEYHIT margin   the keyword top must lead its second by TAU
"""
TAU = NEAR = DELTA = 8; C = 3; GAP = 74
LANES = ['CERTIFIED', 'MEANING', 'KEYWORD', 'MIX', 'WIDE', 'DIG']

# ---- the sphere-authored lanes, verbatim -----------------------------------
SIG        = lambda a, b: a + 2 * b
SIG_AND    = lambda s: (s & (s >> 1))
SIG_ANDNOT = lambda s: ((s & 1) - (s & (s >> 1)))
SIG_OR     = lambda s: ((s - (s >> 1)) - (s & (s >> 1)))
NOT1       = lambda b: (1 - b)
L_LANE_OF  = lambda x: (((x + 5) >> 2) ^ (x | ((x + 7) >> 2)))
L_CERT     = lambda x: (x & 1)
L_CLEAR    = lambda x: (1 & (x >> 1))
L_CROWDED  = lambda x: (1 & (x >> 2))
L_FLAT     = lambda x: (1 & (x >> 3))
L_RARE     = lambda x: (1 & (x >> 4))
L_KEYHIT   = lambda x: (1 & (x >> 5))
L_AGREE    = lambda x: (1 & (x >> 6))
L_TRIED    = lambda x: (x >> 7)
DIGSLOT    = 32

def observe(cert_lead, top_lead, n_near, best_minus_med, idf, key_lead, shared, tried):
    """the eight bits, all measurable for free before Claude is called"""
    return ((1 if cert_lead >= DELTA else 0)
          | (1 if top_lead  >= TAU   else 0) << 1
          | (1 if n_near    >= C     else 0) << 2
          | (1 if best_minus_med <= GAP else 0) << 3
          | (1 if idf >= observe.THETA  else 0) << 4
          | (1 if key_lead >= TAU    else 0) << 5
          | (1 if shared             else 0) << 6
          | (1 if tried              else 0) << 7)
observe.THETA = 6.0

def router_mask(obs):
    x = obs & 0xFF
    p0 = L_CERT(x)
    p1 = L_KEYHIT(x)
    p2 = 1                                                   # MIX, the workhorse
    p3 = SIG_ANDNOT(SIG(L_CLEAR(x), L_CROWDED(x)))           # MEANING
    p4 = SIG_OR(SIG(L_CROWDED(x), NOT1(L_CLEAR(x))))         # WIDE
    return p0 | (p1 << 1) | (p2 << 2) | (p3 << 3) | (p4 << 4) | DIGSLOT

def emit(obs, live=63):
    """returns (slot, lane) -- the lowest live priority and the lane it names"""
    m = router_mask(obs) & live
    if not m: return 5, 5
    slot = (m & -m).bit_length() - 1
    return slot, L_LANE_OF(slot)

def advance(live, slot):
    """clears the slot just served.  Strictly reduces `live`, so the loop ends."""
    return live & ~(1 << slot)

def route(observe_fn, judge_fn):
    """measure -> EMIT -> readout -> judge -> HALT or ADVANCE.  Unchanged."""
    live, served = 63, []
    tried = False
    while True:
        obs = observe_fn(tried)
        slot, lane = emit(obs, live)
        served.append(lane)
        if lane == 5: return served, 'DIG'
        if judge_fn(lane): return served, 'HALT'
        tried = True
        live = advance(live, slot)

if __name__ == '__main__':
    # the same exhaustive checks as router.c
    bad = reduce_bad = repeat = notdig = 0
    for x in range(256):
        live, seen, rounds, last = 63, 0, 0, -1
        while True:
            slot, lane = emit(x, live)
            nl = advance(live, slot)
            if nl >= live: reduce_bad += 1
            if seen & (1 << lane): repeat += 1
            seen |= 1 << lane; live = nl; rounds += 1; last = lane
            if lane == 5 or rounds > 8: break
        if last != 5: notdig += 1
    print('  256 states: ADVANCE always shrinks %s   no lane twice %s   all reach DIG %s'
          % (reduce_bad == 0, repeat == 0, notdig == 0))
    from collections import Counter
    print('  first readout: %s'
          % {LANES[k]: v for k, v in sorted(Counter(emit(x)[1] for x in range(256)).items())})

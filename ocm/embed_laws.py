"""THE EMBEDDING LAW's integer laws, verbatim: machine-authored by integer program synthesis, each found by a fresh,
live search (checked strictly alive) and proven on every input of its domain against the derivation (3 translation
units, -O3 and -O1, -fwrapv, a volatile sink). Python is the exact int32 meaning of the C expression.

  SEL(d)    the quantile rule: d when |d| > 4 bits, else 0.            proven on d in [-1024, 1024]
  CGAP(s)   the certifier's gap, never derived, in sigma0 units: round(41 s / 37).   proven on s in [0, 511]
  CNEAR(s)  the certifier's near, likewise: round(10 s / 37).                      proven on s in [0, 511]
  RLIM(x)   RELATION_LIMIT, whole: x = s | a84 << 10. sigma0, or the 84.13% lift when it departs by more than 4 bits.
  GAPW(x)   GAP, whole: x = s2 | a98 << 10. 2 sigma0, or the 97.72% lift likewise. Two fresh searches returned the same
            expression: one rule at k = 1 and k = 2. Both proven on all 2^20 packed inputs (and on all 2^32 int32).
  TAUW(x)   TAU = NEAR = DELTA, whole: x = a98 | N << 10, N in [30, 2^21). Built on the declared collection-size table
            XF(N) = round(2^21 (sqrt(2 ln N) - sqrt(2 ln N/3))), the one non-integer piece (float64, rounded once).
            Proven on all 2,147,452,928 inputs against (a98 XF(N) + 2^21) >> 22, in 64-bit arithmetic. Without the
            table, a search over the integers (the N field, an exact integer square root, the multiply, the scale) found
            nothing up to size 5. It equals the float formula round((lift98 / 2)(sqrt(2 ln N) - sqrt(2 ln N/3))) on all
            but 65,589 inputs of the domain (0.003%), each one bit off at a near-tie within 0.00012 of a half; and it
            reads round(lift98), as GAP does, where the float formula read lift98 itself.

C, as authored:
  SEL    ((x & ((x + 4) >> 31)) + (x & ((4 - x) >> 31)))
  CGAP   ((1990 + ((int)((unsigned)(x) * (unsigned)(4539)))) >> (12 & 31))
  CNEAR  ((2006 + ((int)((unsigned)(x) * (unsigned)(1107)))) >> (12 & 31))
  RLIM, GAPW (the same expression)
         ((x & 1023) - ((((x & 1023) - ((x >> 10) & 1023)) & ((((x & 1023) - ((x >> 10) & 1023)) + 4) >> 31))
                        + (((x & 1023) - ((x >> 10) & 1023)) & ((4 - (((x & 1023) - ((x >> 10) & 1023)))) >> 31))))
  TAUW   ((2097152 + ((int)((unsigned)((x & 1023)) * (unsigned)(XFN(x))))) >> 22)
         XFN(x) = ((x >> 10) >= 30 ? (int)floor(2097152.0 * (sqrt(2.0 * log((double)(x >> 10)))
                                                - sqrt(2.0 * log((double)(x >> 10) / 3.0))) + 0.5) : 0)"""
import math


def s32(v):
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v


def SEL(x):
    assert -1024 <= x <= 1024, x
    return s32(s32(x & (s32(x + 4) >> 31)) + s32(x & (s32(4 - x) >> 31)))


def CGAP(x):
    assert 0 <= x <= 511, x
    return s32(1990 + s32(x * 4539)) >> 12


def CNEAR(x):
    assert 0 <= x <= 511, x
    return s32(2006 + s32(x * 1107)) >> 12


# RLIM and GAPW: on [0, 2^20) every intermediate value lies in [-2047, 2047], where Python's ints are int32's.
def RLIM(x):
    assert 0 <= x < 1 << 20, x
    return ((x & 1023) - ((((x & 1023) - ((x >> 10) & 1023)) & ((((x & 1023) - ((x >> 10) & 1023)) + 4) >> 31))
                          + (((x & 1023) - ((x >> 10) & 1023)) & ((4 - (((x & 1023) - ((x >> 10) & 1023)))) >> 31))))


def GAPW(x):
    assert 0 <= x < 1 << 20, x
    return ((x & 1023) - ((((x & 1023) - ((x >> 10) & 1023)) & ((((x & 1023) - ((x >> 10) & 1023)) + 4) >> 31))
                          + (((x & 1023) - ((x >> 10) & 1023)) & ((4 - (((x & 1023) - ((x >> 10) & 1023)))) >> 31))))


def XF(n):
    """The declared collection-size table: round(2^21 (sqrt(2 ln N) - sqrt(2 ln N/3))). The same libm log as the C body
    (checked equal on every N of the domain)."""
    assert 30 <= n < 1 << 21, n
    return math.floor(2097152.0 * (math.sqrt(2.0 * math.log(n)) - math.sqrt(2.0 * math.log(n / 3.0))) + 0.5)


def TAUW(x):
    assert 30 << 10 <= x < 1 << 31, x
    return s32(2097152 + s32((x & 1023) * XF(x >> 10))) >> 22

"""Universal Q/B -> physical-check penalty for all Beings (Encounters candidate).

A fixed game-mechanical rule. This normalization is *not* an inference of the
Being's physiology and must never be used for effort feasibility or Q/B updates.
"""
from math import floor

CHECK_SENSITIVITY = 5       # Rules constant; not a tunable simulation parameter
REFERENCE_C0 = 0.60      # Standard reference curve, not a Being attribute
REFERENCE_FC = 0.25
REFERENCE_FP = 0.55
REFERENCE_N = 2.0

def standard_output(q, b):
    """Reference fraction of fresh peak output from Q/B in [0, 1]."""
    if not 0 <= q <= 1 or not 0 <= b <= 1:
        raise ValueError('Q and B must be fractions in [0,1]')
    c = REFERENCE_C0 * (REFERENCE_FC + (1 - REFERENCE_FC) * b)
    h = 1 - (1 - REFERENCE_FP) * (1 - b)
    return c + (h - c) * (1 - (1 - q) ** REFERENCE_N)

def physical_check_penalty(q, b):
    """Nonnegative penalty magnitude; apply once to every physical check."""
    return max(0, floor(CHECK_SENSITIVITY * (1 - standard_output(q,b)) + .5 + 1e-12))

def penalty_table(bands=tuple(range(100,-1,-10))):
    return [[physical_check_penalty(q/100,b/100) for b in bands] for q in bands]

def markdown_table():
    bands=list(range(100,-1,-10)); lines=['| Q% / B% | '+' | '.join(map(str,bands))+' |',
            '|'+ '---:|'*(len(bands)+1)]
    for q,penalties in zip(bands,penalty_table(bands)):
        lines.append('| '+str(q)+' | '+' | '.join('−'+str(p) if p else '0' for p in penalties)+' |')
    return '\n'.join(lines)

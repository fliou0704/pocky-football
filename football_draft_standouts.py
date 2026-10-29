"""Round-only draft standouts: relative draft-slot gain and positional excellence.

No weighted composite and no cross-position FPTS comparison. Existing player
metrics, FPTS round rankings, manager aggregates and Summary are not modified.
"""
from fractions import Fraction


def round_standouts(picks, finalized):
    if not finalized:
        return {'status': 'provisional', 'valueLeaders': [], 'finishLeaders': [], 'missingBenchmarks': 0}
    if not picks or any(pick.get('points') is None for pick in picks):
        return {'status': 'missing_scores', 'valueLeaders': [], 'finishLeaders': [], 'missingBenchmarks': 0}
    values = [p for p in picks if p.get('draftPositionGain') is not None and p.get('overallPick', 0) > 0]
    finishes = [p for p in picks if p.get('positionalRank') is not None]
    # Exact rational comparison avoids inventing a numerical tie tolerance.
    best_value = max((Fraction(str(p['draftPositionGain'])) / p['overallPick'] for p in values), default=None)
    best_finish = min((p['positionalRank'] for p in finishes), default=None)
    return {
        'status': 'available' if values or finishes else 'missing_ranks',
        'valueLeaders': [p for p in values if Fraction(str(p['draftPositionGain'])) / p['overallPick'] == best_value],
        'finishLeaders': [p for p in finishes if p['positionalRank'] == best_finish],
        'relativeGainPercent': float(best_value * 100) if best_value is not None else None,
        'missingBenchmarks': len(picks) - len(values),
    }


def compare_methods(seasons):
    """Reproducible comparison of raw-gain and relative-gain candidates, all rounds."""
    rows = []
    for season in seasons.values():
        if not season['performanceEligible']:
            continue
        for round_ in season['rounds']:
            picks = round_['picks']
            available = [p for p in picks if p.get('draftPositionGain') is not None]
            raw_best = max((p['draftPositionGain'] for p in available), default=None)
            selected = round_standouts(picks, True)
            rows.append({'season': season['season'], 'round': round_['round'],
                         'rawGainLeaders': [p for p in available if p['draftPositionGain'] == raw_best],
                         **selected})
    return rows

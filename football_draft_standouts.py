"""Round winners maximize positional draft-slot gain; finish recognition is separate."""


def round_standouts(picks, finalized):
    if not finalized:
        return {'status': 'provisional', 'valueLeaders': [], 'finishLeaders': [], 'missingBenchmarks': 0}
    if not picks or all(pick.get('points') is None for pick in picks):
        return {'status': 'missing_scores', 'valueLeaders': [], 'finishLeaders': [], 'missingBenchmarks': 0}
    values = [p for p in picks if p.get('draftPositionGain') is not None and p.get('overallPick', 0) > 0]
    finishes = [p for p in picks if p.get('positionalRank') is not None]
    best_value = max((p['draftPositionGain'] for p in values), default=None)
    best_finish = min((p['positionalRank'] for p in finishes), default=None)
    return {
        'status': 'available' if values or finishes else 'missing_ranks',
        'valueLeaders': [p for p in values if p['draftPositionGain'] == best_value],
        'finishLeaders': [p for p in finishes if p['positionalRank'] == best_finish],
        'relativeGainPercent': None,
        'missingBenchmarks': len(picks) - len(values),
    }


def compare_methods(seasons):
    """Audit round winners against the canonical raw gain, all finalized rounds."""
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

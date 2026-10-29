"""Native calculation kernels shared by live Actions and inactive proposals.

No world access or effects. Callers own the supplied dice/check/save functions.
"""

def attack_hits(roll, attack, defense, difficulty):
    return roll + attack - defense >= difficulty


def saving_throw(roll, difficulty, experience_modifier):
    return roll == 20 or (roll != 1 and roll >= difficulty - experience_modifier)


def hit_outcome(difficulty, roll, hits, target_save, actor_save):
    value = roll('1d20')
    if value == 20:
        confirmation = roll('1d20')
        if confirmation == 20:
            return 'critical' if target_save(difficulty) else 'fatal'
        return 'critical' if hits(confirmation, difficulty) else 'normal'
    if value == 1:
        confirmation = roll('1d20')
        if confirmation == 1:
            return 'hit self'
        if not hits(confirmation, difficulty):
            return 'spectacular miss' if actor_save(difficulty) else 'drop weapon'
        return 'miss'
    return 'normal' if hits(value, difficulty) else 'miss'


def armor_impact(damage, defenses, penetration):
    """Native least-hardness/least-stopping semantics, independently selected."""
    hardness = least_armor_defense(defenses, penetration, 'h')
    stopped = least_armor_defense(defenses, penetration, 'd')
    return max(0, damage - hardness), max(0, damage - stopped)


def shield_impact(damage, size, roll):
    intercepted = roll <= int(size) + 4
    return intercepted, max(0, damage - int(size)) if intercepted else damage


def check_succeeds(roll, rank, difficulty):
    return roll == 20 or (roll != 1 and roll + rank >= difficulty)


def run_outcome(displacement, minimum):
    return 'no_movement' if displacement == 0 else 'success' if displacement >= minimum else 'partial'


def defense_succeeds(defense_roll, defense_rank, defense_strategy,
                     attack_roll, attack_rank, attack_strategy):
    return defense_roll + defense_rank + defense_strategy >= attack_roll + attack_rank + attack_strategy


def damage_path(outcome, potential, extra, roll, shield, armor, body):
    """Distribute native ordinary/critical/self-hit damage through supplied sinks.

    Sinks may publish legacy effects or collect immutable proposals. Critical
    extra die is rolled before protection and bypasses both protection layers.
    Fatal has deliberately no ordinary damage path.
    """
    if outcome not in ('normal', 'critical', 'hit self'):
        return
    ordinary = roll(f'1d{potential}')
    critical = roll(f'1d{potential}') if outcome == 'critical' else 0
    body(armor(shield(ordinary + extra)), critical)


def least_armor_defense(defenses, penetration, attribute):
    values = []
    for kind in penetration.split(','):
        if kind not in defenses or attribute not in defenses[kind]:
            return 0
        values.append(defenses[kind][attribute])
    return min(values, default=1000)


def melee_path_status(distance, reach, path):
    if distance is None or distance == 0:
        return 'unplaced', distance
    if distance > reach:
        return 'out_of_reach', distance
    if path is None:
        return 'unplaced', distance
    if path.intersections:
        return 'blocked', distance
    if path.unmodeled_entity_ids:
        return 'uncertain_path', distance
    return 'in_reach', distance

"""Native calculation kernels shared by live Actions and inactive proposals.

No world access or effects. Callers own the supplied dice/check/save functions.
"""
import math


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


def _distance_to_hex_prism(position, center, vertex_offsets):
    """Distance from a point to the target hex at its native position height."""
    px, py = position.x, position.y
    vertices = tuple((center.x + x, center.y + y) for x, y in vertex_offsets)
    crosses = []
    for first, second in zip(vertices, vertices[1:] + vertices[:1]):
        crosses.append((second[0] - first[0]) * (py - first[1])
                       - (second[1] - first[1]) * (px - first[0]))
    # Vertex order is counter-clockwise. The tolerance only stabilizes the
    # closed polygon edge; reach tangency itself remains a strict comparison.
    inside = all(value >= -1e-12 for value in crosses)
    planar = 0.0 if inside else math.inf
    if not inside:
        for first, second in zip(vertices, vertices[1:] + vertices[:1]):
            dx, dy = second[0] - first[0], second[1] - first[1]
            length2 = dx * dx + dy * dy
            fraction = max(0.0, min(1.0,
                ((px - first[0]) * dx + (py - first[1]) * dy) / length2))
            qx, qy = first[0] + fraction * dx, first[1] + fraction * dy
            planar = min(planar, math.hypot(px - qx, py - qy))
    return math.hypot(planar, position.z - center.z)


def melee_hex_path_status(source, target, reach, path, layout, facing=None):
    """Resolve Being targetability by positive overlap with its occupied hex.

    The occupied address comes from the target's authoritative impact-time
    point and the native finite layout's deterministic edge-tie policy. The
    reach envelope must penetrate the hex interior: exact tangency is out of
    reach. This changes no intervening-path, defense, or hit rules.
    """
    from spatial.state import CartesianPosition
    from arena_hex_map import HexAddress

    if (not isinstance(source, CartesianPosition)
            or not isinstance(target, CartesianPosition)):
        return 'unplaced', None
    distance = math.dist(source.as_tuple(), target.as_tuple())
    address = layout.cell_at_position(target)
    if type(address) is not HexAddress:
        return 'unplaced', distance
    center = layout.center_position(address, z=target.z)
    separation = _distance_to_hex_prism(source, center,
                                        layout.vertex_offsets_meters)
    if not separation < reach:
        return 'out_of_reach', distance
    if facing is None:
        return 'unplaced', distance
    try:
        from hex_facing import FacingSector, classify_vector, validate_facing
        validate_facing(facing)
        if classify_vector(facing, (target.x - source.x,
                                    target.y - source.y, target.z - source.z)) is not FacingSector.FRONT:
            return 'not_facing', distance
    except ValueError:
        return 'not_facing', distance
    if path is None:
        return ('uncertain_path' if source == target else 'unplaced'), distance
    if path.intersections:
        return 'blocked', distance
    if path.unmodeled_entity_ids:
        return 'uncertain_path', distance
    return 'in_reach', distance

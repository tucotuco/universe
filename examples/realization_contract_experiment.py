"""Three small inquiries into *one* minimal objective-realization contract.

Demonstration only, not a full Group/Being/physics adapter. It tests whether
historical, compositional and physical models can share the same commitment
rules. Run: python examples/realization_contract_experiment.py
"""
from pathlib import Path
from random import Random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from realization import Fact, FactKey, ImpossibleRealization, RealityLedger
from realization_constraints import bounded_speed, fixed_composition, within_lifetime


def run_experiment():
    caravan = "nomadic-caravan"
    hunter = "hunter-father"
    adults = FactKey(caravan, "formation_adults", 0)
    h1 = FactKey(caravan, "household_adults", 0, "household-1")
    h2 = FactKey(caravan, "household_adults", 0, "household-2")
    career = FactKey(hunter, "career", 40)
    training = FactKey(hunter, "training_event", 16)
    at0 = FactKey(caravan, "position", 0)
    at5 = FactKey(caravan, "position", 5)
    at10 = FactKey(caravan, "position", 10)

    ledger = RealityLedger(validators=(
        fixed_composition(caravan, 0, "formation_adults", "household_adults",
                          ("household-1", "household-2")),
        within_lifetime(hunter, "training_event", 0, 40),
        bounded_speed(caravan, 2.0),
    ))
    ledger.commit((Fact(adults, 9, "established"),
                   Fact(career, "veteran hunter", "established"),
                   Fact(at0, [0, 0, 0], "established"),
                   Fact(at10, [10, 0, 0], "established")))
    initially_unresolved = ledger.inspect(h1) is None
    group_detail = ledger.ask(h1, lambda facts: [
        Fact(h1, 4), Fact(h2, facts.get(adults) - 4)])

    # The listener's claim is not evidence of a historical fact: only a
    # truthful inquiry into objective reality can trigger realization here.
    spoken_claim = "I slew a dragon when I was eight"
    # A provisional generation rule. Changing seed or distribution may change
    # an *uncommitted* story, but once committed, revisiting it cannot.
    training_options = {
        "veteran hunter": (
            "apprenticed with traveling hunters",
            "learned tracking from a village elder",
            "learned survival skills while herding livestock",
        )
    }
    def generate_training(view):
        role = view.get(career)
        return [Fact(training, Random(29).choice(training_options[role]),
                     "conditional_backstory_generator")]
    established_training = ledger.ask(training, generate_training)

    try:
        ledger.commit((Fact(at5, [100, 0, 0]),))
    except ImpossibleRealization:
        invalid_position_rejected = True
    else:
        invalid_position_rejected = False
    midpoint = ledger.ask(at5, lambda facts: [Fact(at5, [5, 0.5, 0])])
    # Repeated inquiry cannot silently generate a new past.
    second_inquiry = ledger.ask(training, lambda facts: [
        Fact(training, "different childhood")])

    return dict(ledger=ledger, group_detail=group_detail,
                initially_unresolved=initially_unresolved,
                established_training=established_training,
                spoken_claim=spoken_claim,
                invalid_position_rejected=invalid_position_rejected,
                midpoint=midpoint, second_inquiry=second_inquiry)


if __name__ == "__main__":
    outcome = run_experiment()
    print("Composition:", [(r.key.detail, r.value)
                           for r in outcome["ledger"].view().facts_at("nomadic-caravan", 0)
                           if r.key.attribute == "household_adults"])
    print("Back-story:", outcome["established_training"].record.value)
    print("An unverified bar story remains only a statement:", outcome["spoken_claim"])
    print("Infeasible movement rejected:", outcome["invalid_position_rejected"])
    print("Realized position at t=5:", outcome["midpoint"].record.value)
    print("Repeated inquiry creates new history:", outcome["second_inquiry"].newly_realized)

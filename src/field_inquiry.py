"""Minimal evidence-driven follow-up policy; no access to objective group reality.

This policy is only a *decision scaffold*. Reported uncertainty intervals
are not calibrated confidence intervals, and conflicting evidence might be
correlated. Planning an observation does not guarantee it will be possible or
successful; the scheduled ObserveGroupAction still determines that.
"""
from __future__ import annotations

import math

from field_observation import BeliefLedger, InquiryProposal


class InquiryPolicy:
    """Prefer conflicting reports, otherwise investigate large relative uncertainty."""

    def __init__(self, relative_uncertainty_threshold=0.7):
        if (isinstance(relative_uncertainty_threshold, bool) or
                not isinstance(relative_uncertainty_threshold, (int, float)) or
                not math.isfinite(relative_uncertainty_threshold) or
                relative_uncertainty_threshold <= 0):
            raise ValueError("relative uncertainty threshold must be finite and positive")
        self.relative_uncertainty_threshold = float(relative_uncertainty_threshold)

    def propose(self, ledger, group_id, time):
        """Return one reproducible question the Agent has reason to investigate.

        Conflict priority is based on report-interval nonoverlap, not access to
        the actual composition. No mutation occurs until an Action is scheduled.
        """
        if not isinstance(ledger, BeliefLedger):
            raise TypeError("planner requires a BeliefLedger")
        if not isinstance(group_id, str) or not group_id:
            raise ValueError("group_id must be nonempty")
        if isinstance(time, bool) or not isinstance(time, (int, float)) or not math.isfinite(time):
            raise ValueError("inquiry time must be finite")
        time = float(time)
        reports = [e for e in ledger.evidence if e.group_id == group_id]
        if not reports:
            return None  # No evidence to motivate an investigation.
        if time < max(e.time for e in reports):
            raise ValueError("inquiry cannot predate its evidence")
        disputes = sorted(ledger.discrepancies(group_id))
        if disputes:
            category, first, second = disputes[0]
            return InquiryProposal(ledger.observer_id, group_id, category,
                                   "conflicting_reports", (first, second), time)

        # Only summaries of *interpreted evidence* are available, not truth.
        # Relative reported half-width is an uncalibrated selection heuristic.
        candidates = []
        categories = sorted({name for e in reports for name in ledger.reports_for_observation(e.id)})
        for category in categories:
            estimate = ledger.count_estimate(group_id, category)
            category_reports = [(e.id, ledger.reports_for_observation(e.id)[category])
                                for e in reports if category in ledger.reports_for_observation(e.id)]
            # Choose the tightest available interval as a conservative cue about
            # what at least one source claims; these are not posterior intervals.
            half_width = min(r.uncertainty for _, r in category_reports)
            relative = half_width / max(1.0, estimate)
            if relative >= self.relative_uncertainty_threshold:
                candidates.append((-relative, category, tuple(i for i, _ in category_reports)))
        if not candidates:
            return None
        _, category, ids = sorted(candidates)[0]
        return InquiryProposal(ledger.observer_id, group_id, category,
                               "uncertain_estimate", ids, time)

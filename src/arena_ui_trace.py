"""Opt-in, bounded terminal tracing for generated Arena UI actions."""

from __future__ import annotations

import sys
import threading
import time


_RATES = frozenset(("walk", "hustle", "jog", "run", "sprint"))
_POLICIES = frozenset(("turn", "maintain"))
_CLIENT_EVENTS = {
    "page_script_ready": frozenset(),
    "page_script_error": frozenset(),
    "generate_clicked": frozenset(),
    "canvas_click_received": frozenset(),
    "canvas_modal_blocked": frozenset(),
    "canvas_player_marker_hit": frozenset(),
    "canvas_entity_marker_hit": frozenset(("entity_category",)),
    "canvas_marker_missed": frozenset(),
    "canvas_hex_missed": frozenset(),
    "canvas_hex_selected": frozenset(("column", "row")),
    "destination_request_queued": frozenset(("column", "row", "rate", "facing_policy")),
    "destination_request_accepted": frozenset(("column", "row")),
    "destination_request_refused": frozenset(),
    "rate_selected": frozenset(("rate",)),
    "facing_policy_selected": frozenset(("facing_policy",)),
    "advance_clicked": frozenset(),
    "stop_clicked": frozenset(),
    "run_clicked": frozenset(),
    "encounter_name_apply_clicked": frozenset(),
    "player_name_apply_clicked": frozenset(),
    "entity_selected": frozenset(),
    "character_sheet_opened": frozenset(),
    "pickup_clicked": frozenset(),
    "ready_weapon_clicked": frozenset(),
    "melee_strike_clicked": frozenset(),
    "rename_entity_clicked": frozenset(),
}


class ArenaUITerminalTrace:
    """Print only fixed-schema Arena UI and native movement facts."""

    def __init__(self, enabled=False, *, stream=None, clock=None):
        self.enabled = enabled is True
        self._stream = stream or sys.stdout
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._request_id = 0
        self._accepted_client_events = 0
        self._window_started = self._clock()
        self._window_count = 0
        self._line_window_started = self._window_started
        self._line_window_count = 0
        self._line_count = 0

    def _write_locked(self, line, now):
        if self._line_count >= 10000:
            return False
        if now - self._line_window_started >= 1.0:
            self._line_window_started = now
            self._line_window_count = 0
        if self._line_window_count >= 100:
            return False
        self._line_window_count += 1
        self._line_count += 1
        try:
            print(line, file=self._stream, flush=True)
        except Exception:
            # Diagnostics must never interrupt a session operation.
            pass
        return True

    def _print(self, prefix, fields):
        if not self.enabled:
            return
        with self._lock:
            self._write_locked(f"[{prefix}] {fields}", self._clock())

    @staticmethod
    def _client_seq(value):
        if type(value) is int and 1 <= value <= 2**31 - 1:
            return value
        return None

    def begin_request(self, action, client_seq=None):
        if not self.enabled:
            return None, None
        if type(action) is not str or not action.isascii() or not action.isidentifier():
            action = "unknown"
        seq = self._client_seq(client_seq)
        with self._lock:
            self._request_id = 1 if self._request_id >= 2**31 - 1 else self._request_id + 1
            request_id = self._request_id
        return request_id, seq

    def http_result(self, request_id, client_seq, action, status, http_status,
                    *, classification=None, detail=None):
        if not self.enabled or request_id is None:
            return
        fields = [f"req={request_id}"]
        if client_seq is not None:
            fields.append(f"client_seq={client_seq}")
        fields.extend((f"action={action}", f"status={status}", f"http={http_status}"))
        if classification:
            if type(classification) is str and classification.isascii() and classification.isidentifier():
                fields.append(f"reason={classification}")
        if type(detail) is str and detail:
            fields.append(detail[:256])
        self._print("arena-http", " ".join(fields))

    def native_advance(self, request_id, client_seq, fields):
        if not self.enabled:
            return
        parts = []
        if request_id is not None:
            parts.append(f"req={request_id}")
        if client_seq is not None:
            parts.append(f"client_seq={client_seq}")
        parts.append(fields)
        self._print("arena-native", " ".join(parts))

    def client_event(self, payload):
        """Validate and print one small client-only event; never changes Arena state."""
        if not self.enabled:
            raise ValueError("terminal UI tracing is disabled")
        if type(payload) is not dict:
            raise ValueError("trace event must be an object")
        event = payload.get("event")
        seq = payload.get("seq")
        if type(event) is not str or event not in _CLIENT_EVENTS:
            raise ValueError("unsupported trace event")
        if type(seq) is not int or not 1 <= seq <= 2**31 - 1:
            raise ValueError("trace sequence must be a positive bounded integer")
        expected = {"seq", "event"} | set(_CLIENT_EVENTS[event])
        if set(payload) != expected:
            raise ValueError("trace event has unknown or missing fields")

        details = []
        if event in ("canvas_hex_selected", "destination_request_accepted"):
            column, row = payload["column"], payload["row"]
            if (type(column) is not int or type(row) is not int
                    or not -10000 <= column <= 10000 or not -10000 <= row <= 10000):
                raise ValueError("trace hex address is outside the accepted range")
            details.append(f"cell=({column},{row})")
        elif event == "destination_request_queued":
            column, row = payload["column"], payload["row"]
            if (type(column) is not int or type(row) is not int
                    or not -10000 <= column <= 10000 or not -10000 <= row <= 10000):
                raise ValueError("trace hex address is outside the accepted range")
            rate, policy = payload["rate"], payload["facing_policy"]
            if type(rate) is not str or rate not in _RATES:
                raise ValueError("trace rate is unsupported")
            if type(policy) is not str or policy not in _POLICIES:
                raise ValueError("trace facing policy is unsupported")
            details.extend((f"cell=({column},{row})", f"rate={rate}", f"policy={policy}"))
        elif event == "canvas_entity_marker_hit":
            category = payload["entity_category"]
            if type(category) is not str or category not in ("being", "object"):
                raise ValueError("trace entity category is unsupported")
            details.append(f"entity_category={category}")
        elif event == "rate_selected":
            if type(payload["rate"]) is not str or payload["rate"] not in _RATES:
                raise ValueError("trace rate is unsupported")
            details.append(f"rate={payload['rate']}")
        elif event == "facing_policy_selected":
            if type(payload["facing_policy"]) is not str or payload["facing_policy"] not in _POLICIES:
                raise ValueError("trace facing policy is unsupported")
            details.append(f"facing_policy={payload['facing_policy']}")

        now = self._clock()
        with self._lock:
            if self._accepted_client_events >= 2000:
                raise ValueError("trace event budget exhausted")
            if now - self._window_started >= 1.0:
                self._window_started = now
                self._window_count = 0
            if self._window_count >= 30:
                raise ValueError("trace event rate limit exceeded")
            suffix = " " + " ".join(details) if details else ""
            if not self._write_locked(f"[arena-ui] seq={seq} event={event}{suffix}", now):
                raise ValueError("trace output rate limit exceeded")
            self._window_count += 1
            self._accepted_client_events += 1
        return {"accepted": True}

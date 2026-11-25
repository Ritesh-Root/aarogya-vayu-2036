"""Per-visitor demo sandbox.

Each browser gets a session cookie. With the sandbox on, stock, consignments and the audit chain live in
memory per (session, region), seeded from the bundled demo files, so one visitor's clicks never change
what another sees. Sessions expire after a day idle and the oldest are evicted past a cap.
"""
import os
import re
import threading
import time
from collections import OrderedDict
from contextvars import ContextVar
from typing import Callable, Dict, Optional

SESSION_COOKIE = "av_session"
SANDBOX_ENABLED = os.getenv("AV_SANDBOX", "0") == "1"
SANDBOX_MAX_SESSIONS = int(os.getenv("SANDBOX_MAX_SESSIONS", "500"))
SANDBOX_TTL_S = 86400

current_session: ContextVar[str] = ContextVar("current_session", default="shared")
current_region: ContextVar[Optional[str]] = ContextVar("current_region", default=None)

_SESSION_RE = re.compile(r"^[0-9a-f]{32}$")


def valid_session_id(value: Optional[str]) -> bool:
    return bool(value) and bool(_SESSION_RE.match(value))


class SessionStore:
    def __init__(self, max_sessions: int = SANDBOX_MAX_SESSIONS, ttl_s: float = SANDBOX_TTL_S):
        self.max_sessions = max_sessions
        self.ttl_s = ttl_s
        self._sessions: "OrderedDict[str, dict]" = OrderedDict()
        self._lock = threading.RLock()

    def _expire(self, now: float) -> None:
        while self._sessions:
            sid, entry = next(iter(self._sessions.items()))
            if now - entry["ts"] < self.ttl_s and len(self._sessions) <= self.max_sessions:
                break
            del self._sessions[sid]

    def get(self, session_id: str, region: str, seed: Callable[[], dict]) -> dict:
        """The session's mutable state for a region, seeded on first use. Touching it renews the session."""
        with self._lock:
            now = time.time()
            entry = self._sessions.pop(session_id, None)
            if entry is not None and now - entry["ts"] >= self.ttl_s:
                entry = None
            if entry is None:
                entry = {"ts": now, "regions": {}}
            entry["ts"] = now
            self._expire(now)
            self._sessions[session_id] = entry
            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)
            regions: Dict[str, dict] = entry["regions"]
            if region not in regions:
                regions[region] = seed()
            return regions[region]

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)


SESSIONS = SessionStore()


def sessions() -> SessionStore:
    """Look up the module attribute each time so tests can swap the store."""
    import app.sandbox as _self
    return _self.SESSIONS

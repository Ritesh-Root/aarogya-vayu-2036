import json
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

from app import sandbox as sandbox_mod
from app.regions import DEFAULT_REGION, get_region

class AuditLedger:
    def __init__(self, ledger_file: Optional[str] = None, sandbox: Optional[bool] = None):
        self.sandbox = sandbox_mod.SANDBOX_ENABLED if sandbox is None else sandbox
        self._file_entries: List[Dict[str, Any]] = []
        self.seed_fn = None  # set by StorageManager.attach_ledger so a chain and its stock are seeded together
        if ledger_file is None:
            base_dir = Path(__file__).resolve().parent.parent
            ledger_file = str(base_dir / "data" / "audit_log.json")
        self.ledger_file = ledger_file
        self._load()

    # In sandbox mode each (visitor, region) has its own chain, starting with its own GENESIS block.
    def _chain(self, region: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.sandbox:
            return self._file_entries
        reg = get_region(region or sandbox_mod.current_region.get() or DEFAULT_REGION).id
        seed = self.seed_fn or (lambda r: {"ledger": []})
        state = sandbox_mod.sessions().get(sandbox_mod.current_session.get(), reg, lambda: seed(reg))
        chain = state.setdefault("ledger", [])
        if not chain:
            chain.append(self._make_entry(chain, "GENESIS", {"message": f"Aarogya-Vāyu demo audit ledger initialised ({reg})"},
                                          "SYSTEM_INITIALIZER"))
        return chain

    @property
    def entries(self) -> List[Dict[str, Any]]:
        return self._chain()

    @entries.setter
    def entries(self, value: List[Dict[str, Any]]) -> None:
        self._file_entries = value

    def rollback_to(self, length: int, region: Optional[str] = None) -> None:
        """Drop entries recorded after `length` (their change was never saved)."""
        chain = self._chain(region)
        del chain[length:]
        if not self.sandbox:
            self._save()

    def discard_head(self, entry: Dict[str, Any]) -> None:
        """Remove `entry` if it is the newest block of any chain this request touched."""
        chain = self._chain()
        if chain and chain[-1].get("current_hash") == entry.get("current_hash"):
            chain.pop()
            if not self.sandbox:
                self._save()

    def _load(self):
        loaded = False
        for path in [self.ledger_file, "/tmp/audit_log.json"]:
            try:
                with open(path, "r") as f:
                    self._file_entries = json.load(f)
                    loaded = True
                    break
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                continue
        if not loaded:
            self._file_entries = []
            # Genesis block
            self.record_entry(
                event_type="GENESIS",
                details={"message": "Aarogya-Vāyu audit ledger initialised (demo regions)"},
                approved_by="SYSTEM_INITIALIZER"
            )

    def _save(self):
        try:
            with open(self.ledger_file, "w") as f:
                json.dump(self._file_entries, f, indent=2)
        except OSError:
            try:
                with open("/tmp/audit_log.json", "w") as f:
                    json.dump(self._file_entries, f, indent=2)
            except Exception:
                pass

    def record_entry(self, event_type: str, details: Dict[str, Any], approved_by: str = "SYSTEM",
                     region: Optional[str] = None) -> Dict[str, Any]:
        token = sandbox_mod.current_region.set(get_region(region).id) if region else None
        try:
            chain = self._chain()
            entry = self._make_entry(chain, event_type, details, approved_by)
            chain.append(entry)
            if not self.sandbox:
                self._save()
            return entry
        finally:
            if token is not None:
                sandbox_mod.current_region.reset(token)

    @staticmethod
    def _make_entry(chain: List[Dict[str, Any]], event_type: str, details: Dict[str, Any], approved_by: str) -> Dict[str, Any]:
        prev_hash = chain[-1]["current_hash"] if chain else "0" * 64
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        
        payload_str = f"{len(chain)}|{timestamp}|{event_type}|{json.dumps(details, sort_keys=True)}|{approved_by}|{prev_hash}"
        current_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        entry = {
            "index": len(chain),
            "timestamp": timestamp,
            "event_type": event_type,
            "approved_by": approved_by,
            "details": details,
            "prev_hash": prev_hash,
            "current_hash": current_hash
        }
        return entry

    def get_recent_entries(self, limit: int = 15) -> List[Dict[str, Any]]:
        limit = max(1, min(100, int(limit)))  # entries[-0:] would return the whole ledger
        return list(reversed(self.entries[-limit:]))

    def verify_chain_integrity(self) -> Dict[str, Any]:
        """
        Cryptographically validates the entire SHA-256 hash chain from genesis to head.
        Shows tampering (any edited entry breaks the chain); entries are not signed, so it does not prove who wrote them.
        """
        if not self.entries:
            return {"valid": True, "total_blocks": 0, "head_hash": None, "tamper_evident": True}

        expected_prev_hash = "0" * 64
        for i, entry in enumerate(self.entries):
            # 1. Validate block index continuity
            if entry.get("index") != i:
                return {
                    "valid": False,
                    "error": f"Block index discontinuity at position {i}: expected {i}, got {entry.get('index')}",
                    "compromised_index": i
                }

            # 2. Validate cryptographic link to previous block
            if entry.get("prev_hash") != expected_prev_hash:
                return {
                    "valid": False,
                    "error": f"Broken cryptographic link at block {i}: expected prev_hash {expected_prev_hash}, got {entry.get('prev_hash')}",
                    "compromised_index": i
                }

            # 3. Recalculate block SHA-256 hash over deterministic payload
            payload_str = f"{entry['index']}|{entry['timestamp']}|{entry['event_type']}|{json.dumps(entry['details'], sort_keys=True)}|{entry['approved_by']}|{entry['prev_hash']}"
            recomputed_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

            if recomputed_hash != entry.get("current_hash"):
                return {
                    "valid": False,
                    "error": f"Tampering detected at block {i}: stored hash {entry.get('current_hash')} does not match recomputed hash {recomputed_hash}",
                    "compromised_index": i
                }

            expected_prev_hash = entry["current_hash"]

        return {
            "valid": True,
            "total_blocks": len(self.entries),
            "head_hash": self.entries[-1]["current_hash"],
            "genesis_hash": self.entries[0]["current_hash"],
            "tamper_evident": True,
            "algorithm": "SHA-256 Chained Hash Ledger",
            "verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        }


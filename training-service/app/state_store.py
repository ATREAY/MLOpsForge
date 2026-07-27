"""Tracks in-flight jobs across training-service restarts. Deliberately a flat
JSON file rather than a database: this service's only state is "which Slurm
job ids am I polling and where do I report their status" — the system of
record for everything else (job history, metrics, models) is the backend's
Postgres, reached via the callback_url stored per job.
"""

import json
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()


class JobStateStore:
    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("{}")

    def _read(self) -> dict[str, Any]:
        return json.loads(self._path.read_text() or "{}")

    def _write(self, data: dict[str, Any]) -> None:
        tmp_path = self._path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(data, indent=2))
        tmp_path.replace(self._path)

    def put(self, job_id: str, record: dict[str, Any]) -> None:
        with _lock:
            data = self._read()
            data[job_id] = record
            self._write(data)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with _lock:
            return self._read().get(job_id)

    def update(self, job_id: str, **fields: Any) -> None:
        with _lock:
            data = self._read()
            if job_id not in data:
                raise KeyError(job_id)
            data[job_id].update(fields)
            self._write(data)

    def all_active(self) -> dict[str, dict[str, Any]]:
        """Jobs not yet in a terminal state — what the poller needs to check."""
        terminal = {"finished", "failed", "cancelled"}
        with _lock:
            return {jid: rec for jid, rec in self._read().items() if rec.get("status") not in terminal}

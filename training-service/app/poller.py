"""Background thread that periodically reconciles every active job's Slurm
state. A plain thread + sleep loop rather than APScheduler/Celery — the only
job is "call reconcile_job on a timer," which doesn't need a task queue."""

import logging
import threading
import time

from app.orchestrator import reconcile_job
from app.state_store import JobStateStore

logger = logging.getLogger(__name__)


class JobPoller:
    def __init__(self, store: JobStateStore, interval_seconds: int):
        self._store = store
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _run(self) -> None:
        while not self._stop_event.is_set():
            for job_id, record in self._store.all_active().items():
                try:
                    reconcile_job(self._store, job_id, record)
                except Exception:  # noqa: BLE001 — one job's polling failure must not kill the loop
                    logger.exception("failed to reconcile job %s", job_id)
            self._stop_event.wait(self._interval)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="slurm-job-poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

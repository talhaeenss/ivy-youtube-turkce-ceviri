"""Tek kullanicilik yerel is durumu (bellekte)."""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass, field
from typing import Optional

MAX_JOBS = 24


@dataclass
class JobState:
    status: str = "queued"  # queued | running | done | error
    percent: int = 0
    message: str = ""
    work_dir: str = ""
    output_path: Optional[str] = None
    error: Optional[str] = None
    created: float = field(default_factory=lambda: time.time())


JOBS: dict[str, JobState] = {}


def prune_old_jobs() -> None:
    while len(JOBS) > MAX_JOBS:
        done_or_err = [(k, v) for k, v in JOBS.items() if v.status in ("done", "error")]
        if not done_or_err:
            break
        jid = min(done_or_err, key=lambda x: x[1].created)[0]
        st = JOBS[jid]
        shutil.rmtree(st.work_dir, ignore_errors=True)
        del JOBS[jid]

#!/usr/bin/env python3
"""Self-check for watchdog.py. Run:  python3 selftest.py
Feeds synthetic mouse packets through a FIFO (so it works without a real mouse)."""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WATCHDOG = Path(__file__).resolve().parent / "watchdog.py"
PACKET = b"\x08\x05\x02"


def _lines(log):
    return [l for l in log.read_text().splitlines() if l.strip()] if log.exists() else []


def _wait_lines(log, n, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if len(_lines(log)) >= n:
            return True
        time.sleep(0.1)
    return len(_lines(log)) >= n


def main():
    with tempfile.TemporaryDirectory() as wd:
        wd = Path(wd)
        fifo = wd / "mouse"
        os.mkfifo(fifo)
        log = wd / "mouse_tracker.log"
        script = wd / "watchdog.py"
        shutil.copy(WATCHDOG, script)
        p = subprocess.Popen([sys.executable, str(script), str(fifo)], cwd=str(wd),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        wfd = os.open(str(fifo), os.O_RDWR)
        try:
            os.write(wfd, PACKET)
            ok1 = _wait_lines(log, 1, 5)
            for _ in range(5):
                os.write(wfd, PACKET)
                time.sleep(0.1)
            _wait_lines(log, 1, 5)
            time.sleep(1)
            ok2 = len(_lines(log)) == 1
        finally:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            os.close(wfd)

    print(("PASS" if ok1 else "FAIL"), "movement writes a line")
    print(("PASS" if ok2 else "FAIL"), "rapid movements = at most one line in 10s")
    print(f"\n{ok1 + ok2}/2 checks passed.")
    return 0 if ok1 and ok2 else 1


if __name__ == "__main__":
    sys.exit(main())

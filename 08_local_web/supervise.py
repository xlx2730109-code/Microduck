"""Run the two local Microduck demos and restart failed child processes."""
from pathlib import Path
import json
import ctypes
from ctypes import wintypes
import logging
from logging.handlers import RotatingFileHandler
import msvcrt
import os
import subprocess
import sys
import time
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / "python" / "python.exe"
URLS = ["http://127.0.0.1:8080/", "http://127.0.0.1:18080/"]
OPENER = build_opener(ProxyHandler({}))


class ChildJob:
    """Windows closes the job and its children even if the supervisor is killed."""

    def __init__(self):
        class BasicLimits(ctypes.Structure):
            _fields_ = [("ProcessTime", ctypes.c_longlong), ("JobTime", ctypes.c_longlong),
                        ("LimitFlags", wintypes.DWORD), ("MinWorkingSet", ctypes.c_size_t),
                        ("MaxWorkingSet", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class IOCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                        ("ReadCount", "WriteCount", "OtherCount", "ReadBytes", "WriteBytes", "OtherBytes")]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [("Basic", BasicLimits), ("IO", IOCounters),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemory", ctypes.c_size_t), ("PeakJobMemory", ctypes.c_size_t)]

        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                    ctypes.c_void_p, wintypes.DWORD]
        self.api.SetInformationJobObject.restype = wintypes.BOOL
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.AssignProcessToJobObject.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.CloseHandle.restype = wintypes.BOOL
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.Basic.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.get_last_error()
            self.close()
            raise ctypes.WinError(error)

    def assign(self, process):
        if not self.api.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle))):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


def commands():
    studio = ROOT / "studio"
    return [
        ("servo", [str(PYTHON), "-B", "-u", str(ROOT / "launch_servo.py"),
                   str(studio / "deps"), str(ROOT / "servo")]),
        ("fake", [str(PYTHON), "-B", "-u", "-I", str(studio / "dev/fake_robotd.py"),
                  "--fixture", str(studio / "tests/fixtures/now-20261018.jsonl"),
                  "--robotd-port", "17001", "--configd-port", "17002",
                  "--net-mode", "hotspot", "--net-state-file", str(ROOT / "state/net.json")]),
        ("studio", [str(PYTHON), "-B", "-u", "-I", str(studio / "run.py"),
                    "--listen", "127.0.0.1:18080", "--robotd", "tcp:127.0.0.1:17001",
                    "--configd", "tcp:127.0.0.1:17002", "--net-state", str(ROOT / "state/net.json"),
                    "--dev-autologin", "--state-dir", str(ROOT / "state"),
                    "--log-dir", str(ROOT / "logs/studio"), "--dev-duck-root", str(ROOT / "duckfs"),
                    "--servo-sim", "--duck-label", "Microduck-DEMO", "--tof", "none",
                    "--camera-socket", "none"]),
    ]


def check():
    rows = []
    for url in URLS:
        try:
            with OPENER.open(url, timeout=4) as response:
                rows.append({"url": url, "status": response.status})
        except Exception as exc:
            rows.append({"url": url, "error": str(exc)})
    return rows


def stop_children(children):
    for _, proc, _ in children:
        if proc.poll() is None:
            proc.terminate()
    for _, proc, handle in children:
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        handle.close()


def main():
    if "--status" in sys.argv:
        rows = check()
        print(json.dumps(rows, ensure_ascii=False))
        return int(any(row.get("status") != 200 for row in rows))
    if "--print-config" in sys.argv:
        print(json.dumps(commands(), ensure_ascii=False, indent=2))
        return 0
    for directory in ["logs", "logs/studio", "state", "duckfs"]:
        (ROOT / directory).mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("microduck-local-web")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(ROOT / "logs/supervisor.log", maxBytes=2_000_000,
                                  backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    lock = (ROOT / "state/supervisor.lock").open("a+b")
    lock.seek(0, 2)
    if not lock.tell():
        lock.write(b"0")
        lock.flush()
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        logger.info("Another supervisor already holds the lock")
        lock.close()
        return 0
    env = os.environ.copy()
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    logger.info("Supervisor started pid=%s root=%s", os.getpid(), ROOT)
    children = []
    failures = 0
    job = None
    try:
        job = ChildJob()
        while True:
            started = time.monotonic()
            children = []
            try:
                for name, command in commands():
                    log_path = ROOT / ("logs/" + name + ".log")
                    if log_path.exists() and log_path.stat().st_size > 5_000_000:
                        log_path.replace(log_path.with_suffix(".log.1"))
                    handle = log_path.open("ab", buffering=0)
                    try:
                        proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                                stdout=handle, stderr=subprocess.STDOUT, env=env,
                                                creationflags=subprocess.CREATE_NO_WINDOW)
                    except BaseException:
                        handle.close()
                        raise
                    children.append((name, proc, handle))
                    job.assign(proc)
                    logger.info("Started %s pid=%s", name, proc.pid)
                (ROOT / "state/processes.json").write_text(json.dumps({
                    "supervisor": os.getpid(),
                    "children": {name: proc.pid for name, proc, _ in children},
                    "started": time.strftime("%Y-%m-%d %H:%M:%S"),
                }, indent=2), encoding="utf-8")
                next_health = time.monotonic() + 15
                unhealthy = 0
                while True:
                    for name, proc, _ in children:
                        code = proc.poll()
                        if code is not None:
                            raise RuntimeError(f"{name} exited with code {code}")
                    if time.monotonic() >= next_health:
                        rows = check()
                        unhealthy = unhealthy + 1 if any(r.get("status") != 200 for r in rows) else 0
                        if unhealthy >= 3:
                            raise RuntimeError("HTTP health failed three times: " + json.dumps(rows))
                        next_health = time.monotonic() + 15
                    time.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                logger.exception("Restarting demo processes")
            finally:
                stop_children(children)
                children = []
            failures = 0 if time.monotonic() - started > 60 else failures + 1
            delay = min(30, 2 ** min(failures, 5))
            logger.info("Retry in %s seconds", delay)
            time.sleep(delay)
    except KeyboardInterrupt:
        logger.info("Supervisor interrupted")
        return 0
    except BaseException:
        logger.exception("Supervisor failed")
        return 1
    finally:
        stop_children(children)
        if job is not None:
            job.close()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        lock.close()


if __name__ == "__main__":
    raise SystemExit(main())

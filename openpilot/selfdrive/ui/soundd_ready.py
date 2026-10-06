"""
soundd audio-stream readiness marker.

On some comma devices the audio device only becomes usable 25-40 s after the manager starts, so soundd may still be
waiting for its output stream when the car is ready to engage. soundd writes its PID here once the stream is open, and
selfdrived blocks engagement (processNotRunning) until the marker matches the running soundd's PID, so that alerts can
be heard before the system can be engaged. The PID check makes a marker left by an earlier soundd instance invalid.
"""
import os
import tempfile

from openpilot.common.hardware.hw import Paths
from openpilot.common.swaglog import cloudlog


def marker_path() -> str:
  prefix = os.environ.get("OPENPILOT_PREFIX")
  name = f"soundd_stream_ready_{prefix}" if prefix else "soundd_stream_ready"
  return os.path.join(Paths.shm_path(), name)


def clear() -> None:
  """Remove a marker left by an earlier soundd instance (called when soundd starts)."""
  try:
    os.remove(marker_path())
  except FileNotFoundError:
    pass
  except OSError:
    cloudlog.exception("soundd: failed to clear stream ready marker")


def mark_ready(pid: int | None = None) -> None:
  """Atomically record that the soundd process `pid` (default: this process) has an open output stream."""
  pid = os.getpid() if pid is None else pid
  path = marker_path()
  tmp = None
  try:
    with tempfile.NamedTemporaryFile("w", dir=os.path.dirname(path), delete=False) as f:
      tmp = f.name
      f.write(str(pid))
    os.replace(tmp, path)
  except OSError:
    # fail closed: without the marker selfdrived keeps engagement blocked
    cloudlog.exception("soundd: failed to write stream ready marker")
    if tmp is not None and os.path.exists(tmp):
      os.remove(tmp)


def is_ready(pid: int) -> bool:
  try:
    with open(marker_path()) as f:
      return f.read().strip() == str(pid)
  except (OSError, ValueError):  # missing or unreadable marker: not ready
    return False


def audio_ready(processes, manager_state_received: bool) -> bool:
  """True once the managed soundd process has reported an open output stream.

  processes: managerState.processes. If soundd isn't managed or shouldn't be running there is nothing to wait for.
  """
  if not manager_state_received:
    return False
  soundd = next((p for p in processes if p.name == "soundd"), None)
  if soundd is None or not soundd.shouldBeRunning:
    return True
  return soundd.running and is_ready(soundd.pid)

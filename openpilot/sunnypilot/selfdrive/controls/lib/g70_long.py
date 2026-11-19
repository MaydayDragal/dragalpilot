"""
dragalpilot (G70 2024, openpilot longitudinal): optional settings, each read from a small text file on the device.
No file means stock behaviour for that setting.

  /data/g70_long_follow       "t1 t2 t3" or "t1 t2 t3 t4": following time in seconds for each gap setting, closest
                              first. Stock is 1.25 / 1.45 / 1.75 (aggressive / standard / relaxed). With four numbers
                              the distance button cycles through four settings and the cluster shows one to four
                              bars; settings 3 and 4 both use the "relaxed" driving personality for everything else.
                              The car's own cruise held 1.11 s on its closest setting and 1.39 s on the next.
  /data/g70_long_stop_extra   metres added to the distance kept to a lead, at every speed. The planner aims to stop
                              6 m behind a lead by its own measure; on the first drive the car stopped 0.8 m behind
                              one (the car's own cruise: 3.1 m median over 13 stops).
  /data/g70_long_engage_any   when this file exists, the accelerate / resume toggle engages at the current speed if
                              no set speed is stored yet, as the decelerate / set toggle does. Stock refuses it
                              ("Press Set to Engage").
  /data/g70_long_gap          written by selfdrived: the current gap setting (0-3) when four are in use.
"""
import os
import time

FOLLOW_FILE = "/data/g70_long_follow"
STOP_EXTRA_FILE = "/data/g70_long_stop_extra"
ENGAGE_ANY_FILE = "/data/g70_long_engage_any"
GAP_FILE = "/data/g70_long_gap"

FOLLOW_MIN = 1.0
FOLLOW_MAX = 2.5
STOP_EXTRA_MAX = 4.0


def read_follow_table(path: str = FOLLOW_FILE) -> tuple[float, ...] | None:
  try:
    with open(path) as f:
      values = tuple(float(x) for x in f.read().split())
  except (OSError, ValueError):
    return None
  if len(values) not in (3, 4) or any(v != v for v in values):
    return None
  values = tuple(min(max(v, FOLLOW_MIN), FOLLOW_MAX) for v in values)
  if any(b < a for a, b in zip(values[:-1], values[1:], strict=True)):
    return None
  return values


def read_stop_extra(path: str = STOP_EXTRA_FILE) -> float:
  try:
    with open(path) as f:
      value = float(f.read().split()[0])
  except (OSError, ValueError, IndexError):
    return 0.0
  if value != value:  # NaN
    return 0.0
  return min(max(value, 0.0), STOP_EXTRA_MAX)


def engage_any_enabled(path: str = ENGAGE_ANY_FILE) -> bool:
  return os.path.exists(path)


def gap_to_personality(gap: int) -> int:
  # gap settings 0-3 -> LongitudinalPersonality 0-2 (aggressive, standard, relaxed, relaxed)
  return min(max(int(gap), 0), 2)


def read_gap(path: str = GAP_FILE) -> int | None:
  try:
    with open(path) as f:
      gap = int(f.read().strip())
  except (OSError, ValueError):
    return None
  return gap if 0 <= gap <= 3 else None


def write_gap(gap: int, path: str = GAP_FILE) -> None:
  try:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
      f.write(str(int(gap)))
    os.replace(tmp, path)
  except OSError:
    pass


class GapReader:
  """The current gap setting for processes other than selfdrived; re-reads the file at most every `period` s."""
  def __init__(self, path: str = GAP_FILE, period: float = 0.5):
    self.path = path
    self.period = period
    self.gap: int | None = None
    self.t = -1e9

  def get(self, personality: int) -> int:
    # falls back to the personality whenever the file is missing or disagrees with it
    now = time.monotonic()
    if now - self.t > self.period:
      self.gap = read_gap(self.path)
      self.t = now
    if self.gap is None or gap_to_personality(self.gap) != personality:
      return personality
    return self.gap


def personality_raw(personality) -> int:
  return int(getattr(personality, "raw", personality))


def follow_time(personality, table: tuple[float, ...] | None, gap_reader: GapReader | None, stock: float) -> float:
  if table is None:
    return stock
  raw = min(max(personality_raw(personality), 0), 2)
  if len(table) == 4 and gap_reader is not None:
    return table[gap_reader.get(raw)]
  return table[raw]

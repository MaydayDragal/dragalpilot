"""
dragalpilot (G70 2024, openpilot longitudinal): optional settings, each read from a small text file on the device.
No file means stock behaviour for that setting.

  /data/g70_long_follow       "t1 t2 t3" or "t1 t2 t3 t4": following time in seconds for each gap setting, closest
                              first. Stock is 1.25 / 1.45 / 1.75 (aggressive / standard / relaxed). With four numbers
                              the distance button cycles through four settings and the cluster shows one to four
                              bars; settings 3 and 4 both use the "relaxed" driving personality for everything else.
                              The car's own cruise held 1.11 s on its closest setting and 1.39 s on the next.
                              The planner adds a fixed 6 m (plus the extra distance below) to time x speed, so
                              1.05 s with 2 m extra measured 1.31 s at 72 mph (route d6).
  /data/g70_long_stop_extra   metres added to the distance kept to a lead, at every speed. The planner aims to stop
                              6 m behind a lead by its own measure; on the first drive the car stopped 0.8 m behind
                              one (the car's own cruise: 3.1 m median over 13 stops).
  /data/g70_long_engage_any   when this file exists, the accelerate / resume toggle engages at the current speed if
                              no set speed is stored yet, as the decelerate / set toggle does. Stock refuses it
                              ("Press Set to Engage").
  /data/g70_long_stop_speed   speed in m/s below which the planner asks for a stop while its lead / cruise plan is
                              braking. Stock is 0.3 m/s (0.7 mph). Twice (routes d5 and db) the car rolled at 1-2 mph
                              for about 5 s against a request of -0.2 to -0.4 m/s2 and stopped 0.8 and 0.7 m behind
                              the lead, with and without the extra distance above; a stop that began at 2.2 mph would
                              have started about 4.5 m back.
  /data/g70_long_cluster_speed  when this file exists, the set speed is taken as the cluster's speed. The cluster reads
                              1.9 % above the wheel-speed value openpilot controls (78.0 against 76.6 mph on routes da
                              and db, on every sample), so a set speed of 78 showed 79-80 on the cluster. The planner
                              scales its target by the measured true / cluster ratio.
  /data/g70_long_gap          written by selfdrived: the current gap setting (0-3) when four are in use.
"""
import os
import time

FOLLOW_FILE = "/data/g70_long_follow"
STOP_EXTRA_FILE = "/data/g70_long_stop_extra"
ENGAGE_ANY_FILE = "/data/g70_long_engage_any"
GAP_FILE = "/data/g70_long_gap"
CLUSTER_SPEED_FILE = "/data/g70_long_cluster_speed"
STOP_SPEED_FILE = "/data/g70_long_stop_speed"
STOP_SPEED_MIN = 0.3
STOP_SPEED_MAX = 1.5
STOP_SPEED_A_TARGET = -0.05   # m/s2: only while the plan is braking

FOLLOW_MIN = 0.7   # with the fixed 6 m plus the extra distance, 0.75 s is about 1.0 s behind the lead at 72 mph
FOLLOW_MAX = 2.5
STOP_EXTRA_MAX = 4.0
CLUSTER_SPEED_MIN_V = 10.0       # m/s
CLUSTER_SPEED_RATIO_MIN = 0.95
CLUSTER_SPEED_MAX_A = 0.3        # m/s2


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


def cluster_speed_enabled(path: str = CLUSTER_SPEED_FILE) -> bool:
  return os.path.exists(path)


class ClusterSpeed:
  """Scales the planner's cruise speed so that the cluster, not the wheel-speed value, reaches the set speed.

  The ratio true / cluster is measured above CLUSTER_SPEED_MIN_V at steady speed and filtered slowly (the cluster speed is whole
  mph or km/h); it is kept between CLUSTER_SPEED_RATIO_MIN and 1, so the car can only go slower than without it."""
  def __init__(self, enabled: bool, alpha: float = 0.005):
    self.enabled = enabled
    self.alpha = alpha
    self.ratio = 1.0

  def update(self, v_cruise: float, v_ego: float, v_ego_cluster: float, a_ego: float) -> float:
    if not self.enabled:
      return v_cruise
    # learn only at steady speed: the cluster value lags while braking (15 against 12.7 mph on route db)
    if v_ego > CLUSTER_SPEED_MIN_V and v_ego_cluster > CLUSTER_SPEED_MIN_V and abs(a_ego) < CLUSTER_SPEED_MAX_A:
      ratio = min(max(v_ego / v_ego_cluster, CLUSTER_SPEED_RATIO_MIN), 1.0)
      self.ratio += self.alpha * (ratio - self.ratio)
    return v_cruise * self.ratio


def read_stop_speed(path: str = STOP_SPEED_FILE) -> float | None:
  try:
    with open(path) as f:
      value = float(f.read().split()[0])
  except (OSError, ValueError, IndexError):
    return None
  if value != value:  # NaN
    return None
  return min(max(value, STOP_SPEED_MIN), STOP_SPEED_MAX)


def early_stop(v_ego: float, a_target: float, stop_speed: float | None) -> bool:
  return stop_speed is not None and bool(v_ego < stop_speed and a_target < STOP_SPEED_A_TARGET)


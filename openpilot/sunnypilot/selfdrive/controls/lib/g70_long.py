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
  /data/g70_long_start        acceleration in m/s2 asked for at once when the lead pulls away from a standstill, until
                              the car is rolling. Stock waits until the plan itself asks for 0.1 m/s2, then ramps
                              from about 0.3 to 0.9 m/s2 over a second, and the car does not move before about 0.9:
                              first movement 1.5-2.1 s after the lead's (routes d6, df), 5-6 m of head start by 2 mph.
                              It starts only behind a lead that is faster than 0.7 m/s and accelerating by more than
                              0.5 m/s2 (a lead creeping forward at 0.7 m/s on route df does not start it), never
                              asks for more than the cruise plan allows, and ends at 1.5 m/s, after 2.5 s, or as
                              soon as the lead is no longer pulling away.
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

START_FILE = "/data/g70_long_start"
START_ACCEL_MIN = 0.5
START_ACCEL_MAX = 1.5
START_EGO_STOPPED = 0.3      # m/s: may begin only below this
START_LEAD_SPEED = 0.7       # m/s
START_LEAD_ACCEL = 0.5       # m/s2
START_MIN_GAP = 3.0          # m
START_CYCLES = 2             # planner cycles (20 Hz) the lead must meet the conditions
START_END_SPEED = 1.5        # m/s: hand back to the plan
START_MAX_T = 2.5            # s
START_LEAD_MARGIN = 0.3      # m/s the lead must stay faster than the car by
START_LEAD_ACCEL_END = -0.3  # m/s2

FOLLOW_MIN = 0.6   # with the fixed 6 m plus the extra distance, 0.69 s is about 0.95 s behind the lead at 70 mph
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
  """The current gap setting for processes other than selfdrived.

  Re-reads the file every `period` s, and at once (at most every `retry` s) when the value it holds disagrees with
  the personality. selfdrived writes the file before it publishes the new personality, so a disagreement means the
  held value is stale: with a 0.5 s period and no retry, going from setting 1 to 4 showed three bars on the cluster
  for a moment before the fourth."""
  def __init__(self, path: str = GAP_FILE, period: float = 0.1, retry: float = 0.02):
    self.path = path
    self.period = period
    self.retry = retry
    self.gap: int | None = None
    self.t = -1e9

  def get(self, personality: int) -> int:
    # falls back to the personality whenever the file is missing or disagrees with it
    now = time.monotonic()
    stale = self.gap is None or gap_to_personality(self.gap) != personality
    if now - self.t > (self.retry if stale else self.period):
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


def read_start_accel(path: str = START_FILE) -> float | None:
  try:
    with open(path) as f:
      value = float(f.read().split()[0])
  except (OSError, ValueError, IndexError):
    return None
  if value != value:  # NaN
    return None
  return min(max(value, START_ACCEL_MIN), START_ACCEL_MAX)


class QuickStart:
  """Asks for a fixed acceleration at once when the lead pulls away from a standstill (see /data/g70_long_start).

  update() returns the acceleration to ask for while it is active, None otherwise."""
  def __init__(self, accel: float | None, dt: float):
    self.accel = accel
    self.dt = dt
    self.count = 0
    self.active = False
    self.t = 0.0

  def update(self, v_ego: float, lead_present: bool, d_rel: float, v_lead: float, a_lead: float, a_cruise: float) -> float | None:
    if self.accel is None:
      return None
    if self.active:
      self.t += self.dt
      if (not lead_present or v_ego > START_END_SPEED or self.t > START_MAX_T or d_rel < START_MIN_GAP or
          v_lead < v_ego + START_LEAD_MARGIN or a_lead < START_LEAD_ACCEL_END or a_cruise <= 0.0):
        self.active = False
        self.count = 0
    else:
      if (lead_present and v_ego < START_EGO_STOPPED and v_lead > START_LEAD_SPEED and a_lead > START_LEAD_ACCEL and
          d_rel > START_MIN_GAP and a_cruise > 0.0):
        self.count += 1
      else:
        self.count = 0
      if self.count >= START_CYCLES:
        self.active = True
        self.t = 0.0
    return min(self.accel, a_cruise) if self.active else None

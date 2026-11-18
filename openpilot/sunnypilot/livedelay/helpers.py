"""
Copyright (c) 2021-, Haibin Wen, sunnypilot, and a number of other contributors.

This file is part of sunnypilot and is licensed under the MIT License.
See the LICENSE.md file in the root directory for more details.
"""
from openpilot.common.params import Params

# dragalpilot (G70 2024): optional steering-delay offset in seconds, read from a one-line text file on the device.
# lagd adds it to the lateralDelay it publishes, so the model plans that much further ahead and the controller
# expects the response that much later. No file, or an unreadable one, means no offset.
LAT_DELAY_OFFSET_FILE = "/data/g70_lat_delay_offset"
LAT_DELAY_OFFSET_MAX = 0.25


def read_lat_delay_offset(path: str = LAT_DELAY_OFFSET_FILE) -> float:
  try:
    with open(path) as f:
      value = float(f.read().strip())
  except (OSError, ValueError):
    return 0.0
  if value != value:  # NaN
    return 0.0
  return min(max(value, 0.0), LAT_DELAY_OFFSET_MAX)


def get_lat_delay(params: Params, stock_lat_delay: float) -> float:
# live learning on: use what lagd publishes.
# off: use the fixed steerActuatorDelay + software delay sum that LagdToggle caches.

  if params.get_bool("LagdToggle"):
    return stock_lat_delay

  return float(params.get("LagdValueCache", return_default=True))

# dragalpilot (G70 2024): optional friction-ramp width in m/s^2, read from a one-line text file on the device.
# The torque controllers ramp the friction term from -friction to +friction over +/- this error; stock is 0.2.
# A wider ramp reacts less to small errors on a straight while keeping the full friction term in curves.
# No file, or an unreadable one, means the stock value.
FRICTION_THRESHOLD_FILE = "/data/g70_friction_threshold"
FRICTION_THRESHOLD_MAX = 0.6


def read_friction_threshold(default: float, path: str = FRICTION_THRESHOLD_FILE) -> float:
  try:
    with open(path) as f:
      value = float(f.read().strip())
  except (OSError, ValueError):
    return default
  if value != value:  # NaN
    return default
  return min(max(value, default), FRICTION_THRESHOLD_MAX)

# dragalpilot (G70 2024): optional smoothing of the model's steering request, in seconds, read from a one-line
# text file on the device. modeld low-passes desiredCurvature with this time constant and, as upstream intends
# for LAT_SMOOTH_SECONDS, both modeld and controlsd add it to the steering delay they plan and compare with.
# No file, or an unreadable one, means the stock value.
LAT_SMOOTH_FILE = "/data/g70_lat_smooth"
LAT_SMOOTH_MAX = 0.3


def read_lat_smooth_seconds(default: float, path: str = LAT_SMOOTH_FILE) -> float:
  try:
    with open(path) as f:
      value = float(f.read().split()[0])
  except (OSError, ValueError, IndexError):
    return default
  if value != value:  # NaN
    return default
  return min(max(value, 0.0), LAT_SMOOTH_MAX)


# The same file may carry two more numbers, "seconds v_lo v_hi" (speeds in m/s): no smoothing below v_lo, the full
# value above v_hi, linear in between. On the car, 0.2 s at all speeds calmed the wheel on the highway and made
# the steering busier below about 10 mph. One number, or unusable speeds, means the same value at every speed.
def read_lat_smooth_speeds(path: str = LAT_SMOOTH_FILE) -> tuple[float, float]:
  try:
    with open(path) as f:
      parts = f.read().split()
    v_lo, v_hi = float(parts[1]), float(parts[2])
  except (OSError, ValueError, IndexError):
    return 0.0, 0.0
  if v_lo != v_lo or v_hi != v_hi or v_lo < 0.0 or v_hi <= v_lo:
    return 0.0, 0.0
  return v_lo, v_hi


# A fourth number sets how much further ahead the model aims (and how much delay controlsd adds) at full
# smoothing: "seconds v_lo v_hi lookahead". Stock ties this to the filter time. Offline, on the plans logged in
# route c1, aiming further ahead made the request 10-15 % larger at 0.3-0.7 Hz; a 0.3 s filter with 0.2 s of
# look-ahead left that band unchanged and removed more frame-to-frame jitter, at 9-15 degrees of lag. No fourth
# number, or an unusable one, means the filter time (the previous behaviour).
def read_lat_smooth_lookahead(default: float, path: str = LAT_SMOOTH_FILE) -> float:
  try:
    with open(path) as f:
      value = float(f.read().split()[3])
  except (OSError, ValueError, IndexError):
    return default
  if value != value:  # NaN
    return default
  return min(max(value, 0.0), LAT_SMOOTH_MAX)


def lat_smooth_at(v_ego: float, seconds: float, v_lo: float, v_hi: float) -> float:
  if v_hi <= v_lo:
    return seconds
  return seconds * min(max((v_ego - v_lo) / (v_hi - v_lo), 0.0), 1.0)

# dragalpilot (G70 2024): optional fixed steering delay in seconds, read from a one-line text file on the device.
# With the offset above, lagd's own estimate crept up on every drive (0.174 s to 0.233 s over nine drives), so
# the published delay moved without any setting changing. When this file exists, lagd publishes exactly this
# value as lateralDelay and ignores the offset; the learner keeps running and lateralDelayEstimate stays raw.
# No file, or an unreadable one, means the learned value (plus the offset, if set).
LAT_DELAY_FIXED_FILE = "/data/g70_lat_delay_fixed"
LAT_DELAY_FIXED_MIN = 0.1
LAT_DELAY_FIXED_MAX = 0.5


def read_lat_delay_fixed(path: str = LAT_DELAY_FIXED_FILE) -> float | None:
  try:
    with open(path) as f:
      value = float(f.read().strip())
  except (OSError, ValueError):
    return None
  if value != value:  # NaN
    return None
  return min(max(value, LAT_DELAY_FIXED_MIN), LAT_DELAY_FIXED_MAX)

# dragalpilot (G70 2024): optional feedback gains for the upstream (v1) torque controller, read from a one-line
# text file "kp ki". Stock is 0.8 / 0.15; LatControlTorqueV0 uses 1.0 / 0.3. On this car v1 kept the wheel calmer
# but had about 30 % more lane motion at 0.2-0.45 Hz than v0, and v0 rang at 0.8 Hz once request smoothing was
# added. kp replaces only the high-speed end of the speed schedule (30 m/s and up, blending in from 15 m/s).
# No file, or an unreadable one, means the stock gains.
V1_GAINS_FILE = "/data/g70_v1_gains"
V1_KP_RANGE = (0.5, 1.2)
V1_KI_RANGE = (0.05, 0.4)


def read_v1_gains(default_kp: float, default_ki: float, path: str = V1_GAINS_FILE) -> tuple[float, float]:
  try:
    with open(path) as f:
      parts = f.read().split()
    kp, ki = float(parts[0]), float(parts[1])
  except (OSError, ValueError, IndexError):
    return default_kp, default_ki
  if kp != kp or ki != ki:  # NaN
    return default_kp, default_ki
  return min(max(kp, V1_KP_RANGE[0]), V1_KP_RANGE[1]), min(max(ki, V1_KI_RANGE[0]), V1_KI_RANGE[1])


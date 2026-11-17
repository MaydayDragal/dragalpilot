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
      value = float(f.read().strip())
  except (OSError, ValueError):
    return default
  if value != value:  # NaN
    return default
  return min(max(value, 0.0), LAT_SMOOTH_MAX)

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

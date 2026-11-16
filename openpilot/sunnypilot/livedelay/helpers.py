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

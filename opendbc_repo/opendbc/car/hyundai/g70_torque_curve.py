"""Genesis G70 2024: optional non-linear torque curve for the torque lateral controller.

The standard controller turns a lateral acceleration request into torque with one number (latAccelFactor), a straight
line through zero. In steady driving this car needs less torque per m/s^2 near the centre than further out (drive logs,
about 48,000 steady samples above 30 mph: slope near the centre about 0.45 of the slope beyond 0.25 m/s^2).

/data/g70_lat_torque_curve holds "centre_gain knee [width]":
  centre_gain  slope of the curve inside the knee, as a share of the slope outside it (0.2 .. 1.0; fitted 0.45)
  knee         lateral acceleration where the slope changes (m/s^2, 0.05 .. 1.0; fitted 0.25)
  width        how gradually it changes (m/s^2, default 0.08)
Without the file, or if it cannot be read, the curve is off and the port behaves as before. The file is read when the
controller starts (each drive).

The request is remapped to an "effective" lateral acceleration and then divided by latAccelFactor as usual, so the
factor keeps its meaning for everything beyond the knee. Everything the controller asks for passes through the curve,
the friction term included: with a centre gain below 1 the friction push near zero shrinks by the same share.
"""
import numpy as np

CURVE_FILE = "/data/g70_lat_torque_curve"
DEFAULT_CENTRE_GAIN = 0.45
DEFAULT_KNEE = 0.25
DEFAULT_WIDTH = 0.08
STEP = 0.005
MAX_LAT_ACCEL = 20.0


def read_curve(path: str = CURVE_FILE):
  try:
    with open(path) as f:
      v = f.read().split()
  except OSError:
    return None
  try:
    gain = float(v[0]) if len(v) > 0 else DEFAULT_CENTRE_GAIN
    knee = float(v[1]) if len(v) > 1 else DEFAULT_KNEE
    width = float(v[2]) if len(v) > 2 else DEFAULT_WIDTH
  except ValueError:
    return None
  if not all(np.isfinite([gain, knee, width])):
    return None
  return float(np.clip(gain, 0.2, 1.0)), float(np.clip(knee, 0.05, 1.0)), float(np.clip(width, 0.02, 0.5))


def curve_table(gain: float, knee: float, width: float = DEFAULT_WIDTH):
  """|lateral acceleration| -> effective |lateral acceleration|, strictly increasing, slope `gain` at zero and 1 far out."""
  x = np.arange(0.0, MAX_LAT_ACCEL + STEP, STEP)
  slope = gain + (1.0 - gain) * 0.5 * (1.0 + np.tanh((x - knee) / width))
  y = np.concatenate(([0.0], np.cumsum((slope[1:] + slope[:-1]) * 0.5 * STEP)))
  return x, y


class TorqueCurve:
  def __init__(self, gain: float, knee: float, width: float = DEFAULT_WIDTH):
    self.x, self.y = curve_table(gain, knee, width)

  def torque_from_lateral_accel(self, lateral_acceleration: float, torque_params) -> float:
    la = float(lateral_acceleration)
    eff = float(np.interp(abs(la), self.x, self.y))
    return float(np.sign(la) * eff / float(torque_params.latAccelFactor))

  def lateral_accel_from_torque(self, torque: float, torque_params) -> float:
    eff = float(torque) * float(torque_params.latAccelFactor)
    return float(np.sign(eff) * np.interp(abs(eff), self.y, self.x))

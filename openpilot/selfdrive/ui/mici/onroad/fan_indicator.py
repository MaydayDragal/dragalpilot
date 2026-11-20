import os

import pyray as rl
from openpilot.cereal import log
from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.text_measure import measure_text_cached
from openpilot.system.ui.widgets import Widget

# dragalpilot: optional fan readout in the top right corner of the driving screen. It shows the fan setting the
# device asks for (deviceState.fanSpeedPercentDesired, 0-100 %), not a measured speed. On when this file exists.
FAN_FILE = "/data/g70_ui_fan"

VALUE_SIZE = 36
LABEL_SIZE = 20
RIGHT_INSET = 20
TOP_INSET = 12
LABEL_GAP = 7
FAN_MIN_WIDTH_WITH_SET_SPEED = 400  # px of camera view below which the readout gives way to the set speed


def fan_indicator_enabled(path: str = FAN_FILE) -> bool:
  return os.path.exists(path)


class FanIndicator(Widget):
  def __init__(self):
    super().__init__()
    self._enabled = fan_indicator_enabled()
    self._font_value = gui_app.font(FontWeight.BOLD)
    self._font_label = gui_app.font(FontWeight.SEMI_BOLD)
    self._alpha_filter = FirstOrderFilter(0.0, 0.05, 1 / gui_app.target_fps)
    self._should_draw = True

  def set_should_draw(self, should_draw: bool):
    self._should_draw = should_draw

  def _render(self, rect: rl.Rectangle) -> None:
    if not self._enabled:
      return

    sm = ui_state.sm
    if sm.recv_frame['deviceState'] < ui_state.started_frame:
      self._alpha_filter.x = 0.0
      return

    # hidden under alerts, and when the caller says the corner is taken
    alpha = self._alpha_filter.update(self._should_draw and sm['selfdriveState'].alertSize == log.SelfdriveState.AlertSize.none)
    if alpha < 1e-2:
      return

    value = f"{int(sm['deviceState'].fanSpeedPercentDesired)}%"
    label = "FAN"
    value_width = measure_text_cached(self._font_value, value, VALUE_SIZE).x
    label_width = measure_text_cached(self._font_label, label, LABEL_SIZE).x

    right = rect.x + rect.width - RIGHT_INSET
    top = rect.y + TOP_INSET
    value_pos = rl.Vector2(right - value_width, top)
    # the label sits on the value's baseline
    label_pos = rl.Vector2(right - value_width - LABEL_GAP - label_width, top + (VALUE_SIZE - LABEL_SIZE) * 0.78)
    rl.draw_text_ex(self._font_label, label, label_pos, LABEL_SIZE, 0, rl.Color(255, 255, 255, round(255 * 0.6 * alpha)))
    rl.draw_text_ex(self._font_value, value, value_pos, VALUE_SIZE, 0, rl.Color(255, 255, 255, round(255 * 0.9 * alpha)))

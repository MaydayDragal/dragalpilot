import math

import numpy as np

from openpilot.cereal import log
from opendbc.car.structs import car
from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR as HYUNDAI
from opendbc.car.vehicle_model import VehicleModel
from openpilot.common.realtime import DT_CTRL
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.car.helpers import convert_to_capnp
from openpilot.sunnypilot.selfdrive.car import interfaces as sunnypilot_interfaces
from openpilot.sunnypilot.selfdrive.controls.lib.latcontrol_torque_v0 import LatControlTorque as LatControlTorqueV0

G70 = HYUNDAI.GENESIS_G70_2024
OTHERS = (HYUNDAI.GENESIS_G70, HYUNDAI.HYUNDAI_SONATA, HYUNDAI.HYUNDAI_IONIQ_5)
V = 30.0
LAT_DELAY = 0.2


def make(car_name, deadzone_deg=None):
  CarInterface = interfaces[car_name]
  CP = CarInterface.get_non_essential_params(car_name)
  if deadzone_deg is not None:
    CP.lateralTuning.torque.steeringAngleDeadzoneDeg = deadzone_deg
  CP_SP = CarInterface.get_non_essential_params_sp(CP, car_name)
  CI = CarInterface(CP, CP_SP)
  sunnypilot_interfaces.setup_interfaces(CI)
  CP_SP = convert_to_capnp(CP_SP)
  return LatControlTorqueV0(CP.as_reader(), CP_SP.as_reader(), CI, DT_CTRL), VehicleModel(CP), CP


def car_state(angle_deg=0.0, v=V):
  CS = car.CarState.new_message()
  CS.vEgo = v
  CS.steeringAngleDeg = angle_deg
  CS.steeringPressed = False
  return CS


def step(controller, VM, active, curvature, angle_deg=0.0, v=V):
  params = log.VehicleParameters.new_message()
  return controller.update(active, car_state(angle_deg, v), VM, params, False, curvature, None, False, LAT_DELAY)[2]


class TestLatControlTorqueV0G70(OpenpilotTestCase):
  def test_deadzone_only_for_g70_2024(self):
    _, _, CP = make(G70)
    self.assertAlmostEqual(CP.lateralTuning.torque.steeringAngleDeadzoneDeg, 0.4, places=6)  # float32 field
    for car_name in OTHERS:
      _, _, CP = make(car_name)
      self.assertEqual(CP.lateralTuning.torque.steeringAngleDeadzoneDeg, 0.0, car_name)

  def test_other_cars_request_unfiltered(self):
    # without the low-pass, V0's setpoint equals the current request (lat_delay * jerk + expected == fut)
    for car_name in OTHERS:
      controller, VM, _ = make(car_name)
      step(controller, VM, True, 0.0)
      lac_log = step(controller, VM, True, 0.001)
      self.assertAlmostEqual(lac_log.desiredLateralAccel, 0.001 * V ** 2, places=6, msg=car_name)  # float32 log fields

  def test_g70_request_first_order_lowpass(self):
    controller, VM, _ = make(G70)
    alpha = DT_CTRL / (1 / (2 * math.pi * 2.0) + DT_CTRL)
    c0, c1 = 0.0005, 0.0015
    lac_log = step(controller, VM, True, c0)  # first value initializes the filter: no ramp from 0
    self.assertAlmostEqual(lac_log.desiredLateralAccel, c0 * V ** 2, places=6)
    for n in range(1, 101):
      lac_log = step(controller, VM, True, c1)
      expected = c1 + (c0 - c1) * (1 - alpha) ** n
      self.assertAlmostEqual(lac_log.desiredLateralAccel, expected * V ** 2, places=6, msg=f"cycle {n}")
    # 2 Hz first order: about 63% of a step after one time constant (80 ms), > 99% after 0.4 s
    self.assertGreater(lac_log.desiredLateralAccel, 0.999 * c1 * V ** 2)

  def test_g70_filter_tracks_while_inactive(self):
    controller, VM, _ = make(G70)
    for _ in range(100):
      step(controller, VM, False, 0.0)
    for _ in range(300):
      lac_log = step(controller, VM, False, 0.001)
    self.assertFalse(lac_log.active)
    lac_log = step(controller, VM, True, 0.001)  # engagement: no step from a stale filter state
    self.assertAlmostEqual(lac_log.desiredLateralAccel, 0.001 * V ** 2, places=6)

  def test_g70_filter_updates_while_inactive_across_reengagement(self):
    # the filter must keep tracking the request while lateral control is off (controlsd calls reset() and update(False, ...)
    # every inactive cycle), so re-engagement starts from the current request instead of the value held at disengagement
    controller, VM, _ = make(G70)
    for _ in range(100):
      step(controller, VM, True, 0.0005)
    for _ in range(300):
      controller.reset()
      step(controller, VM, False, 0.001)
    lac_log = step(controller, VM, True, 0.001)
    self.assertAlmostEqual(lac_log.desiredLateralAccel, 0.001 * V ** 2, places=6)

  def test_g70_friction_deadzone(self):
    # zero request and roll: feedforward f is the friction term alone. 0.4 deg of steering at 30 m/s maps to a lateral-accel
    # deadzone; errors inside it give no friction torque, errors outside it do.
    dz_angle = 0.4
    for angle, inside in ((0.5 * dz_angle, True), (-0.5 * dz_angle, True), (2.0 * dz_angle, False), (-2.0 * dz_angle, False)):
      g70, VM, _ = make(G70)
      ref, VM_ref, _ = make(G70, deadzone_deg=0.0)
      lac_log = step(g70, VM, True, 0.0, angle)
      lac_ref = step(ref, VM_ref, True, 0.0, angle)
      self.assertAlmostEqual(lac_log.error, lac_ref.error, places=12)
      self.assertNotEqual(lac_ref.f, 0.0)
      if inside:
        self.assertEqual(lac_log.f, 0.0, f"angle {angle}")
      else:
        self.assertEqual(lac_log.f, lac_ref.f, f"angle {angle}")
        self.assertEqual(np.sign(lac_log.f), np.sign(lac_log.error))

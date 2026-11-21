import os
from opendbc.car.crc import CRC8J1850, mk_crc8_fun
from opendbc.car.hyundai.values import CAR, HyundaiFlags

from opendbc.sunnypilot.car.hyundai.escc import EnhancedSmartCruiseControl
from opendbc.sunnypilot.car.hyundai.lead_data_ext import CanLeadData

hyundai_checksum = mk_crc8_fun(CRC8J1850, init_crc=0xFD, xor_out=0xDF)


def create_lkas11(packer, frame, CP, apply_torque, steer_req,
                  torque_fault, lkas11, sys_warning, sys_state, enabled,
                  left_lane, right_lane,
                  left_lane_depart, right_lane_depart,
                  lkas_icon):
  values = {s: lkas11[s] for s in [
    "CF_Lkas_LdwsActivemode",
    "CF_Lkas_LdwsSysState",
    "CF_Lkas_SysWarning",
    "CF_Lkas_LdwsLHWarning",
    "CF_Lkas_LdwsRHWarning",
    "CF_Lkas_HbaLamp",
    "CF_Lkas_FcwBasReq",
    "CF_Lkas_HbaSysState",
    "CF_Lkas_FcwOpt",
    "CF_Lkas_HbaOpt",
    "CF_Lkas_FcwSysState",
    "CF_Lkas_FcwCollisionWarning",
    "CF_Lkas_FusionState",
    "CF_Lkas_FcwOpt_USM",
    "CF_Lkas_LdwsOpt_USM",
  ]}
  values["CF_Lkas_LdwsSysState"] = sys_state
  values["CF_Lkas_SysWarning"] = 3 if sys_warning else 0
  values["CF_Lkas_LdwsLHWarning"] = left_lane_depart
  values["CF_Lkas_LdwsRHWarning"] = right_lane_depart
  values["CR_Lkas_StrToqReq"] = apply_torque
  values["CF_Lkas_ActToi"] = steer_req
  values["CF_Lkas_ToiFlt"] = torque_fault  # seems to allow actuation on CR_Lkas_StrToqReq
  values["CF_Lkas_MsgCount"] = frame % 0x10

  if CP.carFingerprint in (CAR.HYUNDAI_SONATA, CAR.HYUNDAI_PALISADE, CAR.KIA_NIRO_EV, CAR.KIA_NIRO_HEV_2021, CAR.KIA_NIRO_PHEV_2022, CAR.HYUNDAI_SANTA_FE,
                           CAR.HYUNDAI_IONIQ_EV_2020, CAR.HYUNDAI_IONIQ_PHEV, CAR.KIA_SELTOS, CAR.HYUNDAI_ELANTRA_2021, CAR.GENESIS_G70_2020,
                           CAR.HYUNDAI_ELANTRA_HEV_2021, CAR.HYUNDAI_SONATA_HYBRID, CAR.HYUNDAI_KONA_EV, CAR.HYUNDAI_KONA_HEV, CAR.HYUNDAI_KONA_EV_2022,
                           CAR.HYUNDAI_SANTA_FE_2022, CAR.KIA_K5_2021, CAR.HYUNDAI_IONIQ_HEV_2022, CAR.HYUNDAI_SANTA_FE_HEV_2022,
                           CAR.HYUNDAI_SANTA_FE_PHEV_2022, CAR.KIA_STINGER_2022, CAR.KIA_K5_HEV_2020, CAR.KIA_CEED, CAR.KIA_CEED_PHEV,
                           CAR.HYUNDAI_AZERA_6TH_GEN, CAR.HYUNDAI_AZERA_HEV_6TH_GEN, CAR.HYUNDAI_CUSTIN_1ST_GEN, CAR.HYUNDAI_KONA_2022,
                           CAR.KIA_CEED_PHEV_2022_NON_SCC, CAR.HYUNDAI_KONA_EV_NON_SCC, CAR.HYUNDAI_ELANTRA_2022_NON_SCC,
                           CAR.GENESIS_G70_2021_NON_SCC, CAR.KIA_SELTOS_2023_NON_SCC, CAR.HYUNDAI_BAYON_1ST_GEN_NON_SCC,
                           CAR.GENESIS_G70_2024):
    values["CF_Lkas_LdwsActivemode"] = int(left_lane) + (int(right_lane) << 1)
    values["CF_Lkas_LdwsOpt_USM"] = 2

    # FcwOpt_USM 5 = Orange blinking car + lanes
    # FcwOpt_USM 4 = Orange car + lanes
    # FcwOpt_USM 3 = Green blinking car + lanes
    # FcwOpt_USM 2 = Green car + lanes
    # FcwOpt_USM 1 = White car + lanes
    # FcwOpt_USM 0 = No car + lanes
    values["CF_Lkas_FcwOpt_USM"] = lkas_icon

    # SysWarning 4 = keep hands on wheel
    # SysWarning 5 = keep hands on wheel (red)
    # SysWarning 6 = keep hands on wheel (red) + beep
    # Note: the warning is hidden while the blinkers are on
    values["CF_Lkas_SysWarning"] = 4 if sys_warning else 0

  # Likely cars lacking the ability to show individual lane lines in the dash
  elif CP.carFingerprint in (CAR.KIA_OPTIMA_G4, CAR.KIA_OPTIMA_G4_FL, CAR.HYUNDAI_KONA_NON_SCC):
    # SysWarning 4 = keep hands on wheel + beep
    values["CF_Lkas_SysWarning"] = 4 if sys_warning else 0

    # SysState 0 = no icons
    # SysState 1-2 = white car + lanes
    # SysState 3 = green car + lanes, green steering wheel
    # SysState 4 = green car + lanes
    values["CF_Lkas_LdwsSysState"] = lkas_icon
    values["CF_Lkas_LdwsOpt_USM"] = 2  # non-2 changes above SysState definition

    # these have no effect
    values["CF_Lkas_LdwsActivemode"] = 0
    values["CF_Lkas_FcwOpt_USM"] = 0

  elif CP.carFingerprint in (CAR.HYUNDAI_GENESIS, CAR.KIA_OPTIMA_H):
    # This field is actually LdwsActivemode
    # Genesis and Optima fault when forwarding while engaged
    values["CF_Lkas_LdwsActivemode"] = 2

  dat = packer.make_can_msg("LKAS11", 0, values)[1]

  if CP.flags & HyundaiFlags.CHECKSUM_CRC8:
    # CRC Checksum as seen on 2019 Hyundai Santa Fe
    dat = dat[:6] + dat[7:8]
    checksum = hyundai_checksum(dat)
  elif CP.flags & HyundaiFlags.CHECKSUM_6B:
    # Checksum of first 6 Bytes, as seen on 2018 Kia Sorento
    checksum = sum(dat[:6]) % 256
  else:
    # Checksum of first 6 Bytes and last Byte as seen on 2018 Kia Stinger
    checksum = (sum(dat[:6]) + dat[7]) % 256

  values["CF_Lkas_Chksum"] = checksum

  return packer.make_can_msg("LKAS11", 0, values)


def create_clu11(packer, frame, clu11, button, CP):
  values = {s: clu11[s] for s in [
    "CF_Clu_CruiseSwState",
    "CF_Clu_CruiseSwMain",
    "CF_Clu_SldMainSW",
    "CF_Clu_ParityBit1",
    "CF_Clu_VanzDecimal",
    "CF_Clu_Vanz",
    "CF_Clu_SPEED_UNIT",
    "CF_Clu_DetentOut",
    "CF_Clu_RheostatLevel",
    "CF_Clu_CluInfo",
    "CF_Clu_AmpInfo",
    "CF_Clu_AliveCnt1",
  ]}
  values["CF_Clu_CruiseSwState"] = button
  values["CF_Clu_AliveCnt1"] = frame % 0x10
  # send buttons to camera on camera-scc based cars
  bus = 2 if CP.flags & HyundaiFlags.CAMERA_SCC else 0
  return packer.make_can_msg("CLU11", bus, values)


def create_lfahda_mfc(packer, enabled, lfa_icon):
  values = {
    "LFA_Icon_State": lfa_icon,
  }
  return packer.make_can_msg("LFAHDA_MFC", 0, values)


# LKAS12 (0x53E, camera, 10 Hz, 8 bytes, no counter or checksum) carries the Driver Attention Warning status.
# On the 2024 G70 the status counts 5..1 and reads 6, with bit 44 set, while the cluster shows "consider taking a break".
# Bit 43 (seen for a few seconds while the camera starts, with status 5) and bits 45-47 are passed through untouched.
LKAS12_DAW_WARNING = 6
LKAS12_DAW_WARNING_BIT = 0x2  # bit 44, i.e. bit 1 of CF_Lkas12_DawWarning (43|5)


def lkas12_daw_filter(lkas12: dict, last_level: int) -> tuple[dict, int]:
  """Returns the camera's LKAS12 values with the DAW warning replaced by the last normal attention level."""
  values = dict(lkas12)
  status = int(values["CF_LkasDawStatus"])
  flags = int(values["CF_Lkas12_DawWarning"])
  if status == LKAS12_DAW_WARNING or flags & LKAS12_DAW_WARNING_BIT:
    if status == LKAS12_DAW_WARNING:
      values["CF_LkasDawStatus"] = last_level
    values["CF_Lkas12_DawWarning"] = flags & ~LKAS12_DAW_WARNING_BIT
  else:
    last_level = status
  return values, last_level


# The camera's LKAS11 carries CF_Lkas_FcwBasReq (byte 1 bit 7), which create_lkas11 copies to the car. On the
# G70 2024 the camera sets it for the 4 s of a Driver Attention Warning (routes c4 and c6: 800 frames, all of them
# inside or within 0.1 s of the LKAS12 warning), and the attention chime still played with the LKAS12 warning
# removed. The bit is cleared while the camera's LKAS12 shows the warning. LKAS12 is a 10 Hz message and the bit
# leads it by up to 0.1 s, so a newly set bit is also held back for LKAS11_BASREQ_HOLD_FRAMES; if no attention
# warning has appeared by then it is passed on unchanged, in case the camera uses it for something else.
LKAS11_BASREQ_HOLD_FRAMES = 20  # 0.2 s at 100 Hz
LKAS11_BASREQ_DAW_LATCHED = -1


def lkas11_daw_filter(lkas11: dict, lkas12: dict, state: int) -> tuple[dict, int]:
  """Returns the camera's LKAS11 values with CF_Lkas_FcwBasReq cleared during a Driver Attention Warning, and the new state.

  state: 0 bit not set; n > 0 frames since the bit was set without a warning; LKAS11_BASREQ_DAW_LATCHED once the
  warning was seen while the bit was set (cleared until the camera drops the bit)."""
  if not int(lkas11["CF_Lkas_FcwBasReq"]):
    return lkas11, 0
  daw = bool(lkas12) and (int(lkas12["CF_LkasDawStatus"]) == LKAS12_DAW_WARNING or bool(int(lkas12["CF_Lkas12_DawWarning"]) & LKAS12_DAW_WARNING_BIT))
  if daw or state == LKAS11_BASREQ_DAW_LATCHED:
    state = LKAS11_BASREQ_DAW_LATCHED
  else:
    state += 1
    if state > LKAS11_BASREQ_HOLD_FRAMES:
      return lkas11, state
  values = dict(lkas11)
  values["CF_Lkas_FcwBasReq"] = 0
  return values, state


def create_lkas12(packer, values):
  return packer.make_can_msg("LKAS12", 0, values)


# dragalpilot (G70 2024, openpilot longitudinal). Two optional behaviours, each on when its file exists:
#
# /data/g70_long_engage_main: turning cruise on with the main button also engages at the current speed, as the
#   car's own cruise does. Only above LONG_ENGAGE_MAIN_MIN_SPEED; below it the set / resume toggles engage as before.
#
# /data/g70_long_no_lead_alert: the camera announces a lead that drives away from a standstill in LKAS12 bit 32
#   (bit 0 of CF_Lkas_TsrAddinfo_Display, set for 4.1 s). On routes d5 and d6 it was set twice in 69,150 frames,
#   both times standing with the lead moving off at 6-7 mph, and never on three drives with the car's own cruise.
#   With openpilot longitudinal the car restarts by itself, so the bit is cleared in the LKAS12 that is re-sent.
LONG_ENGAGE_MAIN_FILE = "/data/g70_long_engage_main"
LONG_NO_LEAD_ALERT_FILE = "/data/g70_long_no_lead_alert"
LONG_ENGAGE_MAIN_MIN_SPEED = 2.2  # m/s, about 5 mph
LKAS12_LEAD_DEPARTURE_BIT = 0x1


def long_engage_main_enabled(path: str = LONG_ENGAGE_MAIN_FILE) -> bool:
  return os.path.exists(path)


def long_no_lead_alert_enabled(path: str = LONG_NO_LEAD_ALERT_FILE) -> bool:
  return os.path.exists(path)


def lkas12_lead_departure_filter(lkas12: dict) -> dict:
  """Returns the camera's LKAS12 values with the lead-departure announcement cleared."""
  values = dict(lkas12)
  values["CF_Lkas_TsrAddinfo_Display"] = int(values["CF_Lkas_TsrAddinfo_Display"]) & ~LKAS12_LEAD_DEPARTURE_BIT
  return values


# SCC11 (0x420, camera, 50 Hz, 8 bytes, rolling AliveCounterACC, no checksum). SCCInfoDisplay = 4 makes the cluster
# show "Use switch or pedal to accelerate" while cruise holds the car at a stop. On the G70 2024 with stock
# longitudinal the panda blocks the camera's copy and the car controller re-sends each frame once. The frame is
# unchanged unless /data/g70_scc11_filter exists, in which case SCCInfoDisplay 4 is sent as 0. openpilot itself
# keeps reading the camera's original (cruiseState.standstill). Every signal of the DBC message is re-packed; the
# 15 signals cover all 64 bits (checked on 294,043 logged frames, tools/drive-eval/scc11_roundtrip.py).
SCC11_INFO_STANDSTILL = 4
SCC11_FILTER_FILE = "/data/g70_scc11_filter"


def scc11_filter_enabled(path: str = SCC11_FILTER_FILE) -> bool:
  return os.path.exists(path)


def scc11_info_filter(scc11: dict) -> dict:
  """Returns the camera's SCC11 values with the standstill prompt (SCCInfoDisplay 4) cleared."""
  values = dict(scc11)
  if int(values["SCCInfoDisplay"]) == SCC11_INFO_STANDSTILL:
    values["SCCInfoDisplay"] = 0
  return values


def create_scc11_passthrough(packer, values):
  return packer.make_can_msg("SCC11", 0, values)


# SCC14 (0x389, openpilot longitudinal): see get_scc14_values below.
SCC14_COUNTER_FILE = "/data/g70_long_scc14_counter"
SCC14_COUNTER = os.path.exists(SCC14_COUNTER_FILE)

# MDPS12 (0x251, steering unit, 100 Hz, 8 bytes) to the camera, after sunnypilot's g70-2024-new branch (camera_scc.py).
# On the G70 2024 the panda blocks the car's copy on its way to the camera (bus 2) and the car controller sends each
# frame there itself with a new counter and checksum. Unchanged otherwise, unless /data/g70_cam_mdps12 exists: then
# CF_Mdps_ToiActive is sent as 0 and CF_Mdps_ToiUnavail as 1, so the camera takes steering assist as unavailable and
# does not start its hands-off sequence ("grasp not detected", then the driving speed limit). Blocking the camera's
# HDA11_MFC, as this branch has done so far, only keeps that sequence off the cluster. openpilot keeps reading the
# steering unit's own message on bus 0. Checksum: CRC8 over the frame without byte 3; it reproduces byte 3 of every
# logged frame from the steering unit (tools/drive-eval/mdps12_check.py). Bits 32-34 are always set by the steering
# unit and are in no upstream signal; CF_Mdps_Rsv32 carries them so the unchanged re-send is bit-exact.
CAM_MDPS12_FILE = "/data/g70_cam_mdps12"


def cam_mdps12_spoof_enabled(path: str = CAM_MDPS12_FILE) -> bool:
  return os.path.exists(path)


def create_camera_mdps12(packer, frame, CP, mdps12: dict, spoof: bool):
  values = dict(mdps12)
  if spoof:
    values["CF_Mdps_ToiActive"] = 0
    values["CF_Mdps_ToiUnavail"] = 1
    values["CF_Mdps_Rsv32"] = 0  # as g70-2024-new sends it; the steering unit itself always sends 7 here
  values["CF_Mdps_MsgCount2"] = frame % 0x100
  values["CF_Mdps_Chksum2"] = 0
  dat = packer.make_can_msg("MDPS12", 2, values)[1]
  payload = dat[:3] + dat[4:]
  values["CF_Mdps_Chksum2"] = hyundai_checksum(payload) if CP.flags & HyundaiFlags.CHECKSUM_CRC8 else sum(payload) % 256
  return packer.make_can_msg("MDPS12", 2, values)


def create_acc_commands(packer, enabled, accel, upper_jerk, idx, lead_data: CanLeadData,
                        hud_control, set_speed, stopping, long_override, use_fca, CP,
                        main_cruise_enabled, tuning, ESCC: EnhancedSmartCruiseControl | None = None):
  commands = []

  def get_scc11_values():
    return {
      "MainMode_ACC": 1 if main_cruise_enabled else 0,
      "TauGapSet": hud_control.leadDistanceBars,
      "VSetDis": set_speed if enabled else 0,
      "AliveCounterACC": idx % 0x10,
      "ObjValid": int(lead_data.lead_visible), # close lead makes controls tighter
      "ACC_ObjStatus": int(lead_data.lead_visible), # close lead makes controls tighter
      "ACC_ObjLatPos": 0,
      "ACC_ObjRelSpd": lead_data.lead_rel_speed,
      "ACC_ObjDist": int(lead_data.lead_distance), # close lead makes controls tighter
    }

  def get_scc12_values():
    scc12_values = {
      "ACCMode": 2 if enabled and long_override else 1 if enabled else 0,
      "StopReq": 1 if tuning.stopping else 0,
      "aReqRaw": tuning.desired_accel,
      "aReqValue": tuning.actual_accel,  # stock ramps up and down respecting jerk limit until it reaches aReqRaw
      "CR_VSM_Alive": idx % 0xF,
    }

    # show AEB disabled indicator on dash with SCC12 if not sending FCA messages.
    # these signals also prevent a TCS fault on non-FCA cars with alpha longitudinal
    if not use_fca:
      scc12_values["CF_VSM_ConfMode"] = 1
      scc12_values["AEB_Status"] = 1 # AEB disabled

    # Since we have ESCC available, we can update SCC12 with ESCC values.
    if ESCC and ESCC.enabled:
      ESCC.update_scc12(scc12_values)

    return scc12_values

  def calculate_scc12_checksum(values):
    scc12_dat = packer.make_can_msg("SCC12", 0, values)[1]
    values["CR_VSM_ChkSum"] = 0x10 - sum(sum(divmod(i, 16)) for i in scc12_dat) % 0x10
    return values

  def get_scc14_values():
    scc14_values = {
      "ComfortBandUpper": tuning.comfort_band_upper, # stock usually is 0 but sometimes uses higher values
      "ComfortBandLower": tuning.comfort_band_lower, # stock usually is 0 but sometimes uses higher values
      "JerkUpperLimit": tuning.jerk_upper, # stock usually is 1.0 but sometimes uses higher values
      "JerkLowerLimit": tuning.jerk_lower, # stock usually is 0.5 but sometimes uses higher values
      "ACCMode": 2 if enabled and long_override else 1 if enabled else 4, # stock will always be 4 instead of 0 after first disengage
      "ObjGap": lead_data.object_gap, # 5: >30, m, 4: 25-30 m, 3: 20-25 m, 2: < 20 m, 0: no lead
      "ObjDistStat": lead_data.object_rel_gap,
    }
    # dragalpilot: rolling counter and checksum as sunnypilot's g70-2024-new branch sends them, when
    # /data/g70_long_scc14_counter exists (read once at import). Without the file the two fields stay 0 as before.
    if SCC14_COUNTER and CP.carFingerprint == CAR.GENESIS_G70_2024:
      scc14_values["AliveCounter"] = idx % 0xF
      scc14_dat = packer.make_can_msg("SCC14", 0, scc14_values)[1]
      scc14_values["Checksum"] = (0x10 - sum(sum(divmod(i, 16)) for i in scc14_dat) % 0x10) % 0x10
    return scc14_values

  def get_fca11_values():
    return {
      "CR_FCA_Alive": idx % 0xF,
      "PAINT1_Status": 1,
      "FCA_DrvSetStatus": 1,
      "FCA_Status": 1,
    }

  def calculate_fca11_checksum(values):
    fca11_dat = packer.make_can_msg("FCA11", 0, values)[1]
    values["CR_FCA_ChkSum"] = hyundai_checksum(fca11_dat[:7])
    return values

  scc11_values = get_scc11_values()
  commands.append(packer.make_can_msg("SCC11", 0, scc11_values))

  scc12_values = get_scc12_values()
  scc12_values = calculate_scc12_checksum(scc12_values)
  commands.append(packer.make_can_msg("SCC12", 0, scc12_values))

  scc14_values = get_scc14_values()
  commands.append(packer.make_can_msg("SCC14", 0, scc14_values))

  # Only send FCA11 on cars where it exists on the bus
  # On Camera SCC cars, FCA11 is not disabled, so we forward stock FCA11 back to the car forward hooks
  # If we don't use ESCC since ESCC does not block FCA11 from stock radar
  if use_fca and not ((CP.flags & HyundaiFlags.CAMERA_SCC) or (ESCC and ESCC.enabled)):
    # note that some vehicles most likely have an alternate checksum/counter definition
    # https://github.com/commaai/opendbc/commit/9ddcdb22c4929baf310295e832668e6e7fcfa602
    fca11_values = get_fca11_values()
    fca11_values = calculate_fca11_checksum(fca11_values)
    commands.append(packer.make_can_msg("FCA11", 0, fca11_values))

  return commands


def create_acc_opt(packer, CP, ESCC: EnhancedSmartCruiseControl | None = None):
  """
    Creates SCC13 and FCA12. If ESCC is enabled, it will only create SCC13 since ESCC does not block FCA12.
    :param packer:
    :param ESCC:
    :return:
  """

  def get_scc13_values():
    return {
      "SCCDrvModeRValue": 2,
      "SCC_Equip": 1,
      "Lead_Veh_Dep_Alert_USM": 2,
    }

  def get_fca12_values():
    return {
      "FCA_DrvSetState": 2,
      "FCA_USM": 1, # AEB disabled
    }

  commands = []

  scc13_values = get_scc13_values()
  commands.append(packer.make_can_msg("SCC13", 0, scc13_values))

  # If ESCC is available and enabled, we skip FCA12, since ESCC does not block FCA12
  if ESCC and ESCC.enabled:
    return commands

  # TODO: this needs to be detected and conditionally sent on unsupported long cars
  # On Camera SCC cars, FCA12 is not disabled, so we forward stock FCA12 back to the car forward hooks
  if not (CP.flags & HyundaiFlags.CAMERA_SCC):
    fca12_values = get_fca12_values()
    commands.append(packer.make_can_msg("FCA12", 0, fca12_values))

  return commands


def create_frt_radar_opt(packer):
  frt_radar11_values = {
    "CF_FCA_Equip_Front_Radar": 1,
  }
  return packer.make_can_msg("FRT_RADAR11", 0, frt_radar11_values)

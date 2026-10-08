# G70 2024: every tunable in the lateral control path (source inventory, 2026-10-07, session 13ws)

- **What this is:** a read-only source inventory of everything that could change the steering motion, active or not.
- **Source:** `dragal/custom` @ `89bbe60ab1`, made by one exploration agent.
- **Verified by the coordinator against the source:**
  - the two FRICTION_THRESHOLD values (V0 0.3, opendbc 0.2);
  - the torqued constants (#63–#71);
  - the controller selection (#16);
  - the EPS angle cut-off (#108);
  - the panda limits (#112–#116).
- **Toggle values are source defaults.** The live Params on the car are unknown.
- **Active chain with defaults:** stock modeld → controlsd → `LatControlTorqueV0` (with torqued, paramsd and lagd feeding it) → Hyundai carcontroller → panda `hyundai` mode.
- Path prefixes: `op/` = `openpilot/`, `odbc/` = `opendbc_repo/opendbc/`.
- For what the project has tested and found, see [weave-twitch-sim findings](2026-10-07-g70-weave-twitch-sim.md) §11.

## 1. Driving model output

| # | Tunable | Where | Value | Active |
|---|---|---|---|---|
| 1 | model process choice (stock modeld vs modeld_v2 bundle) | op/system/manager/process_config.py:124,172; op/sunnypilot/models/helpers.py:178–190 | stock (no `ModelManager_ActiveBundle`) | yes |
| 2 | LAT_SMOOTH_SECONDS (curvature smoothing; also added to lat_delay) | op/selfdrive/modeld/modeld.py:44 | 0.0 | yes (no-op) |
| 3 | MIN_LAT_CONTROL_SPEED | modeld.py:46 | 0.3 m/s | yes |
| 4 | curvature from the model's `action` output | modeld.py:65 | action/max(1,v)² | yes if the model has `action` |
| 5 | lat_delay given to the model (lagd raw; LagdToggle ignored here) | modeld.py:395 | lagd + 0.0 | yes |
| 6 | frame_delay / action_delay | modeld.py:425–426 | 0.05 / 0.025 s | yes |
| 7 | lat_action_t (model's `action_t` input) | modeld.py:427,432 | lag + 0.075 s | yes |
| 8 | MIN_STABLE_DELAY (plan → curvature) | op/selfdrive/controls/lib/drive_helpers.py:10,63–70 | 0.3 s | only without `action` |
| 9 | MIN_SPEED (plan → curvature) | drive_helpers.py:5,59 | 1.0 m/s | as #8 |
| 10 | smooth_value law | drive_helpers.py:24 | 1 − exp(−dt/τ) | yes |
| 11–15 | modeld_v2: LAT_SMOOTH 'lat' override; generation gate; PlanplusControl 1.0; CameraOffset 0.0 (0.9/0.1 smoothing, height 1.22 m); v2 lat_delay | op/sunnypilot/modeld_v2/modeld.py:108–111,300–314,465–509; camera_offset_helper.py:29–40 | defaults | no (v2 not selected) |

## 2. controlsd and the torque controller

| # | Tunable | Where | Value | Active |
|---|---|---|---|---|
| 16 | controller selection: V0 unless EnforceTorqueControl; TorqueControlTune 0.0 → V0, 1.0 → upstream (V1) | op/sunnypilot/selfdrive/controls/controlsd_ext.py:37–48 | V0 | yes |
| 17 | EnforceTorqueControl / TorqueControlTune | op/common/params_keys.h:290,294 | false / 0.0 | default-off |
| 18 | vehicle-model update floors (stiffness, sR ≥ 0.1) | controlsd.py:86–88 | — | yes |
| 19 | learned torque params replace offline ones (useParams) | controlsd.py:94–100 | Hyundai allowed | yes |
| 20 | standstill gate (minSteerSpeed 0, 0.3 m/s; steerAtStandstill false) | controlsd.py:113–119 | — | yes |
| 21 | lat_delay to the controller (lagd raw) | controlsd.py:147 | lagd + 0.0 | yes |
| 22 | extensions' lat_delay (refresh 3 s; LagdValueCache 0.2) | controlsd.py:104; controlsd_ext.py:55 | — | only with #43/#44 |
| 23 | steer_limited_by_safety threshold (freezes I) | controlsd.py:204 | 1e-2 | yes |
| 24 | MAX_LATERAL_JERK (curvature rate limit 5/v²) | drive_helpers.py:13,31–34 | 5.0 m/s³ | yes |
| 25 | MAX_LATERAL_ACCEL_NO_ROLL | drive_helpers.py:14,36–39 | 3.0 m/s² ± roll·g | yes |
| 26 | MAX_CURVATURE | drive_helpers.py:9 | 0.2 1/m | yes |
| 27 | steer_max (normalized range) | op/selfdrive/controls/lib/latcontrol.py:14 | 1.0 | yes |
| 28–29 | steerLimitTimer (saturation timer) / sat_check_min_speed | latcontrol.py:9–31 | 0.4 s / 10 m/s | alerts only |
| 30 | KP / KI / KD | op/sunnypilot/selfdrive/controls/lib/latcontrol_torque_v0.py:25–27 | 1.0 / 0.3 / 0.0 | yes |
| 31 | KP speed schedule | v0:28–29 | [1…30 m/s] → [250,120,65,30,11.5,5.5,3.5,2.0,1.0] | yes |
| 32 | LP_FILTER_CUTOFF_HZ (D-term rate filter) | v0:31 | 1.2 Hz | no effect (KD = 0) |
| 33 | LAT_ACCEL_REQUEST_BUFFER_SECONDS | v0:32 | 1.0 s | yes |
| 34 | FRICTION_THRESHOLD (V0's own) | v0:33 | 0.3 m/s² | yes |
| 35 | DESIRED_CURVATURE_LP_HZ (C4) | v0:40 | {G70_2024: 2.0} | yes |
| 36 | setpoint = lat_delay·jerk + expected (= the current request) | v0:98,104 | — | yes |
| 37 | feedforward = request − roll·g − latAccelOffset + friction | v0:109–113 | — | yes |
| 38 | integrator freeze (safety-limited, steering pressed, v < 5 m/s) | v0:115 | — | yes |
| 39 | PID output limits ±latAccelFactor | v0:69–71 | — | yes |
| 40 | anti-windup / i_dt | op/common/pid.py:14,53–58 | 0.01 | yes |
| 41 | torque = lat accel / latAccelFactor | odbc/car/interfaces.py:215–217 | linear | yes |
| 42 | first-order filter law | op/common/filter_simple.py:8–13 | α = dt/(rc+dt) | yes |

**Notes:**
- V0 does not override `reset()`, so `pid.i` carries over across disengagements.
- The upstream controller (V1) has its own constants: KP 0.8, KI 0.15, jerk lookahead 0.19 s, jerk gain 0.3, opendbc friction threshold 0.2. It has no C4.

## 3. sunnypilot torque extensions (all default-off)

| # | Tunable | Where | Value |
|---|---|---|---|
| 43 | LateralJerkTorqueController (torque-space error + lookahead-jerk friction) | latcontrol_torque_jerk_aware.py:19; params_keys.h:291 | 0 |
| 44 | NeuralNetworkLateralControl (NNLC) | nnlc/nnlc.py:39; params_keys.h:217 | 0 |
| 45–50 | NNLC: model match (0.99 exact, < 0.9 substitute), LOW_SPEED boost [12,3,1,0]², input horizons, pitch filter 0.5 s, error blend 1–2 m/s², friction override | nnlc/*.py | defaults |
| 51–56 | extension base: LAT_PLAN_MIN_IDX 5, LATERAL_LAG_MOD 0, lookahead 1.4–2.0 s at 9–30 m/s, lat_jerk_friction_factor 0.4, lat_accel_friction_factor 0.7, jerk-time floor | latcontrol_torque_ext_base.py:14–105 | defaults |
| 57–58 | opendbc FRICTION_THRESHOLD 0.2; torque-space get_friction | odbc/car/lateral.py:7; odbc/sunnypilot/car/lateral_ext.py:13–21 | used only by #43/#44 |
| 59 | TorqueParamsOverrideEnabled / LatAccelFactor / Friction (needs EnforceTorqueControl) | latcontrol_torque_ext_override.py:15–31 | 0 / 2.5 / 0.1 |
| 60 | Blinker pause lateral (enable, min speed, re-engage delay) | blinker_pause_lateral.py:24–27 | 0 / 20 / 0 |
| 61 | Mads / MadsSteeringMode (engagement only) | params_keys.h:198,200 | 1 / 0 (active) |

## 4. Online learners

| # | Tunable | Where | Value |
|---|---|---|---|
| 62 | torqued use_params (Hyundai allowed) | op/selfdrive/locationd/torqued.py:39,81 | yes |
| 63–71 | torqued: history 5 s; points per bucket 1500 / min total 4000 / fit 2000; min speed 15 m/s; friction factor 1.5; sanity ±30% laf, ±50% friction (→ laf 2.8–5.2, friction 0.035–0.105); steer min 0.02; lat-acc threshold 1.0; filter decay 50 → 250 s; 8 buckets with min points; engage buffer 2 s | torqued.py:18–36 | as listed |
| 72–73 | torqued lag alignment; restore key (fingerprint, tune, friction, laf, version) | torqued.py:105–190 | — |
| 74 | LiveTorqueParamsToggle / RelaxedToggle / CustomTorqueParams (need EnforceTorqueControl) | torqued_ext.py | off |
| 75–81 | paramsd: angle-offset rate 20°/s; roll limits (±10°, 8°, std 1.5°); validity thresholds; active speed 1 / 10 m/s; \|angle\| < 45°; sR valid 7.05–28.2; stiffness valid 0.2–5.0 (reset to 1.0 each drive) | op/selfdrive/locationd/paramsd.py:16–237 | as listed |
| 82 | paramsd Kalman noise (learning rates of stiffness, sR, offsets, roll) | op/selfdrive/locationd/models/car_kf.py:47–80 | as listed |
| 83 | lagd: block sizes, window 60 s, min speed 50 mph, min NCC 0.95, lag range 0.15–0.65 s, max std 0.1, confidence 0.7, smoothing | op/selfdrive/locationd/lagd.py:19–39 | as listed |
| 84 | lagd initial lag (steerActuatorDelay + 0.2) | lagd.py:186,241 | 0.3 s |
| 85 | LagdToggle / LagdToggleDelay / LagdValueCache (do not affect V0 or stock modeld) | lagd_toggle.py; params_keys.h:248–250 | 1 / 0.2 / 0.2 |

## 5. Vehicle model and CarParams for GENESIS_G70_2024

| # | Tunable | Where | Value |
|---|---|---|---|
| 86 | mass (incl. 136 kg standard load) | odbc/car/hyundai/values.py:603 | 1905 kg |
| 87 | wheelbase / steerRatio | values.py:603 | 2.83 m / 14.1 |
| 88 | centerToFront | hyundai/interface.py:131 | 1.132 m |
| 89 | tireStiffnessFactor / minSteerSpeed / steerRatioRear | interfaces.py:239–246 | 1.0 / 0 / 0 |
| 90–91 | rotationalInertia; tire stiffness front / rear | interfaces.py:161–162 | about 3579; about 250,373 / 263,859 |
| 92 | steerActuatorDelay / steerLimitTimer | hyundai/interface.py:132–133 | 0.1 s / 0.4 s |
| 93 | torque tune: LAT_ACCEL_FACTOR / MAX_LAT_ACCEL_MEASURED / FRICTION | odbc/car/torque_data/override.toml:120 | 4.0 / 2.7 / 0.07 |
| 94 | latAccelOffset (then learned) | interfaces.py:263 | 0.0 |
| 95 | steeringAngleDeadzoneDeg (D2) | hyundai/interface.py:25,36–41 | 0.4° |
| 96–97 | vehicle-model dynamic switch (> 0.1 m/s); curvature factor (understeer) | odbc/car/vehicle_model.py:61,79–90 | — |

## 6. opendbc helpers and Hyundai CAN

| # | Tunable | Where | Value |
|---|---|---|---|
| 98 | get_friction / apply_center_deadzone | odbc/car/lateral.py:198–212 | ±friction·laf |
| 99 | ISO limits for angle/curvature cars | lateral.py:10–18 | not used by torque cars |
| 100–104 | STEER_MAX / DELTA_UP / DELTA_DOWN / DRIVER_ALLOWANCE / MULTIPLIER / FACTOR / THRESHOLD / STEER_STEP | odbc/car/hyundai/values.py:20–57 | 384 / 3 / 7 / 50 / 2 / 1 / 150 / 1 |
| 105 | steeringPressed debounce | hyundai/carstate.py:125; interfaces.py:350–354 | 5 frames |
| 106 | steering angle source (SAS11, 0.1°, unfiltered); rate signal 4 °/s steps | carstate.py:119–120 | — |
| 107 | steerFaultTemporary (MDPS12 ToiUnavail/ToiFlt) | carstate.py:126 | — |
| 108 | EPS angle cut-off: MAX_ANGLE / FRAMES / CONSECUTIVE_FRAMES | hyundai/carcontroller.py:22–24 | 85° / 89 / 2 |
| 109–111 | torque scaling round(torque·384); torque_fault (CF_Lkas_ToiFlt); LKAS11 composition | carcontroller.py:88–143; hyundaican.py | — |

## 7. Panda safety (`hyundai`, CAMERA_SCC)

| # | Tunable | Where | Value |
|---|---|---|---|
| 112 | max_torque / max_rate_up / max_rate_down | odbc/safety/modes/hyundai.h:224,273–274 | 384 / 3 / 7 |
| 113 | max_rt_delta per 250 ms | hyundai.h:10 | 112 |
| 114–115 | driver torque allowance / multiplier; samples (MDPS12 at 50 Hz, last 6) | hyundai.h:11–12,46,161–164 | 50 / 2 |
| 116 | steer-request tolerance: min valid 89 frames, max invalid 2, min interval 810 ms | hyundai.h:16–19 | — |
| 117 | ALT / ALT_2 limits | hyundai.h:225–226 | not used |

## Not determined

- Whether the stock model outputs `action`. If it does, #8–#9 are unused.
- The car's live Params and cached learned values.
- Which NNLC model would load.
- The EPS's internal handling of CF_Lkas_ToiFlt/ActToi.
- Whether the panda firmware on the car matches this source.

# In-car checklist: G70 2024 port, first drives (user-run)

For use without Claude in the car (user decision, 2026-10-04). Software: `dragal/custom` @ `7e9d0755d9`. Alpha longitudinal **off**, NNLC **off**.

**Anytime fallback:** disengage (brake, cancel, or steer over), pull over, and if needed **unplug the comma device**. Comma's harness design returns the car to stock behaviour when the device is unpowered; that is not tested on this car. Rollback to the baseline software happens later, with Claude.

**Write down anything odd** with the approximate time (clock time is enough). The logs are matched to your notes by time.

## A. Parked, ignition on (~1 minute)

- [ ] The device shows the normal driving screen and **not** "dashcam mode" or "car unrecognized".
- [ ] No persistent alerts (examples: CAN error, communication issue, cruise fault, steering unavailable).
- **Stop here** (don't drive with it plugged in, or unplug it) if either box fails.

## B. Short drive, NOT engaged (5–10 minutes)

- [ ] No alerts appear while driving normally.
- [ ] If you use stock adaptive cruise, it works as usual with no cruise or SCC fault.
  - This is the key check for the `CAMERA_SCC` assumption. Cruise errors here mean **do not engage**.
- Note: with the device connected, the car's own lane-keeping assist may behave differently. openpilot takes over that message path. That is expected.
- **Stop** (no engagement) on any alert, CAN error, or cruise fault.

## C. First engagement: closed area, no traffic, low speed

- [ ] Hands on the wheel the whole time; be ready to override.
- [ ] Engage the way you normally would in sunnypilot. MADS is on by default, so lateral can engage separately from cruise. Know your disengage method before you start.
- [ ] Short engagements (10–30 s), gentle curves first.
- **Disengage immediately** on any of: unexpected or jerky steering, oscillation (wheel hunting left/right), any alert, or "steering temporarily unavailable". Note the time.
- At very low speed the car's steering system may refuse openpilot steering (a known Hyundai behaviour, unverified on this car). Note it if seen.

## D. Data collection while engaged (only if C was clean)

- [ ] Normal supervised driving with engagement on suitable roads. Aim for at least 30 minutes total, mixing straights, curves and some speed range.
- [ ] Note any disengagements you made for a reason other than routine (time + what happened).
- Don't let the device's storage fill with new drives before the logs are pulled: the oldest drives get deleted first.

## Afterwards (with Claude)

The device sits offroad/inactive and you confirm its current IP address. Claude then pulls the **rlogs** of those drives in one SSH session and analyses:
- fingerprint and safety mode
- which bus the SCC messages are on (the `CAMERA_SCC` check)
- CAN validity
- requested vs actual steering torque, faults, oscillation
- device CPU load vs the pre-deployment baseline

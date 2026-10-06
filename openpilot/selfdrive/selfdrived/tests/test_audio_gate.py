import os
from types import SimpleNamespace
from unittest import mock

from openpilot.cereal import messaging
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.selfdrived import selfdrived
from openpilot.selfdrive.selfdrived.events import process_not_running_alert
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.selfdrive.ui import soundd_ready


def manager_state(*procs):
  msg = messaging.new_message('managerState')
  msg.managerState.init('processes', len(procs))
  for p, (name, running, should_run, pid) in zip(msg.managerState.processes, procs, strict=True):
    p.name, p.running, p.shouldBeRunning, p.pid = name, running, should_run, pid
  return msg.managerState


class FakeSM:
  def __init__(self, ms, frame=0, received=True):
    self.ms, self.frame = ms, frame
    self.recv_frame = {'managerState': 1 if received else 0}

  def __getitem__(self, key):
    assert key == 'managerState'
    return self.ms


class TestAudioGate(OpenpilotTestCase):
  """SelfdriveD.audio_pending: engagement is blocked (processNotRunning) until soundd has an open audio stream."""
  def setup_method(self):
    self.ms = manager_state(("micd", True, True, 50), ("soundd", True, True, 100))

  def teardown_method(self):
    if os.path.exists(soundd_ready.marker_path()):
      os.remove(soundd_ready.marker_path())

  def _sd(self, frame=0, received=True):
    return SimpleNamespace(audio_ready=False, sm=FakeSM(self.ms, frame, received))

  def test_pending_until_stream_open(self):
    sd = self._sd()
    for frame in range(300):
      sd.sm.frame = frame
      assert SelfdriveD.audio_pending(sd)
    soundd_ready.mark_ready(100)
    sd.sm.frame = 300
    assert not SelfdriveD.audio_pending(sd)

  def test_pending_without_manager_state(self):
    soundd_ready.mark_ready(100)
    assert SelfdriveD.audio_pending(self._sd(received=False))

  def test_checked_at_10hz(self):
    soundd_ready.mark_ready(100)
    sd = self._sd(frame=5)
    assert SelfdriveD.audio_pending(sd)
    sd.sm.frame = 10
    assert not SelfdriveD.audio_pending(sd)

  def test_latched_once_ready(self):
    soundd_ready.mark_ready(100)
    sd = self._sd()
    assert not SelfdriveD.audio_pending(sd)
    os.remove(soundd_ready.marker_path())
    self.ms = manager_state(("soundd", True, True, 101))
    for frame in range(1, 50):
      sd.sm.frame = frame
      assert not SelfdriveD.audio_pending(sd)

  def test_stale_marker_keeps_blocking(self):
    soundd_ready.mark_ready(99)
    assert SelfdriveD.audio_pending(self._sd())

  def test_replay_and_simulation_not_gated(self):
    for flag in ("REPLAY", "SIMULATION"):
      with mock.patch.object(selfdrived, flag, True):
        assert not SelfdriveD.audio_pending(self._sd())
    assert SelfdriveD.audio_pending(self._sd())


  def test_process_not_running_event(self):
    """processNotRunning is raised while audio is pending even though every process is alive, and for real crashes."""
    sd = self._sd()
    sd.ignored_processes = {'mapd'}
    sd.process_not_running = lambda nr: SelfdriveD.process_not_running(sd, nr)
    sd.audio_pending = lambda: SelfdriveD.audio_pending(sd)
    assert sd.process_not_running(set())         # all alive, audio pending
    assert sd.process_not_running({'mapd'})      # only an ignored process down, audio pending
    soundd_ready.mark_ready(100)
    assert not sd.process_not_running(set())     # audio ready
    assert not sd.process_not_running({'mapd'})  # ignored process stays ignored
    assert sd.process_not_running({'micd'})      # real crash still raises it


class TestProcessNotRunningAlert(OpenpilotTestCase):
  def _text(self, ms):
    return process_not_running_alert(None, None, {'managerState': ms}, False, 0, None).alert_text_2

  def test_audio_starting_when_nothing_is_down(self):
    assert self._text(manager_state(("micd", True, True, 50), ("soundd", True, True, 100))) == "soundd (audio starting)"

  def test_real_crash_listed(self):
    assert self._text(manager_state(("micd", False, True, 50), ("soundd", True, True, 100))) == "micd"

  def test_crashed_soundd_listed_once(self):
    assert self._text(manager_state(("micd", False, True, 50), ("soundd", False, True, 100))) == "micd, soundd"

  def test_no_marker_lookup_in_replay(self):
    with mock.patch.object(soundd_ready, "is_ready", side_effect=AssertionError("alert must not read the marker")):
      assert self._text(manager_state(("micd", False, True, 50))) == "micd"

import contextlib
import os
import sys
import types
from unittest import mock

from openpilot.cereal import messaging
from openpilot.common.hardware.hw import Paths
from openpilot.common.test import OpenpilotTestCase
from openpilot.selfdrive.ui import soundd_ready
from openpilot.selfdrive.ui.soundd import Soundd
from openpilot.system.micd import Mic


def manager_processes(*procs):
  """procs: (name, running, shouldBeRunning, pid) tuples -> managerState.processes"""
  msg = messaging.new_message('managerState')
  msg.managerState.init('processes', len(procs))
  for p, (name, running, should_run, pid) in zip(msg.managerState.processes, procs, strict=True):
    p.name, p.running, p.shouldBeRunning, p.pid = name, running, should_run, pid
  return msg.managerState.processes


class FakeSoundDevice:
  """Stands in for the sounddevice module: the first `fail` stream opens raise, like PortAudio before the card is ready."""
  def __init__(self, fail):
    self.fail = fail
    self.opens = 0

  def _terminate(self):
    pass

  def _initialize(self):
    pass

  def _open(self, **kwargs):
    self.opens += 1
    if self.opens <= self.fail:
      raise RuntimeError("Error querying device -1")
    return "stream"

  OutputStream = _open
  InputStream = _open


class StreamOwner:
  callback = None


class TestSounddReadyMarker(OpenpilotTestCase):
  def teardown_method(self):
    if os.path.exists(soundd_ready.marker_path()):
      os.remove(soundd_ready.marker_path())

  def test_marker_path_is_shm_and_prefixed(self):
    path = soundd_ready.marker_path()
    assert os.path.dirname(path) == Paths.shm_path()
    assert os.environ["OPENPILOT_PREFIX"] in os.path.basename(path)

  def test_missing_marker_is_not_ready(self):
    assert not soundd_ready.is_ready(1234)

  def test_marker_matches_only_its_pid(self):
    soundd_ready.mark_ready(1234)
    assert soundd_ready.is_ready(1234)
    assert not soundd_ready.is_ready(4321)

  def test_new_instance_replaces_marker(self):
    soundd_ready.mark_ready(1)
    soundd_ready.mark_ready(2)
    assert not soundd_ready.is_ready(1)
    assert soundd_ready.is_ready(2)

  def test_default_pid_is_own_process(self):
    soundd_ready.mark_ready()
    assert soundd_ready.is_ready(os.getpid())

  def test_write_failure_fails_closed(self, mocker):
    mocker.patch("openpilot.selfdrive.ui.soundd_ready.tempfile.NamedTemporaryFile", side_effect=OSError("read-only"))
    soundd_ready.mark_ready(1234)  # must not raise
    assert not soundd_ready.is_ready(1234)

  def test_failed_replace_leaves_no_temp_file(self, mocker):
    mocker.patch("openpilot.selfdrive.ui.soundd_ready.os.replace", side_effect=OSError("busy"))
    before = set(os.listdir(Paths.shm_path()))
    soundd_ready.mark_ready(1234)
    assert set(os.listdir(Paths.shm_path())) == before
    assert not soundd_ready.is_ready(1234)

  def test_corrupt_marker_is_not_ready(self):
    with open(soundd_ready.marker_path(), "wb") as f:
      f.write(b"\xff\xfe\x00")
    assert not soundd_ready.is_ready(1234)

  def test_clear_removes_previous_marker(self):
    soundd_ready.mark_ready(1234)
    soundd_ready.clear()
    assert not soundd_ready.is_ready(1234)
    soundd_ready.clear()  # no marker: no error


class TestAudioReady(OpenpilotTestCase):
  def teardown_method(self):
    if os.path.exists(soundd_ready.marker_path()):
      os.remove(soundd_ready.marker_path())

  def test_no_manager_state_yet(self):
    soundd_ready.mark_ready(100)
    assert not soundd_ready.audio_ready(manager_processes(("soundd", True, True, 100)), manager_state_received=False)

  def test_waiting_for_stream(self):
    assert not soundd_ready.audio_ready(manager_processes(("soundd", True, True, 100)), True)

  def test_stream_open(self):
    soundd_ready.mark_ready(100)
    assert soundd_ready.audio_ready(manager_processes(("micd", True, True, 99), ("soundd", True, True, 100)), True)

  def test_stale_marker_from_previous_soundd(self):
    soundd_ready.mark_ready(77)
    assert not soundd_ready.audio_ready(manager_processes(("soundd", True, True, 100)), True)

  def test_crashed_soundd_is_not_ready(self):
    soundd_ready.mark_ready(100)
    assert not soundd_ready.audio_ready(manager_processes(("soundd", False, True, 100)), True)

  def test_soundd_not_managed(self):
    assert soundd_ready.audio_ready(manager_processes(("micd", True, True, 99)), True)

  def test_soundd_not_supposed_to_run(self):
    assert soundd_ready.audio_ready(manager_processes(("soundd", False, False, 0)), True)


class StopLoop(Exception):
  pass


class TestSounddThreadMarker(OpenpilotTestCase):
  """soundd clears an old marker when it starts and writes its own only once the output stream is open."""
  def _run(self, mocker, get_stream):
    calls = []
    patcher = mock.patch.dict(sys.modules, {"sounddevice": types.ModuleType("sounddevice")})
    patcher.start()
    self.addCleanup(patcher.stop)
    mocker.patch("openpilot.selfdrive.ui.soundd.soundd_ready.clear", side_effect=lambda: calls.append("clear"))
    mocker.patch("openpilot.selfdrive.ui.soundd.soundd_ready.mark_ready", side_effect=lambda: calls.append("mark_ready"))
    sm = mocker.patch("openpilot.selfdrive.ui.soundd.messaging.SubMaster").return_value
    sm.update.side_effect = StopLoop  # leave the main loop on its first iteration

    def stream(sd):
      calls.append("get_stream")
      return get_stream(sd)
    with contextlib.suppress(StopLoop, RuntimeError):
      Soundd.soundd_thread(types.SimpleNamespace(get_stream=stream))
    return calls

  def test_marks_ready_after_stream_open(self, mocker):
    assert self._run(mocker, lambda sd: mock.MagicMock()) == ["clear", "get_stream", "mark_ready"]

  def test_no_marker_when_stream_never_opens(self, mocker):
    def fail(sd):
      raise RuntimeError("get_stream failed after retry")
    assert self._run(mocker, fail) == ["clear", "get_stream"]


class TestAudioStreamRetryBudget(OpenpilotTestCase):
  def _get(self, get_stream, fail, mocker):
    sleep = mocker.patch("openpilot.common.utils.time.sleep")
    sd = FakeSoundDevice(fail)
    try:
      return get_stream(StreamOwner(), sd), sd, sum(c.args[0] for c in sleep.call_args_list)
    except Exception as e:
      return e, sd, sum(c.args[0] for c in sleep.call_args_list)

  def test_soundd_waits_through_30_attempts(self, mocker):
    stream, sd, slept = self._get(Soundd.get_stream, 29, mocker)
    assert stream == "stream" and sd.opens == 30 and slept == 87

  def test_soundd_gives_up_after_30_attempts(self, mocker):
    err, sd, slept = self._get(Soundd.get_stream, 30, mocker)
    assert isinstance(err, Exception) and "failed after retry" in str(err)
    assert sd.opens == 30 and slept == 90

  def test_micd_waits_through_30_attempts(self, mocker):
    stream, sd, slept = self._get(Mic.get_stream, 29, mocker)
    assert stream == "stream" and sd.opens == 30 and slept == 87

  def test_micd_gives_up_after_30_attempts(self, mocker):
    err, sd, slept = self._get(Mic.get_stream, 30, mocker)
    assert isinstance(err, Exception) and sd.opens == 30 and slept == 90

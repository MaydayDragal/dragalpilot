"""Reads comma rlog.zst files on the PC (no openpilot needed): pip install pycapnp zstandard.

  from pclog import read            ->  for msg in read(path): msg.which(), msg.logMonoTime, ...
  CEREAL: the cereal folder of a sunnypilot checkout; CAR_CAPNP_DIR: a folder holding opendbc's car.capnp
(both taken from the environment, see below). Slower than the device's reader but needs no device."""
import os, capnp, zstandard
CEREAL = os.environ.get("CEREAL_DIR"); CARDIR = os.environ.get("CAR_CAPNP_DIR")
_log = None
def schema():
    global _log
    if _log is None:
        capnp.remove_import_hook()
        _log = capnp.load(os.path.join(CEREAL, "log.capnp"), imports=[CEREAL, CARDIR])
    return _log
def read(path):
    data = zstandard.ZstdDecompressor().stream_reader(open(path, "rb")).read()
    it = schema().Event.read_multiple_bytes(data, traversal_limit_in_words=2 ** 63 - 1)
    while True:
        try: m = next(it)
        except StopIteration: return
        except capnp.KjException: return      # a segment cut off mid-message (ignition off): keep what was read
        yield m

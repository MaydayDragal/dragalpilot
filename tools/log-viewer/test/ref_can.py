#!/usr/bin/env python3
"""Reference CAN signal decode for the log viewer tests, using the pinned opendbc's DBC loader
and bit extraction (opendbc.can.parser.get_raw_value). Writes the DBC text it used (so the JS
side parses the very same file) and a digest per /<svc>/<bus>/<Message>/<Signal> series.

Run from the checkout's opendbc_repo with PYTHONPATH=.:.. (as the other rlog readers):
usage: ref_can.py <sunnypilot-root> <dbc-name> <rlog(.zst)> <out-dbc> <out.json>
"""
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import zstandard

from opendbc import get_generated_dbcs, DBC_PATH
from opendbc.can.dbc import DBC
from opendbc.can.parser import get_raw_value


def main():
  root, dbc_name, rlog, out_dbc, out_json = sys.argv[1:6]
  gen = get_generated_dbcs()
  text = gen[dbc_name] if dbc_name in gen else (Path(DBC_PATH) / f"{dbc_name}.dbc").read_text()
  Path(out_dbc).write_text(text)
  dbc = DBC(dbc_name)
  # opendbc drops multiplexing; read the m<n> markers from the text so muxed signals are only
  # decoded when their switch has that value (DBC semantics, as the viewer does)
  mux, cur = {}, None
  for line in text.splitlines():
    line = line.strip()
    if line.startswith("BO_ "):
      cur = line.split()[2].rstrip(":")
    m = re.match(r"SG_ (\w+) (M|m\d+) *:", line)
    if m and cur:
      mux.setdefault(cur, {})[m.group(1)] = m.group(2)

  from openpilot.cereal import log  # opendbc already loaded the shared schema files; reuse them
  raw = Path(rlog).read_bytes()
  if raw[:4] == b"\x28\xb5\x2f\xfd":
    raw = zstandard.ZstdDecompressor().stream_reader(raw).read()
  events = list(log.Event.read_multiple_bytes(raw, traversal_limit_in_words=2**63 - 1, nesting_limit=1024))
  t0 = min(e.logMonoTime for e in events)
  out = defaultdict(lambda: ([], []))
  for svc in ("can", "sendcan"):
    evs = sorted(((e.logMonoTime, i, e) for i, e in enumerate(events) if e.which() == svc), key=lambda x: (x[0], x[1]))
    for mono, _, e in evs:
      t = (float(mono) - float(t0)) / 1e9
      for f in getattr(e, svc):
        msg = dbc.addr_to_msg.get(f.address) if hasattr(dbc, "addr_to_msg") else None
        if msg is None:
          msg = next((m for m in dbc.msgs.values() if m.address == f.address), None) if isinstance(dbc.msgs, dict) else None
        if msg is None:
          continue
        dat = bytes(f.dat)
        mm = mux.get(msg.name, {})
        switch = next((msg.sigs[n] for n, k in mm.items() if k == "M"), None)
        for sig in msg.sigs.values():
          k = mm.get(sig.name)
          if k and k != "M" and (switch is None or get_raw_value(dat, switch) != int(k[1:])):
            continue
          if max(sig.lsb, sig.msb) // 8 >= len(dat):
            continue
          v = get_raw_value(dat, sig)
          if sig.is_signed and v >= (1 << (sig.size - 1)):
            v -= 1 << sig.size
          ts, vs = out[f"/{svc}/{f.src}/{msg.name}/{sig.name}"]
          ts.append(t)
          vs.append(v * sig.factor + sig.offset)

  def digest(a):
    return hashlib.sha1(np.asarray(a, dtype="<f8").tobytes()).hexdigest()

  Path(out_json).write_text(json.dumps({p: [len(ts), digest(ts), digest(vs)] for p, (ts, vs) in out.items()}, sort_keys=True))
  print(f"{len(out)} signal series from {dbc_name}")


if __name__ == "__main__":
  main()

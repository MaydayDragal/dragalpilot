#!/usr/bin/env python3
"""Reference flattener for the log viewer tests: walks an rlog with pycapnp's own reader and
applies the viewer's path rules, then writes a digest per series (count + SHA-1 of the float64
times and values) as JSON. Independent of the JS wire decoder; shares only the path rules.

usage: ref_flatten.py <sunnypilot-root> <rlog(.zst|.bz2)> <out.json> [max_scalar_list=64]
"""
import bz2
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import capnp
import numpy as np

SCALARS = {"bool", "int8", "int16", "int32", "int64", "uint8", "uint16", "uint32", "uint64", "float32", "float64", "enum"}
SKIP = {"void", "text", "data", "anyPointer", "interface"}
NO_DISC = 65535
EVENT_BASE = {"valid", "logMonoTime", "t"}


def num(v, kind):
  if kind == "enum":
    return float(v.raw)
  return float(v)


def elem_schema(schema, etype):
  return schema.elementType if etype.which() in ("struct", "list", "enum") else None


class Flattener:
  def __init__(self, max_list):
    self.max_list = max_list
    self.out = defaultdict(lambda: ([], []))

  def push(self, path, t, v):
    ts, vs = self.out[path]
    ts.append(t)
    vs.append(v)

  def struct(self, r, schema, path, t):
    which = r.which() if schema.union_fields else None
    for name in schema.fieldnames:
      f = schema.fields[name]
      p = f.proto
      if p.discriminantValue != NO_DISC and which != name:
        continue
      fp = f"{path}/{name}"
      if path.count("/") == 1 and name in EVENT_BASE:
        fp += " (payload)"  # the event-level series keeps /<service>/<name>
      if p.which() == "group":
        self.struct(getattr(r, name), f.schema, fp, t)
        continue
      kind = p.slot.type.which()
      if kind in SKIP:
        continue
      if kind in SCALARS:
        self.push(fp, t, num(getattr(r, name), kind))
      elif kind == "struct":
        if r._has(name):
          self.struct(getattr(r, name), f.schema, fp, t)
      elif kind == "list":
        if r._has(name):
          et = p.slot.type.list.elementType
          self.lst(getattr(r, name), et, elem_schema(f.schema, et), fp, t)

  def lst(self, lr, etype, eschema, path, t):
    k = etype.which()
    if k in SKIP:
      return
    if k in SCALARS:
      if len(lr) > self.max_list:
        return
      for i, v in enumerate(lr):
        self.push(f"{path}/{i}", t, num(v, k))
    elif k == "struct":
      for i, v in enumerate(lr):
        self.struct(v, eschema, f"{path}/{i}", t)
    elif k == "list":
      sub_t = etype.list.elementType
      for i, v in enumerate(lr):
        self.lst(v, sub_t, elem_schema(eschema, sub_t), f"{path}/{i}", t)


def main():
  root = Path(sys.argv[1])
  path = Path(sys.argv[2])
  max_list = int(sys.argv[4]) if len(sys.argv) > 4 else 64
  capnp.remove_import_hook()
  log = capnp.load(str(root / "openpilot/cereal/log.capnp"), imports=[str(root / "opendbc_repo/opendbc/car")])
  raw = path.read_bytes()
  if raw[:4] == b"\x28\xb5\x2f\xfd":
    import zstandard
    raw = zstandard.ZstdDecompressor().stream_reader(raw).read()
  elif raw[:3] == b"BZh":
    raw = bz2.decompress(raw)
  events = []
  try:
    for e in log.Event.read_multiple_bytes(raw, traversal_limit_in_words=2**63 - 1, nesting_limit=1024):
      events.append(e)
  except capnp.KjException as ex:
    print(f"stopped at a truncated message after {len(events)} events: {str(ex).splitlines()[0]}")
  t0 = min(e.logMonoTime for e in events)
  by_svc = defaultdict(list)
  for i, e in enumerate(events):
    by_svc[e.which()].append((e.logMonoTime, i, e))
  ev_schema = log.Event.schema
  fl = Flattener(max_list)
  for svc, items in by_svc.items():
    items.sort(key=lambda x: (x[0], x[1]))
    field = ev_schema.fields[svc]
    kind = field.proto.slot.type.which()
    for mono, _, e in items:
      t = (float(mono) - float(t0)) / 1e9
      fl.push(f"/{svc}/valid", t, float(e.valid))
      fl.push(f"/{svc}/logMonoTime", t, float(mono))
      fl.push(f"/{svc}/t", t, t)
      if svc in ("can", "sendcan"):
        continue
      payload = getattr(e, svc)
      if kind == "struct":
        fl.struct(payload, field.schema, f"/{svc}", t)
      elif kind == "list":
        et = field.proto.slot.type.list.elementType
        fl.lst(payload, et, elem_schema(field.schema, et), f"/{svc}", t)

  def digest(a):
    a = np.asarray(a, dtype="<f8")
    a = np.where(np.isnan(a), np.nan, a)
    return hashlib.sha1(a.tobytes()).hexdigest()

  out = {p: [len(ts), digest(ts), digest(vs)] for p, (ts, vs) in fl.out.items()}
  Path(sys.argv[3]).write_text(json.dumps({"events": len(events), "series": out}, sort_keys=True))
  print(f"{len(events)} events, {len(out)} series")


if __name__ == "__main__":
  main()

"""Live steering reader, PC side.

Starts device_reader.py on the comma over ssh (the script is piped in; nothing is written to the device),
saves every row to a CSV on the PC and prints a status line every few seconds.

  python live.py --out <folder> [--usb | --host 192.168.x.y] [--key <private key>] [--adb <adb.exe>] [--rate 20] [--seconds N]

--usb (default) forwards local port 8022 to the device's ssh port with adb. Ctrl+C stops it; the reader on
the comma exits when the connection closes. Summaries: summary.py <csv>.
"""
import argparse, datetime, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REMOTE = ("cd /data/openpilot && LIVE_RATE={rate} LIVE_MAX_SECONDS={secs} PYTHONPATH=/data/openpilot PYTHONDONTWRITEBYTECODE=1 "
          "exec nice -n 10 /usr/local/venv/bin/python -u -")


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--out", required=True)
  ap.add_argument("--host", help="device address on Wi-Fi/hotspot; omit to use USB (adb forward)")
  ap.add_argument("--usb", action="store_true")
  ap.add_argument("--port", type=int, default=8022, help="local port for the adb forward")
  ap.add_argument("--key", default=os.path.expanduser("~/.ssh/id_ed25519_dragalpilot"))
  ap.add_argument("--adb", default="adb")
  ap.add_argument("--rate", type=float, default=20)
  ap.add_argument("--seconds", type=float, default=7200)
  ap.add_argument("--status", type=float, default=5, help="seconds between status lines")
  ap.add_argument("--host-key-alias", default="192.168.98.104", help="known_hosts name of the device's host key")
  a = ap.parse_args()

  ssh = ["ssh", "-i", a.key, "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "LogLevel=ERROR",
         "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=3", "-o", f"HostKeyAlias={a.host_key_alias}"]
  if a.host:
    ssh += [f"comma@{a.host}"]
  else:
    subprocess.run([a.adb, "forward", f"tcp:{a.port}", "tcp:22"], check=True, stdout=subprocess.DEVNULL)
    ssh += ["-p", str(a.port), "comma@127.0.0.1"]
  ssh.append(REMOTE.format(rate=a.rate, secs=a.seconds))

  os.makedirs(a.out, exist_ok=True)
  path = os.path.join(a.out, "live-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv")
  print("saving to", path, flush=True)
  with open(os.path.join(HERE, "device_reader.py"), "rb") as script, open(path, "w", newline="\n") as f:
    p = subprocess.Popen(ssh, stdin=script, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    cols, n, last, t_last_row = None, 0, time.time(), time.time()
    try:
      for line in p.stdout:
        f.write(line)
        if line.startswith("#"):
          print(line.rstrip(), flush=True)
          continue
        if cols is None:
          if line.startswith("t,"):
            cols = line.strip().split(",")
          else:
            print(line.rstrip(), flush=True)  # an error from ssh or python
          continue
        n += 1
        t_last_row = time.time()
        if t_last_row - last >= a.status:
          last = t_last_row
          f.flush()
          r = dict(zip(cols, line.strip().split(",")))
          g = lambda k, fmt="{:.2f}": fmt.format(float(r[k])) if r.get(k) else "-"
          lane = "{:+.2f}".format((float(r["ll"]) + float(r["rl"])) / 2) if r.get("ll") and r.get("rl") else "-"
          print(f"rows {n:6d} | started {r.get('started') or '-'} | v {g('v', '{:.1f}')} m/s | latActive {r.get('latActive') or '-'} | "
                f"des {g('desiredLateralAccel')} act {g('actualLateralAccel')} | torque {g('out')} | wheel {g('ang', '{:.1f}')} deg | "
                f"lane {lane} m | delay {g('delay')} s", flush=True)
    except KeyboardInterrupt:
      pass
    finally:
      p.terminate()
      try:
        p.wait(5)
      except subprocess.TimeoutExpired:
        p.kill()
  print(f"stopped: {n} rows in {path}", flush=True)
  return 0 if n else 1


if __name__ == "__main__":
  sys.exit(main())

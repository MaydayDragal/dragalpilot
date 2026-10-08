# Remote SSH to the device through the comma proxy (ssh.comma.ai): research (2026-10-07, session 11r)

Research only; **no device connection was made**. Purpose: reach the device while it is away from the home LAN (at the user's
partner's workplace) for a read-only, rlogs-only pull of the D2C4 A/B drives
([kickoff](../sessions/2026-10-07-s11-remote-pull-d2c4-ab-kickoff.md)).

Evidence labels (CLAUDE.md §4):
- **source fact** = pinned checkout `dragal/custom` @ `89bbe60ab1` (the installed revision), file + line;
- **doc fact** = official documentation (in-tree `docs/` at the same revision, or docs.comma.ai);
- **observation** = device params pulled read-only on 2026-10-06 ~22:31 EDT (`E:\DragalPilot\device-logs\2026-10-06_s10_diag\`), not current;
- **inference** = not shown by any source; the server side of ssh.comma.ai is closed source.

## 1. How the proxy works

### 1.1 Path

```text
laptop ssh ──TCP 22──> ssh.comma.ai (jump host, user "comma-<dongleId>")
                         └── comma backend ──JSON-RPC "startLocalProxy"──> athenad on the device (already-open websocket)
                                                                   athenad opens a NEW websocket back to the backend
                                                                   and a TCP socket to 127.0.0.1:22 (the device's sshd)
laptop ssh <════ end-to-end SSH session with the device's own sshd (user "comma") ════> device
```

- **Device side (source facts, `openpilot/system/athena/athenad.py`):**
  - `athenad` keeps a persistent websocket to `wss://athena.comma.ai/ws/v2/<DongleId>`, authenticated by a JWT the device signs with its own key (`main`, L1144–1190; `ATHENA_HOST` L53).
  - The backend asks it to `startLocalProxy(remote_ws_uri, local_port)` (L739–745). athenad opens a websocket to the given URI with the device's JWT and bridges it to `127.0.0.1:<port>` (L748–781).
  - Only port 22 is allowed (`LOCAL_PORT_WHITELIST = {22}`, L55; 8022 is mapped to 22, L754–755). Nothing else on the device can be reached this way.
  - The proxy socket is marked high priority (`SSH_TOS`, L35, L761).
  - Frames are 4096 bytes (`WS_FRAME_SIZE`, L64), carried by two Python threads (`ws_proxy_recv`/`ws_proxy_send`, L1026–1075).
- **The SSH session is end to end:** the comma backend relays bytes, but authentication happens at the device's own sshd, with the same key and host key as on the LAN.
- **athenad runs at all times:** it is a `DaemonProcess` (`system/manager/process_config.py` L110), started by the manager regardless of onroad/offroad. The proxy therefore works onroad *and* offroad; our rules (§4) restrict us to offroad.
- **Client side (source fact, `tools/scripts/ssh.py`; doc fact, `docs/how-to/connect-to-comma.md` "ssh.comma.ai proxy", same text on docs.comma.ai):**
  - `ssh -i KEY -o ProxyCommand="ssh -i KEY -W %h:%p -p %p %h@ssh.comma.ai" -p 22 comma@comma-<dongleId>`.
  - So the jump-host user is `comma-<dongleId>`. The docs' one-off example uses the bare dongle ID as host; `ssh.py` uses the `comma-` prefix.
  - `ssh.py` needs a comma account token only to look up the dongle ID from a device alias (`CommaApi(get_token()).get("v1/me/devices")`). With the dongle ID known, no account token is needed.
  - ssh.comma.ai host key (doc fact): **`SHA256:X22GOmfjGb9J04IA2+egtdaJ7vW9Fbtmpz9/x8/W1X4`** (RSA 4096).

### 1.2 Requirements

| Requirement | What the sources say | Our status |
|---|---|---|
| **comma prime** | Doc fact: "With a comma prime subscription, you can SSH into your comma device from anywhere." | Observation: `PrimeType=5` (`PURPLE`). Source fact: `PrimeType` 5 > `NONE` (0) counts as prime (`selfdrive/ui/lib/prime_state.py` L15–23, `is_prime`). The UI refreshes this param from the API while offroad and awake (`_worker_thread`). **The user should confirm the subscription is still active.** |
| **Device paired** to the account that holds prime | Inference from the above (prime is per device, through comma connect). | `PrimeType` ≥ 0 means paired (source fact, `is_paired`). Observation: paired. |
| **Device online, athenad connected** | Source fact: the backend can only reach the device through athenad's open websocket. Any network works (Wi-Fi or cellular); athenad only needs outbound `wss` (443). | Unknown now. Observation: `LastAthenaPingTime` was being updated at the last pull. |
| **Device awake and powered** | Source fact: a remote session cannot wake the device; it needs athenad running. Out of the car there is no ignition, so the device stays offroad. | **The user must keep it powered** for the whole pull. |
| **SSH enabled on the device** | Doc fact: "Enable SSH in your device's settings". | Observation: `SshEnabled=1`. |
| **Key accepted** | Doc fact: the device's authorized keys are the GitHub keys of the username entered on the device. The docs use the same key for the jump host and the device. Source fact: athenad exposes `getSshAuthorizedKeys` (returns `GithubSshKeys`, L790–792). *Inference:* ssh.comma.ai authenticates the jump hop against these keys. | Observation: `GithubUsername=maydaydragal`. `GithubSshKeys` holds exactly one key, fingerprint `SHA256:23gLEBOzR8Jt5JiSnTwCYNMzzkmTwEUcShDpzsyAHX8`, **identical to our `~/.ssh/id_ed25519_dragalpilot.pub`**. No other key is needed. |
| **SSH client** | — | Git Bash `OpenSSH_10.5p1` on the VM supports `ProxyCommand`/`-W`. |

### 1.3 sunnypilot's sunnylink: an alternative?

- **Device side exists (source facts):**
  - `sunnylinkd` (`openpilot/sunnypilot/sunnylink/athena/sunnylinkd.py`) keeps a similar websocket to `wss://athena.sunnylink.ai` with its own `SunnylinkDongleId` and token.
  - It has its own `startLocalProxy` (L257–266) that reuses athenad's shim, so it also reaches only port 22.
  - Observation: `SunnylinkEnabled=1`, `SunnylinkTempFault=0`.
- **But:**
  - Neither the checkout nor the sunnylink documentation describes a client-side SSH endpoint or command. The community doc ([sunnylink connected services](https://community.sunnypilot.ai/t/3707)) lists "local port proxying for SSH-like access" without saying how to use it or which sponsor tier it needs.
  - sunnylinkd opens the proxy websocket with `sslopt={"cert_reqs": ssl.CERT_NONE}` (L263–264), i.e. **without TLS certificate verification**. athenad's proxy does verify (default `create_connection`). The SSH layer still authenticates end to end, so this is a confidentiality-of-metadata and availability weakness, not a login bypass.
  - sunnypilot's maintainer, asked about cellular SSH, pointed to "comma's official instructions for remote SSH access" with prime ([community thread](https://community.sunnypilot.ai/t/how-to-ssh-into-the-device-with-cellular/482)).
- **Conclusion:** use ssh.comma.ai. sunnylink offers no documented, usable path today.

Other options from the same thread, for completeness: a phone hotspot or Tailscale put the laptop and device on one subnet. Neither applies to a VM at home and a device elsewhere without installing software on the device, which is out of scope.

## 2. What the user must supply or do

**No secrets are needed from the user.**
- No comma account login or JWT: we connect by dongle ID, not alias.
- No GitHub credentials: the key is already on the device.
- **Dongle ID:** already known from the 2026-10-06 params pull. It stays on `E:` (`device-logs/2026-10-06_s10_diag/data/params/d_tmp/DongleId`) and is not written into the repo. The user can cross-check it in comma connect if they wish.
- **Private key:** stays in `~/.ssh/` on the VM.

**User actions and confirmations:**
1. **Power and network:**
   - the device powered on (out of the car, so offroad), and kept powered for the whole pull;
   - online, preferably on Wi-Fi (faster, unmetered).
   - Cellular also works if the SIM has data; the pull's data use (§3) then counts against that plan. Say which network it is on.
2. **comma prime** still active on the device's comma connect account (`PrimeType=5` was last seen 2026-10-06). The device showing "online" in comma connect is a useful pre-check.
3. **Device state:**
   - not in a car, not driving (CLAUDE.md §6);
   - **no other SSH session** to it (the user's own or other tools), and no other agent session using SSH.
4. **Authorization for the connections** in §5.

## 3. Bandwidth and practicality

- **Size:** from 431 earlier rlogs (`recordings/`), mean **10.9 MB per 1-minute segment** (max 12.2 MB). The session 10 pull averaged 11.3 MB. So **≈ 0.65–0.7 GB per hour of driving**.
  - The number of new routes is unknown until the listing. The last pull ended at route `0x25` (2026-10-06 20:38 EDT). Everything after it is new, including the ~13:27 EDT "A" drive and any earlier same-day drive.
  - Example: 2 h of driving ≈ 1.4 GB.
- **Throughput:** not measured. Bytes go laptop ↔ ssh.comma.ai ↔ comma backend ↔ device websocket ↔ athenad's Python threads (4 KB frames), so expect well below LAN speed. The first pull batch measures it and the plan adapts. rlogs are already zstd-compressed, so SSH compression (`-C`) would not help.
- **Resumable, hash-verified design** (adapting the session 10 single-tar method, which cannot resume):
  1. **Connection 1, listing (small):**
     - state checks (`IsOffroad=1`, `IsOnroad`≠1, `GitCommit`, sessions);
     - the list of segments after `0x25` with sizes and mtimes;
     - on-device `sha256sum` of every candidate `rlog.zst` (read-only, `nice -n 19`);
     - the small diagnostics: swaglog lines matching the torqued/paramsd/lagd restores, `CarParamsPersistent` and the configuration params (non-secret keys only).
     - The output is a manifest saved to `temporary/`.
  2. **Connections 2…n, pull batches:**
     - one route (or ≤ ~0.5 GB) per connection, streamed as `tar -cf - <files> | ` stdout (no staging on the device);
     - extracted into `temporary/` and checked against the manifest's sha256 per file.
     - A dropped connection loses at most the current batch. The rerun requests only files not yet verified, so the pull is resumable at file granularity (≤ 12 MB lost per interruption).
     - Connections are strictly sequential: the next one opens only after the previous ssh process has exited.
  3. **Keep-alives:** `ServerAliveInterval=15`, `ServerAliveCountMax=4`, `ConnectTimeout=30`, `BatchMode=yes` (fail rather than prompt).
- **Promotion:** as usual into `recordings/YYYY/MM/DD/HH-MM-SS__<route>/rlogs/` (America/New_York start time), with provenance. Every segment's `fcamera`/`ecamera` is recorded in `metadata/` as a gap, "deferred: remote pull, rlogs only".
- **Deferred videos and the deleter** (source facts, `system/loggerd/deleter.py` L13–14, L76–86): the deleter removes the oldest segments only when `/data` free space is < 10% or < 5 GiB.
  - Observation: `/data` had 49 GB free of 89 GB on 2026-10-06.
  - Earlier pulls average 36 MB per segment for each road camera, so a driving hour uses roughly 5 GB with both cameras and the logs.
  - *Inference:* about 8 more hours of driving before the deleter touches anything. The LAN video pull should still happen soon.

## 4. Risks and keeping it read-only

- **No wake-up, no state change:** the proxy cannot wake the device or start it onroad. It uses athenad's existing websocket and an extra one per session (source facts above).
- **Device load (offroad only):**
  - the bytes pass through two Python threads in athenad, plus sshd/tar/sha256sum, all run at `nice -n 19`.
  - This is acceptable offroad. **Never while onroad** (CLAUDE.md §6: CPU overhead is safety-sensitive).
- **athenad/uploader interference:**
  - the proxy runs in its own threads; the uploader continues independently (its qlog/qcamera uploads share the uplink, which only slows us);
  - reading files does not change the uploader's `user.upload` xattrs or the deleter's `user.preserve` (both are set only by those processes);
  - **no uploads are requested through comma connect.** That would be a device-side action and is out of scope.
- **Read-only commands only:**
  - `cat`, `ls`, `stat`, `grep` on swaglogs, `sha256sum`, `tar -c` to stdout;
  - no files written on the device (unlike the install, nothing goes to `/data/tmp`);
  - no param writes, no installs, no restarts.
  - Unavoidable side effects, the same as every LAN session: sshd's login records and journald entries.
- **Host-key safety:**
  - the device hop uses `-o HostKeyAlias=192.168.98.104 -o StrictHostKeyChecking=yes`, so the device must present **the same host key already recorded from the LAN**. A relay cannot impersonate it.
  - ssh.comma.ai's key goes into a separate known-hosts file on `E:` (`E:\DragalPilot\cache\ssh\known_hosts.comma-proxy`), accepted only if it matches the documented fingerprint. `~/.ssh/known_hosts` is not modified.
- **One device connection at a time:** the `ProxyCommand` ssh is a second local process, but it carries the same single session to the device. The jump connection ends at comma's server. We never run two device sessions or a monitoring session alongside.
- **Secrets:**
  - no private keys pulled; no full `params/` dump this time (only named, non-secret keys);
  - the dongle ID and any tokens stay on `E:`.

## 5. Proposed command and connection plan (needs the user's authorization)

Git Bash, from the VM (`<DONGLE>` = the value on `E:`; `$KH` = the E: known-hosts file):

```bash
KEY=~/.ssh/id_ed25519_dragalpilot
ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes \
  -o ProxyCommand="ssh -i $KEY -o IdentitiesOnly=yes -o BatchMode=yes -o UserKnownHostsFile=$KH -o StrictHostKeyChecking=yes -W %h:%p -p 22 %h@ssh.comma.ai" \
  -o HostKeyAlias=192.168.98.104 -o StrictHostKeyChecking=yes \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=4 -o ConnectTimeout=30 \
  -p 22 comma@comma-<DONGLE> 'bash -s' < <read-only script> > <out> 2> <log>
```

1. **No device contact:** fetch ssh.comma.ai's host key (`ssh-keyscan -t rsa ssh.comma.ai`) into `$KH`, and check it against `SHA256:X22GOmfjGb9J04IA2+egtdaJ7vW9Fbtmpz9/x8/W1X4`. Stop if it differs.
2. **Connection 1:** listing, manifest and diagnostics (§3). It aborts unless `IsOffroad=1`, and it reports other sshd sessions.
3. **Connections 2…n:** rlog batches until every file is verified. Then promotion, metadata gaps and provenance.

Sources:
- checkout `89bbe60ab1`:
  - `openpilot/system/athena/athenad.py`, `openpilot/system/athena/manage_athenad.py`;
  - `openpilot/system/manager/process_config.py`, `openpilot/selfdrive/ui/lib/prime_state.py`;
  - `openpilot/sunnypilot/sunnylink/athena/sunnylinkd.py`, `openpilot/sunnypilot/sunnylink/utils.py`;
  - `openpilot/system/loggerd/deleter.py`, `openpilot/system/loggerd/uploader.py`;
  - `tools/scripts/ssh.py`, `docs/how-to/connect-to-comma.md`;
- [docs.comma.ai: connect to comma](https://docs.comma.ai/how-to/connect-to-comma/) (fetched 2026-10-07);
- [sunnypilot community: SSH over cellular](https://community.sunnypilot.ai/t/how-to-ssh-into-the-device-with-cellular/482);
- [sunnypilot community: sunnylink connected services](https://community.sunnypilot.ai/t/3707).

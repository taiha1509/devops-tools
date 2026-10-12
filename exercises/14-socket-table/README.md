# E14 — `sockstat`: A Mini `ss` From `/proc/net`

**Linux track · after E04 · ~5-7 hours**

## The problem

A service fails health checks under load. `ss -s` shows 28,000 sockets in `TIME_WAIT`. Half the team
thinks that's the bug; the other half thinks it's normal. A second service won't start because
"address already in use", and nobody can find what's holding the port.

Both questions are answered by the same two kernel files and one join. Build it.

## What you're building

```bash
sockstat list --state listen            # who is listening, like ss -tlnp
sockstat list --port 5432               # everything touching one port
sockstat summary                        # count per TCP state, like ss -s
sockstat who-has 8080                   # which PID holds this port
```

## Requirements

- **Parse `/proc/net/tcp` and `/proc/net/tcp6`.** Each row has `local_address`, `rem_address`,
  `st`, `uid`, and `inode`, among others. Addresses are hex `IP:PORT`.
- **Byte order is the lesson.** The port is plain big-endian hex (`1F90` → 8080). The IPv4 address
  is the kernel's in-memory `u32` printed as hex, which on x86 and ARM (little-endian) means
  `0100007F` is `127.0.0.1`, not `1.0.0.127`. IPv6 is four such 32-bit words, each in host order.
  Use `socket.inet_ntop` after re-ordering, and write the test that proves `0100007F` decodes to
  `127.0.0.1`.
- **Map state codes to names.** `st` is hex: `01` ESTABLISHED, `02` SYN_SENT, `03` SYN_RECV,
  `04` FIN_WAIT1, `05` FIN_WAIT2, `06` TIME_WAIT, `07` CLOSE, `08` CLOSE_WAIT, `09` LAST_ACK,
  `0A` LISTEN, `0B` CLOSING. Use an `Enum`, not a dict of strings.
- **Socket → PID is a join, not a lookup.** The row's `inode` identifies the socket. The owning
  process has a file descriptor under `/proc/[pid]/fd/` whose symlink target is `socket:[<inode>]`.
  Build the inode→PID map once per run by walking every process's `fd` directory. Expect
  `PermissionError` on other users' processes when not root: skip, count, and report how many you
  couldn't see — don't silently pretend they have no sockets. (`ss -p` has the same limitation, and
  shows nothing for them.)
- **`TIME_WAIT` rows have inode `0`.** They belong to no process any more. Know why before you write
  the code that handles it.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] Decoder tests for: `127.0.0.1`, `0.0.0.0`, an IPv6 loopback (`::1`), and an IPv4-mapped
      IPv6 address (`::ffff:10.0.0.5`) — the last one is how a dual-stack listener shows up
- [ ] `who-has` finds the PID from a fixture `fd` directory containing symlinks
- [ ] Inaccessible processes are counted and reported, not dropped
- [ ] Live comparison against `ss -tanp` in the container, differences explained in `DECISIONS.md`

## Capturing fixtures

In the container: `python3 -m http.server 8080 &`, then `curl -s localhost:8080 >/dev/null` a few
times to leave `TIME_WAIT` sockets behind. Copy `/proc/net/tcp` and `/proc/net/tcp6` immediately.
For the `fd` join, `ls -l /proc/<pid>/fd` and recreate those symlinks in `tests/fixtures/` with
`os.symlink` in a fixture — symlinks to `socket:[12345]` are just dangling links, which is fine.

## Stretch

`/proc/net/udp` uses the same format. Add `--udp`. Then read `/proc/sys/net/ipv4/ip_local_port_range`
and report how close you are to ephemeral port exhaustion — the real reason 28,000 `TIME_WAIT`
sockets can matter.

## Why this one matters

"Address already in use", `TIME_WAIT` storms, and "is anything listening on that port inside the
pod?" are everyday incidents. Knowing that `ss` is reading hex rows from a text file, joined to fd
symlinks by inode, means you can answer them on a box where `ss` isn't installed — which, in a
distroless container, is every box.

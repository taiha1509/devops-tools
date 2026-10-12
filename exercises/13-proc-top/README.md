# E13 — `ptop`: Processes From `/proc`

**Linux track · after E02 · ~6-8 hours**

## The problem

A node is slow. Someone runs `top`, sees a process at 380% CPU, and restarts it. It comes back at
380%. Nobody in the room can say what "380%" means on this box, whether RSS includes shared libraries,
or why `top`'s first frame shows different numbers from every frame after it.

`ps` and `top` are not magic. They open files under `/proc`, parse text, and do a little arithmetic.
Build that, and you stop guessing what the numbers mean.

## What you're building

```bash
ptop list --sort rss --limit 15        # one snapshot, like ps aux
ptop top --interval 2 --iterations 5   # CPU % over an interval, like top -b
ptop show 1234                         # one process in detail
```

Each process: PID, PPID, state, user, command, RSS, CPU % (in `top` mode), start time.
Plus a system line: load average, total/available memory, uptime.

## Requirements

- **Read the right files.** `/proc/[pid]/stat` for state, PPID, CPU ticks (`utime`, `stime`) and
  start time; `/proc/[pid]/status` for `Uid` and `VmRSS`; `/proc/[pid]/cmdline` for the command;
  `/proc/stat`, `/proc/meminfo`, `/proc/loadavg`, `/proc/uptime` for the system line.
- **Parse `stat` correctly.** Field 2 (`comm`) is in parentheses and may itself contain spaces and
  parentheses. Splitting on whitespace is the classic bug. Split on the *last* `)`. Write a test with
  a process named `(sd-pam)` and one named `my proc)`.
- **Convert units, don't assume them.** CPU times are in clock ticks — read
  `os.sysconf("SC_CLK_TCK")` rather than hard-coding 100. Start time is ticks since boot, so you need
  `/proc/uptime` to turn it into a wall-clock time. RSS in `status` is kB; RSS in `stat` is pages.
  Pick one and say why in `DECISIONS.md`.
- **CPU % needs two samples.** A process's CPU % is (Δ its ticks) ÷ (Δ wall ticks) over an interval.
  One snapshot can only give you a lifetime average, which is what `ps` shows and why it disagrees
  with `top`. Decide whether 100% means one core or all cores (`top` and `htop` both default to one
  core, so 380% means nearly four) and put it in the `--help`.
- **Processes vanish mid-read.** A PID in `os.listdir("/proc")` can be gone before you open its
  `stat`. That is not an error, it is Tuesday. `FileNotFoundError` and `ProcessLookupError` skip the
  process; they never crash the run. Kernel threads have no `cmdline` and no `VmRSS`; handle both.
- **`now` and the clock tick rate are parameters** to the pure functions, for the same reason `now`
  was in E01: testable without freezing time.

## Acceptance criteria

- [ ] Same done bar as E01, on fixtures, on your Mac
- [ ] Fixture tree with at least: a normal process, a kernel thread, a zombie (state `Z`), a
      process whose `comm` contains `)`, and a PID directory whose `stat` is missing
- [ ] `top` mode computes CPU % from two fixture snapshots with known tick deltas; the test asserts
      the exact number
- [ ] Live comparison: `ptop list` vs `ps -eo pid,ppid,stat,rss,comm` in the container. Every
      difference explained in `DECISIONS.md`

## Capturing fixtures

In the container, start something to look at:

```bash
sleep 1000 &
# comm comes from the executable's file name (not argv[0]), so rename the binary:
cp /bin/sleep '/tmp/my proc)' && '/tmp/my proc)' 1000 &
# a zombie: the child exits immediately and the parent never reaps it
python3 -c 'import os,time; os.fork() or exit(); time.sleep(600)' &
```

Then copy `/proc/<pid>/{stat,status,cmdline}` for each, plus a kernel thread if the container can
see one, into `tests/fixtures/proc/<pid>/`. Note that `comm` is truncated to 15 characters; a test
for that is cheap.

## Why this one matters

"Walk me through what `top` is showing you" is a standard SRE screen question, and most answers stop
at reading the columns aloud. Being able to say *CPU % is a delta of `utime+stime` over an interval,
divided by clock ticks, per core* — and that's why the first frame is garbage — is the difference.

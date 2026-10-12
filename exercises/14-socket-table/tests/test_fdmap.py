"""Contract for parsing the table and joining sockets to processes.

The join is the half people get wrong by making it a lookup. There is no file
saying "socket 29123 belongs to pid 1217" - you build the inode map once and
join, or you re-walk `/proc` for every one of 28,000 rows and your tool appears
to hang.
"""

from __future__ import annotations

from sockstat.fdmap import attach_pids, build_inode_map, who_has_port
from sockstat.models import TcpState
from sockstat.parse import parse_net_tcp
from sockstat.source import LiveProcSource

LISTENER_INODE = 29123
PG_LISTENER_INODE = 18442
ESTABLISHED_INODE = 29150


class TestParseNetTcp:
    def test_the_header_line_is_skipped(self, net_tcp):
        """Nine data rows in the fixture. Ten means the header became a socket."""
        assert len(parse_net_tcp(net_tcp)) == 9

    def test_a_listener_is_decoded_end_to_end(self, net_tcp):
        sockets = parse_net_tcp(net_tcp)
        listener = next(s for s in sockets if s.inode == LISTENER_INODE)
        assert listener.local_address == "127.0.0.1"
        assert listener.local_port == 8080
        assert listener.state is TcpState.LISTEN
        assert listener.uid == 1000

    def test_a_wildcard_listener(self, net_tcp):
        """`0.0.0.0:5432` - bound to every interface, which is the common case
        for a database in a container and the one that surprises people."""
        sockets = parse_net_tcp(net_tcp)
        pg = next(s for s in sockets if s.inode == PG_LISTENER_INODE)
        assert pg.local_address == "0.0.0.0"
        assert pg.local_port == 5432

    def test_time_wait_rows_have_inode_zero(self, net_tcp):
        """Three of them in the fixture. **Not a parse error** - the socket
        genuinely belongs to no process any more."""
        sockets = parse_net_tcp(net_tcp)
        time_waits = [s for s in sockets if s.state is TcpState.TIME_WAIT]
        assert len(time_waits) == 3
        assert all(s.inode == 0 for s in time_waits)

    def test_a_close_wait_socket_is_parsed(self, net_tcp):
        """`CLOSE_WAIT` means *your* application has not called close(). A pile of
        these is an application bug, unlike `TIME_WAIT` which is usually normal -
        telling them apart is half of why this tool is useful."""
        sockets = parse_net_tcp(net_tcp)
        assert any(s.state is TcpState.CLOSE_WAIT for s in sockets)

    def test_the_remote_end_is_decoded_too(self, net_tcp):
        sockets = parse_net_tcp(net_tcp)
        established = next(s for s in sockets if s.inode == ESTABLISHED_INODE)
        assert established.remote_address == "127.0.0.1"
        assert established.remote_port == 50000

    def test_pids_are_not_resolved_by_the_parser(self, net_tcp):
        """The fd join is a separate pass - it costs a walk of every process, and
        the caller may not need it (`summary` does not)."""
        assert all(s.pid is None for s in parse_net_tcp(net_tcp))

    def test_a_blank_trailing_line_is_not_a_row(self, net_tcp):
        """Normal in `/proc`. Letting `fields[1]` raise on it is not."""
        assert len(parse_net_tcp(net_tcp + "\n")) == 9

    def test_an_empty_table_is_an_empty_list(self):
        """Just the header - a host with no TCP sockets at all. Rare, but
        `lines[1:]` on a one-line file must not raise."""
        header = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt\n"
        assert parse_net_tcp(header) == []


class TestIpv6Table:
    def test_tcp6_uses_the_same_column_layout(self, net_tcp6):
        """Only the address decoding differs - one parameter threaded through,
        not a second parser."""
        assert len(parse_net_tcp(net_tcp6, ipv6=True)) == 3

    def test_an_ipv4_mapped_listener_is_visible(self, net_tcp6):
        sockets = parse_net_tcp(net_tcp6, ipv6=True)
        assert any(s.local_address == "::ffff:10.0.0.5" for s in sockets)


class TestInodeJoin:
    def test_a_socket_is_attributed_to_its_process(self, fd_tree, net_tcp):
        root = fd_tree({1217: [LISTENER_INODE]}, commands={1217: "python3"})
        inode_map, _ = build_inode_map(LiveProcSource(root=root))
        joined = attach_pids(parse_net_tcp(net_tcp), inode_map)
        listener = next(s for s in joined if s.inode == LISTENER_INODE)
        assert listener.pid == 1217
        assert listener.command == "python3"

    def test_non_socket_fds_are_ignored(self, fd_tree, net_tcp):
        """The fixture gives every process a `/dev/null` and a `pipe:[...]` fd.
        An unanchored regex would match the pipe; a missing guard would crash."""
        root = fd_tree({1217: [LISTENER_INODE]})
        inode_map, _ = build_inode_map(LiveProcSource(root=root))
        assert set(inode_map) == {LISTENER_INODE}

    def test_the_map_is_built_once_for_the_whole_table(self, fd_tree, net_tcp):
        """Shape test, but the shape is the performance characteristic: on a box
        with 28,000 TIME_WAIT sockets, a per-socket walk is why your tool hangs."""
        root = fd_tree({1217: [LISTENER_INODE], 1301: [PG_LISTENER_INODE]})
        inode_map, _ = build_inode_map(LiveProcSource(root=root))
        assert len(inode_map) == 2

    def test_inode_zero_is_never_looked_up(self, fd_tree, net_tcp):
        """If inode 0 ever appeared in the map it would attribute every orphaned
        TIME_WAIT socket to one unlucky process."""
        root = fd_tree({1217: [LISTENER_INODE]})
        inode_map, _ = build_inode_map(LiveProcSource(root=root))
        joined = attach_pids(parse_net_tcp(net_tcp), inode_map)
        assert all(s.pid is None for s in joined if s.inode == 0)

    def test_an_unmapped_inode_keeps_pid_none(self, fd_tree, net_tcp):
        root = fd_tree({1217: [LISTENER_INODE]})
        inode_map, _ = build_inode_map(LiveProcSource(root=root))
        joined = attach_pids(parse_net_tcp(net_tcp), inode_map)
        assert next(s for s in joined if s.inode == PG_LISTENER_INODE).pid is None

    def test_inaccessible_processes_are_counted_not_dropped(self, fd_tree):
        """**The acceptance criterion.**

        A mode-000 `fd` directory stands in for another user's process. Running
        as non-root you genuinely cannot see those sockets - `ss -p` cannot
        either - but silently pretending the process has no sockets is the
        failure. Count them and let the CLI say so.
        """
        root = fd_tree({1217: [ESTABLISHED_INODE]}, unreadable_pids=[2000])
        _, inaccessible = build_inode_map(LiveProcSource(root=root))
        assert inaccessible == 1

    def test_a_process_that_exits_mid_walk_is_skipped_silently(self, fd_tree):
        """E13's "that is Tuesday" case. Does not need counting separately."""
        root = fd_tree({1217: [LISTENER_INODE]})
        (root / "9999").mkdir()
        inode_map, inaccessible = build_inode_map(LiveProcSource(root=root))
        assert inode_map
        assert inaccessible == 0


class TestWhoHasPort:
    def test_the_listener_sorts_first(self, fd_tree, net_tcp):
        """On a busy box the listener is what the asker wants, and it would
        otherwise be buried under hundreds of ESTABLISHED rows on the same port."""
        root = fd_tree({1217: [LISTENER_INODE]})
        inode_map, _ = build_inode_map(LiveProcSource(root=root))
        found = who_has_port(attach_pids(parse_net_tcp(net_tcp), inode_map), 8080)
        assert found[0].state is TcpState.LISTEN

    def test_every_socket_touching_the_port_is_returned(self, net_tcp):
        """Local **and** remote ends. A connection *to* port 8080 is on port 8080
        as far as "what is using this port" goes."""
        found = who_has_port(parse_net_tcp(net_tcp), 8080)
        assert len(found) > 1

    def test_a_port_with_only_time_wait_rows_is_the_answer_to_a_bind_failure(self, net_tcp):
        """Port 50001-50003 in the fixture are TIME_WAIT only.

        "Nothing is listening, but N sockets are in TIME_WAIT and will clear in
        up to 60s" **is** the explanation for a bind failure. Printing "not
        found" sends the reader looking for a process that does not exist.
        """
        found = who_has_port(parse_net_tcp(net_tcp), 50001)
        assert found
        assert all(s.state is TcpState.TIME_WAIT for s in found)

    def test_an_unused_port_is_empty(self, net_tcp):
        assert who_has_port(parse_net_tcp(net_tcp), 9999) == []


def test_the_live_comparison():
    """A procedure, not an assertion - and the exercise's real deliverable.

    Run `sockstat list` and `ss -tanp` side by side in the container and explain
    every difference in `DECISIONS.md`. Expect to find: sockets owned by other
    users (invisible to both without root), `TIME_WAIT` rows `ss` shows with no
    process, and the socket `ss` itself opened.

    Delete this test once written up.
    """
    raise AssertionError("implement: run the live comparison, record it, delete this test")

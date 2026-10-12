"""Contract for the hex decoders. Four tests here are the acceptance criteria.

`test_loopback_is_not_reversed` is the one the brief calls out by name, and it is
the whole exercise in one assertion: `0100007F` is `127.0.0.1`, not `1.0.0.127`.
"""

from __future__ import annotations

import pytest

from sockstat.decode import (
    decode_address,
    decode_ipv4,
    decode_ipv6,
    decode_port,
    decode_state,
)
from sockstat.models import TcpState


class TestPort:
    @pytest.mark.parametrize(
        ("hex_port", "expected"),
        [("1F90", 8080), ("1538", 5432), ("0050", 80), ("0016", 22), ("0000", 0)],
    )
    def test_ports_are_plain_big_endian(self, hex_port, expected):
        """The easy half - and it being easy is what makes the address
        surprising. Same file, same row, different byte order."""
        assert decode_port(hex_port) == expected


class TestIpv4:
    def test_loopback_is_not_reversed(self):
        """**The test the brief insists on.**

        `0100007F` is `127.0.0.1`. An implementation that reads the hex left to
        right produces `1.0.0.127`, which is a valid-looking address pointing
        somewhere entirely different - the worst kind of bug to have in a tool
        you are using to diagnose something else.
        """
        assert decode_ipv4("0100007F") == "127.0.0.1"

    def test_any_address(self):
        assert decode_ipv4("00000000") == "0.0.0.0"

    @pytest.mark.parametrize(
        ("hex_addr", "expected"),
        [("020011AC", "172.17.0.2"), ("010011AC", "172.17.0.1")],
    )
    def test_docker_bridge_addresses(self, hex_addr, expected):
        """The addresses you will actually see doing this in a container."""
        assert decode_ipv4(hex_addr) == expected

    def test_it_is_host_byte_order_not_protocol_byte_order(self):
        """Worth stating as a test so the reasoning is recorded somewhere.

        The kernel dumps the raw in-memory `u32`. On x86/ARM that is
        little-endian, hence the reversal. On a big-endian machine this file
        would print `7F000001` for the same address - you will never meet one,
        and knowing why the caveat exists is the difference between understanding
        this and memorising it.
        """
        assert decode_ipv4("0100007F") == "127.0.0.1"


class TestIpv6:
    def test_loopback(self):
        assert decode_ipv6("00000000000000000000000001000000") == "::1"

    def test_unspecified(self):
        """`::` - a dual-stack listener bound to everything."""
        assert decode_ipv6("00000000000000000000000000000000") == "::"

    def test_an_ipv4_mapped_address(self):
        """**The acceptance criterion, and the one with a real consequence.**

        This is how a dual-stack listener on `0.0.0.0` shows up in
        `/proc/net/tcp6`. Get it wrong and you conclude a service is not
        listening when it is.
        """
        assert decode_ipv6("0000000000000000FFFF00000500000A") == "::ffff:10.0.0.5"

    def test_reversal_is_per_word_not_across_the_whole_address(self):
        """The bug this test exists to catch.

        The format is four 32-bit words, **each** in host order - so you reverse
        within each 4-byte group, not across all sixteen bytes. Reversing all
        sixteen turns `::ffff:10.0.0.5` into `::ffff:0:a00:5`, which looks like a
        real IPv6 address and is not the one you wanted.
        """
        assert decode_ipv6("0000000000000000FFFF00000100007F") == "::ffff:127.0.0.1"


class TestDecodeAddress:
    def test_splits_and_decodes_both_halves(self):
        assert decode_address("0100007F:1F90") == ("127.0.0.1", 8080)

    def test_ipv6_variant(self):
        assert decode_address("00000000000000000000000001000000:0050", ipv6=True) == ("::1", 80)


class TestDecodeState:
    @pytest.mark.parametrize(
        ("hex_state", "expected"),
        [
            ("01", TcpState.ESTABLISHED),
            ("06", TcpState.TIME_WAIT),
            ("08", TcpState.CLOSE_WAIT),
            ("0A", TcpState.LISTEN),
        ],
    )
    def test_known_states(self, hex_state, expected):
        assert decode_state(hex_state) is expected

    def test_an_unknown_state_raises_rather_than_becoming_a_string(self):
        """A silent `"UNKNOWN"` would be counted in `sockstat summary` as if it
        were a real state, and then your totals disagree with `ss -s` for no
        visible reason."""
        with pytest.raises(ValueError, match="FF"):
            decode_state("FF")

    def test_time_wait_is_an_orphan_state(self):
        """`TIME_WAIT` sockets have inode 0 - the process is gone and the kernel
        is holding the tuple for 2*MSL so a late duplicate packet cannot be
        mistaken for part of a new connection. This is why `ss -p` shows nothing
        for them."""
        assert TcpState.TIME_WAIT.is_orphan is True
        assert TcpState.LISTEN.is_orphan is False

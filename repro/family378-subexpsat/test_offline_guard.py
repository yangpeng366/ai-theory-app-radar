"""The offline guard in ``conftest.py`` must actually bite.

Without these two tests the guard is an untested fixture: a suite that never
touches the network also never proves the guard is installed, so a future test
that *does* fetch would pass locally and in CI.  These tests open a real socket
and resolve a real name on purpose, and expect the guard to refuse both.
"""

import socket

import pytest


def test_guard_refuses_a_dns_lookup():
    with pytest.raises(RuntimeError, match="offline test guard"):
        socket.getaddrinfo("api.github.com", 443)


def test_guard_refuses_a_non_loopback_connection():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        with pytest.raises(RuntimeError, match="offline test guard"):
            sock.connect(("93.184.216.34", 80))

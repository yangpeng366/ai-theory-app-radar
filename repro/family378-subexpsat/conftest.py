"""Offline guard for the family-378 review tooling.

The whole point of this suite is that a stranger can verify the review tools
without fetching anything from openai/math.  The test modules replace
``urllib.request.urlopen`` (see ``test_fetch_sources.py``) or ``fetch_one``
before any request can happen, so the suite is *already* offline; this fixture
makes a regression loud instead of slow: any socket connect or DNS lookup for a
non-loopback host fails the test that attempted it.

Run from the repository root:
    python -m pytest repro/family378-subexpsat -q
"""

import socket

import pytest

LOOPBACK = {"127.0.0.1", "::1", "localhost", "ip6-localhost", ""}


@pytest.fixture(autouse=True)
def offline_network_guard(monkeypatch):
    """Refuse real network I/O for every test in this directory."""
    real_connect = socket.socket.connect

    def guard_connect(self, address):
        host = address[0] if isinstance(address, tuple) and address else address
        if host not in LOOPBACK:
            raise RuntimeError(
                "offline test guard: refusing a network connection to %r; stub "
                "urllib.request.urlopen or fetch_one instead" % (host,))
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guard_connect)

    real_getaddrinfo = socket.getaddrinfo

    def guard_getaddrinfo(host, *args, **kwargs):
        if host in LOOPBACK:
            return real_getaddrinfo(host, *args, **kwargs)
        raise RuntimeError(
            "offline test guard: refusing a DNS lookup for %r; the review set must "
            "be verifiable without network access" % (host,))

    monkeypatch.setattr(socket, "getaddrinfo", guard_getaddrinfo)

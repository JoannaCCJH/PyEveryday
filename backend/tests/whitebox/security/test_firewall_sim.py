"""Whitebox coverage for ``scripts/security/firewall_sim.py``.

The module is short but has every branch we want to lock down:

* ``generate_ip``: returns a deterministic IP within the documented range
  when ``random.randint`` is patched.
* ``check_firewall_action``: matching IP -> rule action; no match -> default
  ``ALLOW!!``.
* ``main``: the loop runs 12 iterations and prints lines.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from scripts.security import firewall_sim as fs


class TestGenerateIp:
    @pytest.mark.parametrize("rand,expected", [
        (0, "192.168.1.0"),
        (15, "192.168.1.15"),
        (20, "192.168.1.20"),
    ])
    def test_returns_in_range(self, rand, expected):
        with patch("scripts.security.firewall_sim.random.randint", return_value=rand):
            assert fs.generate_ip() == expected


class TestCheckFirewallAction:
    @pytest.fixture
    def rules(self):
        return {"192.168.1.1": "Block", "192.168.1.7": "Block"}

    def test_match(self, rules):
        assert fs.check_firewall_action("192.168.1.1", rules) == "Block"

    def test_no_match(self, rules):
        assert fs.check_firewall_action("192.168.1.42", rules) == "ALLOW!!"

    def test_empty_rules(self):
        assert fs.check_firewall_action("1.2.3.4", {}) == "ALLOW!!"


class TestMain:
    def test_loops_12_times(self, capsys):
        with patch("scripts.security.firewall_sim.generate_ip",
                   return_value="192.168.1.1"):
            fs.main()
        # Each iteration prints exactly one line; 12 iterations -> 12 lines.
        out = capsys.readouterr().out.strip().splitlines()
        assert len(out) == 12
        assert all(line.startswith("IP:192.168.1.1") for line in out)

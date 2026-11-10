"""Offline regression tests for check-gap.py's C16 branch."""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check-gap.py")


def _load():
    spec = importlib.util.spec_from_file_location("check_gap", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cg = _load()


class _HugeEncodedFormula:
    def __len__(self):
        return 10 ** 9


def test_c16_failure_branch_reports_violations(monkeypatch):
    captured = []
    monkeypatch.setattr(cg, "encode_cnf_python",
                        lambda n, clauses: _HugeEncodedFormula())
    monkeypatch.setattr(cg, "record",
                        lambda *args: captured.append(args))

    cg.check_encoding_bounds()

    assert len(captured) == 1
    assert captured[0][1] == "FAIL"
    assert "samples violate" in captured[0][2]


def test_c16_pass_branch_reports_sample_count(monkeypatch):
    captured = []
    monkeypatch.setattr(cg, "record",
                        lambda *args: captured.append(args))

    cg.check_encoding_bounds()

    assert len(captured) == 1
    assert captured[0][1] == "PASS"
    assert "sampled formulas satisfy" in captured[0][2]


def test_rho_is_larger_than_paper_main_exponent():
    n = 10 ** 12
    assert cg.rho(n) > cg.paper_main(n) > 0

"""Offline regression tests for check-gap.py's C14, C16 and C20/C21 verdicts."""

import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check-gap.py")

# The two `rho` bodies C14 must tell apart: the fetched definition and the same
# definition without the square (which is the manuscript's own exponent).
RHO_SQUARED = ("def rho (n : ℕ) : ℝ :=\n"
               "(n : ℝ) * (Real.logb 2 (Real.logb 2 n)) ^ 2 / Real.sqrt (Real.logb 2 n)")
RHO_SINGLE = ("def rho (n : ℕ) : ℝ :=\n"
              "(n : ℝ) * Real.logb 2 (Real.logb 2 n) / Real.sqrt (Real.logb 2 n)")


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


def _capture(monkeypatch):
    captured = []
    monkeypatch.setattr(cg, "record", lambda *args: captured.append(args))
    return captured


def test_c14_passes_on_the_fetched_definition(monkeypatch):
    captured = _capture(monkeypatch)

    rows = cg.check_exponent_gap(RHO_SQUARED)

    assert len(rows) == len(cg.C14_SAMPLES)
    assert [check for check, _v, _d in captured] == ["C14 指数差"]
    assert captured[0][1] == "PASS"
    assert "log2 log2 n" in captured[0][2]


def test_c14_goes_red_when_the_lean_body_loses_its_square(monkeypatch):
    # A source edit, not a numeric edge case: the mirrored formula would drift.
    captured = _capture(monkeypatch)

    rows = cg.check_exponent_gap(RHO_SINGLE)

    assert len(rows) == len(cg.C14_SAMPLES)
    assert captured[0][1] == "FAIL"
    assert "no longer n*(log2 log2 n)^2" in captured[0][2]


def test_c14_goes_red_when_rho_collapses_to_the_paper_exponent(monkeypatch):
    # If the Lean exponent equalled Theorem 1.1's there would be no gap at all;
    # C14 must say "not above" instead of printing a ratio as a PASS.
    monkeypatch.setattr(cg, "rho", cg.paper_main)
    captured = _capture(monkeypatch)

    cg.check_exponent_gap(RHO_SQUARED)

    assert captured[0][1] == "FAIL"
    assert "is not above the manuscript main exponent" in captured[0][2]


def test_c14_goes_red_when_the_gap_is_a_constant_factor(monkeypatch):
    # A constant-factor discrepancy is Theta(1), not Theta(log log n): the
    # identity check has to fail even though rho is still strictly larger.
    monkeypatch.setattr(cg, "rho", lambda n: 2 * cg.paper_main(n))
    captured = _capture(monkeypatch)

    cg.check_exponent_gap(RHO_SQUARED)

    assert captured[0][1] == "FAIL"
    assert "rho/main=2.000000" in captured[0][2]
    assert "log2 log2 n=" in captured[0][2]


def test_c14_goes_red_when_the_sharpening_ratio_stops_squaring(monkeypatch):
    # The m<=Dn column is rho/paper_sharp = (log2 log2 n)^2; feeding the main
    # exponent there breaks that identity, so C14 must not stay green.
    monkeypatch.setattr(cg, "paper_sharp", cg.paper_main)
    captured = _capture(monkeypatch)

    cg.check_exponent_gap(RHO_SQUARED)

    assert captured[0][1] == "FAIL"
    assert "rho/sharpening=" in captured[0][2]


def test_c20_c21_skip_with_a_reason_when_paper_pdf_is_absent(monkeypatch, tmp_path):
    # SKIP is the chosen verdict when the PDF cannot be read at all; PART is
    # retired, and no dependency problem may look like a partial pass.
    docs = tmp_path / "lean" / "docs"
    docs.mkdir(parents=True)
    (docs / "378.md").write_text("m\\le Dn is not formalised\n", encoding="utf-8")
    captured = _capture(monkeypatch)

    cg.stage3(str(tmp_path), {"final": ""})

    verdicts = {check.split()[0]: (verdict, detail)
                for check, verdict, detail in captured}
    assert verdicts["C20"][0] == "SKIP"
    assert verdicts["C21"][0] == "SKIP"
    assert "PART" not in [verdict for verdict, _detail in verdicts.values()]
    assert "paper.pdf not fetched" in verdicts["C20"][1]

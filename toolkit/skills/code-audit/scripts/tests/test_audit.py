"""Unit tests for audit.py. Run from the scripts folder: python -m unittest discover -s tests"""
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import audit  # noqa: E402


def sh(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True)


NL = chr(10)
LAUNCH = [None]  # the repo the "shell" is in; tests stand in for the working directory


def make_repo(tmp: Path, branch: str = "main") -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    sh(repo, "init", "-b", branch)
    (repo / "a.py").write_text("x = 1\n")
    (repo / "b.ts").write_text("export const b = 1;\n")
    sh(repo, "add", ".")
    sh(repo, "commit", "-m", "init")
    LAUNCH[0] = repo.resolve()
    return repo.resolve()


class TempCase(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name).resolve()
        self.addCleanup(self._td.cleanup)
        patcher = mock.patch.object(audit, "_cwd", lambda: LAUNCH[0] or Path.cwd())
        patcher.start()
        self.addCleanup(patcher.stop)


class ScopeTests(TempCase):
    def test_diff_scope_is_changed_plus_untracked(self):
        repo = make_repo(self.tmp)
        sh(repo, "checkout", "-b", "feat")
        (repo / "a.py").write_text("x = 2\n")
        sh(repo, "commit", "-am", "change a")
        (repo / "new.py").write_text("y = 1\n")  # untracked
        scope = audit.resolve_scope(repo, full=False)
        self.assertEqual(scope["mode"], "diff")
        self.assertEqual(scope["files"], ["a.py", "new.py"])

    def test_full_scope_is_every_tracked_file(self):
        repo = make_repo(self.tmp)
        scope = audit.resolve_scope(repo, full=True)
        self.assertEqual(scope["files"], ["a.py", "b.ts"])

    def test_falls_back_to_master(self):
        repo = make_repo(self.tmp, branch="master")
        sh(repo, "checkout", "-b", "feat")
        (repo / "a.py").write_text("x = 3\n")
        scope = audit.resolve_scope(repo, full=False)
        self.assertEqual((scope["mode"], scope["base_branch"], scope["files"]), ("diff", "master", ["a.py"]))

    def test_no_base_branch_falls_back_to_full_with_notice(self):
        repo = make_repo(self.tmp, branch="trunk")
        scope = audit.resolve_scope(repo, full=False)
        self.assertEqual(scope["mode"], "full")
        self.assertIn("whole repository", scope["notice"])

    def test_deleted_files_are_not_in_scope(self):
        repo = make_repo(self.tmp)
        sh(repo, "checkout", "-b", "feat")
        sh(repo, "rm", "b.ts")
        sh(repo, "commit", "-m", "rm")
        self.assertEqual(audit.resolve_scope(repo, False)["files"], [])

    def test_nothing_to_audit_exits_3_and_suggests_full(self):
        repo = make_repo(self.tmp)
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = audit.main(["--init", "--repo", str(repo)])
        self.assertEqual(rc, audit.EXIT_NOTHING)
        self.assertIn("--full", buf.getvalue())

    def init(self, repo, *extra):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = audit.main(["--init", "--repo", str(repo), *extra])
        return rc, buf.getvalue()

    def test_evidence_lives_in_the_repos_code_audit_folder_and_is_self_ignored(self):
        repo = make_repo(self.tmp)
        (repo / "a.py").write_text("x = 9" + NL)
        rc, out = self.init(repo)
        self.assertEqual(rc, audit.EXIT_OK)
        ev = Path(json.loads(out)["evidence"])
        self.assertTrue((ev / "scope.json").is_file() and (ev / "snapshot.json").is_file())
        self.assertEqual(ev.parent, repo / audit.WORKSPACE)
        self.assertEqual((repo / audit.WORKSPACE / ".gitignore").read_text().strip(), "*")
        status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "-uall"],
                                capture_output=True, text=True).stdout
        self.assertNotIn(audit.WORKSPACE, status)  # git never lists the workspace

    def test_workspace_files_are_never_in_scope_or_snapshot(self):
        repo = make_repo(self.tmp)
        (repo / "a.py").write_text("x = 9" + NL)
        _, out = self.init(repo)
        ev = Path(json.loads(out)["evidence"])
        self.assertTrue(all(not f.startswith("code-audit/") for f in json.loads((ev / "scope.json").read_text())["files"]))
        (ev / "extra.json").write_text("{}")  # the audit writing its own evidence is not tampering
        self.assertEqual(audit.diff_snapshots(json.loads((ev / "snapshot.json").read_text()),
                                              audit.take_snapshot(repo, ["a.py"])), [])

    def test_evidence_outside_the_workspace_is_refused(self):
        repo = make_repo(self.tmp)
        (repo / "a.py").write_text("x = 9" + NL)
        _, out = self.init(repo)
        real = Path(json.loads(out)["evidence"])
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "scope.json").write_text((real / "scope.json").read_text())
        with mock.patch("sys.stderr", io.StringIO()) as err:
            self.assertEqual(audit.main(["--verify", "--evidence", str(elsewhere)]), audit.EXIT_ERROR)
        self.assertIn("evidence must be inside", err.getvalue())

    def test_save_report_writes_only_report_md_in_the_run_folder(self):
        repo = make_repo(self.tmp)
        (repo / "a.py").write_text("x = 9" + NL)
        _, out = self.init(repo)
        ev = Path(json.loads(out)["evidence"])
        with mock.patch("sys.stdin", mock.Mock(buffer=io.BytesIO(b"# report"))), redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(["--save-report", "--evidence", str(ev)]), audit.EXIT_OK)
        self.assertEqual((ev / "report.md").read_text(), "# report")

    def test_scanners_are_told_to_skip_the_workspace(self):
        p = Path("/x")
        self.assertIn("code-audit", audit.cmd_semgrep("semgrep", ["."], "c"))
        self.assertIn("**/code-audit/**", audit.cmd_jscpd("jscpd", p, ["."]))
        self.assertIn("code-audit", audit.cmd_trivy("trivy", p))


class LaunchRepoOnlyTests(TempCase):
    def test_init_refuses_a_repo_the_cwd_is_not_in(self):
        other = make_repo(self.tmp)
        (other / "a.py").write_text("x = 9\n")
        LAUNCH[0] = self.tmp  # launched somewhere else
        err = io.StringIO()
        with mock.patch("sys.stderr", err):
            rc = audit.main(["--init", "--repo", str(other)])
        self.assertEqual(rc, audit.EXIT_ERROR)
        self.assertIn("only covers the repository it is launched in", err.getvalue())
        self.assertFalse((self.tmp / "ev").exists())

    def test_phase_and_verify_refuse_evidence_for_another_repo(self):
        repo = make_repo(self.tmp)
        (repo / "a.py").write_text("x = 9\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            audit.main(["--init", "--repo", str(repo)])
        ev = json.loads(buf.getvalue())["evidence"]
        LAUNCH[0] = self.tmp  # now launched elsewhere, pointing at that evidence
        with mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(audit.main(["--phase", "0", "--evidence", ev]), audit.EXIT_ERROR)
            self.assertEqual(audit.main(["--verify", "--evidence", ev]), audit.EXIT_ERROR)

    def test_subfolder_of_the_repo_is_fine(self):
        repo = make_repo(self.tmp)
        LAUNCH[0] = repo / "api"
        audit.require_launch_repo(repo)  # no exception


class Phase0Tests(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = make_repo(self.tmp)
        self.ev = self.tmp / "ev"
        self.ev.mkdir()

    def run_p0(self, files, ruff_json):
        with mock.patch.object(audit, "find_tool", lambda name, _dirs=None: "/fake/ruff" if name == "ruff" else None), \
             mock.patch.object(audit, "run", return_value=(0, ruff_json, "")):
            return audit.run_phase0(self.repo, self.ev, files, 5)

    def test_syntax_error_fails_gate(self):
        out = json.dumps([{"code": None, "message": "SyntaxError: invalid syntax", "filename": str(self.repo / "a.py"),
                           "location": {"row": 1, "column": 1}}])
        res = self.run_p0(["a.py"], out)
        self.assertEqual(res["gate"], "fail")
        self.assertEqual(res["gate_errors"][0]["file"], "a.py")
        self.assertTrue((self.ev / "phase0.json").is_file())

    def test_e9_code_fails_gate(self):
        out = json.dumps([{"code": "E902", "message": "io", "filename": "a.py", "location": {"row": 1}}])
        self.assertEqual(self.run_p0(["a.py"], out)["gate"], "fail")

    def test_lint_only_passes_gate_and_is_a_finding(self):
        out = json.dumps([{"code": "E501", "message": "line too long", "filename": str(self.repo / "a.py"),
                           "location": {"row": 3, "column": 1}}])
        res = self.run_p0(["a.py"], out)
        self.assertEqual(res["gate"], "pass")
        self.assertEqual([f["rule"] for f in res["findings"]], ["E501"])
        self.assertEqual(res["findings"][0]["severity"], "Low")

    def test_missing_tool_is_skipped_not_failed(self):
        with mock.patch.object(audit, "find_tool", return_value=None):
            res = audit.run_phase0(self.repo, self.ev, ["a.py"], 5)
        self.assertEqual(res["gate"], "pass")
        self.assertEqual(res["tools"]["ruff"]["status"], "skipped")
        self.assertIn("not installed", res["tools"]["ruff"]["reason"])

    def test_language_not_present_is_not_reported(self):
        with mock.patch.object(audit, "find_tool", return_value=None):
            res = audit.run_phase0(self.repo, self.ev, ["a.py"], 5)
        self.assertNotIn("tsc", res["tools"])
        self.assertNotIn("eslint", res["tools"])
        self.assertNotIn("clippy", res["tools"])

    def test_crash_with_no_output_is_failed_not_clean(self):
        with mock.patch.object(audit, "find_tool", lambda n, _d=None: "/fake/ruff" if n == "ruff" else None),              mock.patch.object(audit, "run", return_value=(2, "", "boom")):
            res = audit.run_phase0(self.repo, self.ev, ["a.py"], 5)
        self.assertEqual(res["tools"]["ruff"]["status"], "failed")
        self.assertIn("boom", res["tools"]["ruff"]["reason"])

    def test_unparseable_output_is_failed_not_a_crash(self):
        res = self.run_p0(["a.py"], "not json")
        self.assertEqual(res["tools"]["ruff"]["status"], "failed")
        self.assertEqual(res["gate"], "pass")

    def test_mypy_and_tsc_errors_are_gate_failures(self):
        _, gate = audit.parse_mypy("pkg/m.py:4:5: error: Incompatible types  [assignment]\n", self.repo, self.repo)
        self.assertEqual((gate[0]["rule"], gate[0]["line"]), ("assignment", 4))
        _, gate = audit.parse_tsc("src/a.ts(7,3): error TS2322: Type 'string' is not assignable.\n", self.repo, self.repo)
        self.assertEqual((gate[0]["rule"], gate[0]["line"]), ("TS2322", 7))

    def test_eslint_fatal_is_gate_and_rule_is_finding(self):
        out = json.dumps([{"filePath": str(self.repo / "b.ts"), "messages": [
            {"ruleId": None, "severity": 2, "fatal": True, "message": "Parsing error", "line": 2},
            {"ruleId": "no-unused-vars", "severity": 1, "message": "unused", "line": 1}]}])
        findings, gate = audit.parse_eslint(out, self.repo, self.repo)
        self.assertEqual(len(gate), 1)
        self.assertEqual((findings[0]["rule"], findings[0]["severity"]), ("no-unused-vars", "Low"))


class Phase1Tests(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = make_repo(self.tmp)
        self.ev = self.tmp / "ev"
        self.ev.mkdir()

    def test_missing_tools_are_skipped_and_summary_written(self):
        with mock.patch.object(audit, "find_tool", return_value=None):
            summary = audit.run_phase1(self.repo, self.ev, ["a.py"], 5, False)
        for tool in ("gitleaks", "semgrep", "jscpd", "trivy"):
            self.assertEqual(summary["phase1_tools"][tool]["status"], "skipped")
        self.assertTrue((self.ev / "summary.json").is_file())

    def test_phase1_exit_code_is_zero_when_tools_missing(self):
        sh(self.repo, "checkout", "-b", "feat")
        (self.repo / "a.py").write_text("x = 5\n")
        buf = io.StringIO()
        with redirect_stdout(buf):
            audit.main(["--init", "--repo", str(self.repo)])
        ev = json.loads(buf.getvalue())["evidence"]
        with mock.patch.object(audit, "find_tool", return_value=None), redirect_stdout(io.StringIO()):
            rc = audit.main(["--phase", "1", "--evidence", ev])
        self.assertEqual(rc, audit.EXIT_OK)

    def test_tool_that_exits_nonzero_with_no_output_is_failed_not_clean(self):
        with mock.patch.object(audit, "find_tool", lambda n, d=None: "/fake/" + n),              mock.patch.object(audit, "run", return_value=(1, "", "")):
            summary = audit.run_phase1(self.repo, self.ev, ["a.py"], 5, False)
        for tool in ("semgrep", "trivy"):
            self.assertEqual(summary["phase1_tools"][tool]["status"], "failed", tool)

    def test_semgrep_normalized_and_filtered_to_scope(self):
        raw = json.dumps({"results": [
            {"check_id": "r.sqli", "path": "a.py", "start": {"line": 3}, "extra": {"severity": "ERROR", "message": "sqli"}},
            {"check_id": "r.other", "path": "zzz.py", "start": {"line": 1}, "extra": {"severity": "WARNING", "message": "x"}}]})
        found = audit.filter_to_scope(audit.parse_semgrep(raw, self.repo), {"a.py"})
        self.assertEqual([(f["file"], f["severity"], f["line"]) for f in found], [("a.py", "Critical", 3)])

    def test_trivy_gitleaks_jscpd_normalization(self):
        tv = json.dumps({"Results": [{"Target": "package-lock.json", "Vulnerabilities": [
            {"VulnerabilityID": "CVE-1", "PkgName": "x", "Severity": "HIGH", "Title": "t"},
            {"VulnerabilityID": "CVE-2", "PkgName": "y", "Severity": "LOW", "Title": "t"}]}]})
        self.assertEqual([f["severity"] for f in audit.parse_trivy(tv)], ["Critical", "Low"])
        gl = json.dumps([{"RuleID": "aws-key", "File": str(self.repo / "a.py"), "StartLine": 2, "Description": "key"}])
        self.assertEqual(audit.parse_gitleaks(gl, self.repo)[0]["file"], "a.py")
        jc = json.dumps({"duplicates": [{"lines": 12, "firstFile": {"name": "old.py", "start": 1},
                                         "secondFile": {"name": str(self.repo / "a.py"), "start": 9}}]})
        f = audit.parse_jscpd(jc, self.repo, {"a.py"})[0]
        self.assertEqual((f["file"], f["line"], f["severity"]), ("a.py", 9, "Low"))

    def test_severity_mapping(self):
        m = audit.map_severity
        self.assertEqual(m("gitleaks", "x"), "Critical")
        self.assertEqual([m("semgrep", s) for s in ("ERROR", "WARNING", "INFO")], ["Critical", "Medium", "Low"])
        self.assertEqual([m("trivy", s) for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN")],
                         ["Critical", "Critical", "Medium", "Low", "Low"])
        self.assertEqual(m("ruff", None, "F401"), "Medium")
        self.assertEqual(m("ruff", None, "E501"), "Low")
        self.assertEqual(m("jscpd", "x"), "Low")


class ReadOnlyTests(TempCase):
    def all_commands(self):
        p = Path("/x")
        return [
            audit.cmd_ruff("ruff", ["a.py"]), audit.cmd_mypy("mypy", ["a.py"], p), audit.cmd_tsc("tsc", p),
            audit.cmd_eslint("eslint", ["a.ts"]), audit.cmd_clippy("cargo", p),
            audit.cmd_gitleaks("gitleaks", p, p), audit.cmd_semgrep("semgrep", ["."], "p/default"),
            audit.cmd_jscpd("jscpd", p, ["."]), audit.cmd_trivy("trivy", p),
        ]

    def test_no_generated_command_has_a_fix_flag(self):
        for cmd in self.all_commands():
            self.assertFalse(set(cmd) & audit.FIX_FLAGS, cmd)
            self.assertFalse([a for a in cmd if a.startswith("--fix") or a.startswith("--autofix")], cmd)

    def test_run_refuses_a_fix_flag(self):
        for flag in ("--fix", "--autofix", "--fix=true"):
            with self.assertRaises(RuntimeError):
                audit.assert_report_only(["ruff", "check", flag])

    def test_caches_are_not_written_into_the_repo(self):
        self.assertIn("--no-cache", audit.cmd_ruff("ruff", []))
        self.assertIn("--cache-dir", audit.cmd_mypy("mypy", [], Path("/e")))
        self.assertEqual(audit.cmd_tsc("tsc", Path("/p"))[audit.cmd_tsc("tsc", Path("/p")).index("--incremental") + 1], "false")
        self.assertIn("--target-dir", audit.cmd_clippy("cargo", Path("/e")))


class TamperTests(TempCase):
    def setUp(self):
        super().setUp()
        self.repo = make_repo(self.tmp)
        sh(self.repo, "checkout", "-b", "feat")
        (self.repo / "a.py").write_text("x = 2\n")
        (self.repo / "scratch.txt").write_text("u\n")  # untracked
        self.scope = audit.resolve_scope(self.repo, False)
        self.before = audit.take_snapshot(self.repo, self.scope["files"])

    def changes(self):
        return audit.diff_snapshots(self.before, audit.take_snapshot(self.repo, self.scope["files"]))

    def test_unchanged_repo_is_clean(self):
        self.assertEqual(self.changes(), [])

    def test_modified_file_is_named(self):
        (self.repo / "a.py").write_text("x = 3\n")
        self.assertIn("modified: a.py", self.changes())

    def test_modified_untracked_file_is_named(self):
        (self.repo / "scratch.txt").write_text("changed\n")
        self.assertIn("modified: scratch.txt", self.changes())

    def test_added_file_is_named(self):
        (self.repo / "evil.py").write_text("boom\n")
        self.assertIn("added: evil.py", self.changes())

    def test_modified_tracked_file_outside_scope_is_named_modified(self):
        (self.repo / "b.ts").write_text("export const b = 2;\n")  # clean and not in scope at snapshot time
        self.assertIn("modified: b.ts", self.changes())

    def test_deleted_file_is_named(self):
        (self.repo / "a.py").unlink()
        self.assertIn("deleted: a.py", self.changes())

    def test_git_checkout_of_a_file_is_detected(self):
        sh(self.repo, "checkout", "--", "a.py")
        self.assertTrue(any("a.py" in c for c in self.changes()))

    def test_new_commit_and_branch_are_detected(self):
        sh(self.repo, "branch", "sneaky")
        self.assertIn("branches or tags changed", self.changes())
        sh(self.repo, "commit", "-am", "sneaky commit")
        self.assertIn("HEAD moved", self.changes())

    def test_staging_is_detected(self):
        sh(self.repo, "add", "scratch.txt")
        self.assertTrue(self.changes())

    def test_verify_command_fails_with_changed_path(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            audit.main(["--init", "--repo", str(self.repo)])
        ev = json.loads(buf.getvalue())["evidence"]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(["--verify", "--evidence", ev]), audit.EXIT_OK)
        (self.repo / "a.py").write_text("tampered\n")
        out = io.StringIO()
        with redirect_stdout(out):
            rc = audit.main(["--verify", "--evidence", ev])
        self.assertEqual(rc, audit.EXIT_TAMPER)
        self.assertIn("AUDIT INVALID", out.getvalue())
        self.assertIn("a.py", out.getvalue())


if __name__ == "__main__":
    unittest.main()

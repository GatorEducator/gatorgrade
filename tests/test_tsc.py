"""Tests for the scripts/tsc.py module."""

import json
from pathlib import Path

import pytest

from scripts import tsc


class TestWalkNode:
    """Tests for _walk_node."""

    def test_returns_node_itself(self) -> None:
        """_walk_node includes the root node."""
        parser = tsc._make_parser()
        tree = parser.parse(b"x = 1")
        result = tsc._walk_node(tree.root_node)
        assert tree.root_node in result

    def test_returns_child_nodes(self) -> None:
        """_walk_node returns descendant nodes."""
        parser = tsc._make_parser()
        tree = parser.parse(b"def f(): pass")
        result = tsc._walk_node(tree.root_node)
        assert len(result) > 1


class TestGetFuncName:
    """Tests for _get_func_name."""

    def test_extracts_function_name(self) -> None:
        """_get_func_name returns the function name."""
        parser = tsc._make_parser()
        tree = parser.parse(b"def my_function(): pass")
        for node in tsc._walk_node(tree.root_node):
            if node.type == "function_definition":
                name = tsc._get_func_name(node)
                assert name == "my_function"
                return
        pytest.fail("No function_definition node found")

    def test_none_on_no_identifier(self) -> None:
        """_get_func_name returns None for non-function nodes."""
        parser = tsc._make_parser()
        tree = parser.parse(b"x = 1")
        name = tsc._get_func_name(tree.root_node)
        assert name is None


class TestGetCallNames:
    """Tests for _get_call_names."""

    def test_extracts_bare_call(self) -> None:
        """_get_call_names extracts a bare function call name."""
        parser = tsc._make_parser()
        tree = parser.parse(b"foo()")
        for node in tsc._walk_node(tree.root_node):
            if node.type == "call":
                names = tsc._get_call_names(node)
                assert "foo" in names
                return
        pytest.fail("No call node found")

    def test_extracts_dotted_call(self) -> None:
        """_get_call_names extracts a dotted call name."""
        parser = tsc._make_parser()
        tree = parser.parse(b"module.func()")
        for node in tsc._walk_node(tree.root_node):
            if node.type == "call":
                names = tsc._get_call_names(node)
                assert "func" in names
                return
        pytest.fail("No call node found")


class TestComputeCoverageStatus:
    """Tests for compute_coverage_status."""

    def test_direct_function(self) -> None:
        """A directly-tested function gets 'direct' status."""
        all_funcs: dict[str, dict[str, object]] = {
            "foo": {"file": "a.py", "line": 1, "end_line": 5}
        }
        result = tsc.compute_coverage_status(all_funcs, {"foo"}, {})
        assert result["foo"] == "direct"

    def test_indirect_function(self) -> None:
        """A function called by a directly-tested function gets 'indirect'."""
        all_funcs = {
            "foo": {"file": "a.py", "line": 1, "end_line": 5},
            "bar": {"file": "b.py", "line": 1, "end_line": 5},
        }
        call_graph: dict[str, set[str]] = {"foo": {"bar"}, "bar": set()}
        result = tsc.compute_coverage_status(all_funcs, {"foo"}, call_graph)
        assert result["foo"] == "direct"
        assert result["bar"] == "indirect"

    def test_untested_function(self) -> None:
        """A function with no coverage gets 'none'."""
        all_funcs: dict[str, dict[str, object]] = {
            "foo": {"file": "a.py", "line": 1, "end_line": 5}
        }
        result = tsc.compute_coverage_status(all_funcs, set(), {})
        assert result["foo"] == "none"

    def test_indirect_chain(self) -> None:
        """Indirect coverage flows through multiple call levels."""
        all_funcs = {
            "a": {"file": "a.py", "line": 1, "end_line": 5},
            "b": {"file": "b.py", "line": 1, "end_line": 5},
            "c": {"file": "c.py", "line": 1, "end_line": 5},
        }
        call_graph: dict[str, set[str]] = {"a": {"b"}, "b": {"c"}, "c": set()}
        result = tsc.compute_coverage_status(all_funcs, {"a"}, call_graph)
        assert result["a"] == "direct"
        assert result["b"] == "indirect"
        assert result["c"] == "indirect"


class TestClassifyAndReport:
    """Tests for classify_and_report."""

    def test_summary_counts(self) -> None:
        """Report summary has correct counts."""
        all_funcs = {
            "direct_func": {"file": "a.py", "line": 1, "end_line": 5},
            "indirect_func": {"file": "b.py", "line": 1, "end_line": 5},
            "untested_func": {"file": "c.py", "line": 1, "end_line": 5},
        }
        call_graph: dict[str, set[str]] = {
            "direct_func": {"indirect_func"},
            "indirect_func": set(),
        }
        report = tsc.classify_and_report(
            all_funcs,
            {"direct_func"},
            call_graph,
            {
                "direct_func": [
                    {
                        "test_name": "test_x",
                        "test_file": "t.py",
                        "test_start_line": 1,
                        "test_end_line": 10,
                    }
                ],
            },
        )
        s = report["summary"]
        assert s["total"] == 3  # noqa: PLR2004
        assert s["directly_tested"] == 1
        assert s["indirectly_tested"] == 1
        assert s["untested"] == 1

    def test_lists_populated(self) -> None:
        """Report lists are populated correctly."""
        all_funcs = {
            "f1": {"file": "a.py", "line": 1, "end_line": 5},
            "f2": {"file": "b.py", "line": 1, "end_line": 5},
        }
        call_graph: dict[str, set[str]] = {"f1": set(), "f2": set()}
        report = tsc.classify_and_report(
            all_funcs,
            {"f1"},
            call_graph,
            {
                "f1": [
                    {
                        "test_name": "test_f1",
                        "test_file": "t.py",
                        "test_start_line": 1,
                        "test_end_line": 5,
                    }
                ],
            },
        )
        assert len(report["directly_tested_list"]) == 1
        assert report["directly_tested_list"][0]["name"] == "f1"
        assert len(report["untested_list"]) == 1
        assert report["untested_list"][0]["name"] == "f2"


class TestMain:
    """Integration tests for the main CLI entry point."""

    def test_main_with_defaults(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Main runs successfully with default threshold."""
        monkeypatch.chdir(tmp_path)
        # use a very low threshold so it passes regardless of actual coverage
        try:
            tsc.main(
                threshold=0, output=tmp_path / "report.json", verbose=False
            )
        except SystemExit as e:
            assert e.code == 0 or e.code is None

    def test_main_writes_report_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Main writes a JSON report file."""
        monkeypatch.chdir(tmp_path)
        report_path = tmp_path / "tsc.json"
        try:
            tsc.main(threshold=0, output=report_path, verbose=False)
        except SystemExit:
            pass
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert "functions" in data
        assert "summary" in data


class TestDemoApi:
    """Tests for demo_api."""

    def test_returns_lines(self) -> None:
        """demo_api returns a list of lines."""
        lines = tsc.demo_api()
        assert isinstance(lines, list)
        assert len(lines) >= 2  # noqa: PLR2004

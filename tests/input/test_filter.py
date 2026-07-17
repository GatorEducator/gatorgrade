"""Tests for the gatorgrade.input.filter module."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck
from gatorgrade.input.filter import (
    DEFAULT_FILTER_BY,
    DEFAULT_FILTER_MODE,
    DEFAULT_FILTER_TYPE,
    FilterBy,
    FilterMode,
    FilterType,
    _contains_match,
    _exact_match,
    _fuzzy_match,
    _get_field_value,
    _match,
    filter_checks,
)

# --- Helper factories ---


def _make_shell_check(
    command: str = "echo hello",
    description: str | None = None,
    hint: str | None = None,
    check_name: str = "ShellCommand",
) -> ShellCheck:
    """Create a ShellCheck with the given attributes."""
    json_info: dict[str, str] = {
        "check": check_name,
        "description": description or "",
    }
    return ShellCheck(
        command=command,
        description=description,
        json_info=json_info,
        hint=hint,
    )


def _make_gg_check(
    description: str | None = None,
    name: str = "MatchFileFragment",
    hint: str | None = None,
) -> GatorGraderCheck:
    """Create a GatorGraderCheck with the given attributes."""
    json_info: dict[str, str] = {
        "check": name,
        "description": description or "",
    }
    return GatorGraderCheck(
        gg_args=["--description", description or "", name],
        json_info=json_info,
        hint=hint,
    )


# --- Matcher tests (grouped by function) ---


class TestExactMatch:
    """Tests for _exact_match."""

    def test_equal_strings_return_true(self) -> None:
        """Exact match returns True when strings are equal."""
        assert _exact_match("todo", "todo") is True

    def test_case_insensitive_match(self) -> None:
        """Exact match is case-insensitive."""
        assert _exact_match("TODO", "todo") is True

    def test_different_strings_return_false(self) -> None:
        """Exact match returns False when strings differ."""
        assert _exact_match("todo", "todos") is False

    def test_empty_query_does_not_match_nonempty(self) -> None:
        """Exact match returns False when query is empty and target is not."""
        assert _exact_match("", "todo") is False

    def test_both_empty_returns_true(self) -> None:
        """Exact match returns True when both strings are empty."""
        assert _exact_match("", "") is True


class TestContainsMatch:
    """Tests for _contains_match."""

    def test_substring_in_target_returns_true(self) -> None:
        """Contains match returns True when query is a substring."""
        assert _contains_match("todo", "Complete all TODOs") is True

    def test_case_insensitive_substring(self) -> None:
        """Contains match is case-insensitive."""
        assert _contains_match("TODO", "Complete all todos") is True

    def test_not_found_returns_false(self) -> None:
        """Contains match returns False when query is absent."""
        assert _contains_match("todo", "Add documentation") is False

    def test_empty_query_in_any_string(self) -> None:
        """Contains match returns True for empty query (empty string is in any string)."""
        assert _contains_match("", "anything") is True

    def test_exact_match_is_also_contains(self) -> None:
        """Contains match returns True for exact match of entire string."""
        assert _contains_match("hello", "hello") is True


class TestFuzzyMatch:
    """Tests for _fuzzy_match."""

    def test_subsequence_match_returns_true(self) -> None:
        """Fuzzy match returns True when all query chars appear in order."""
        assert _fuzzy_match("tdo", "Complete all TODOs") is True

    def test_exact_substring_is_fuzzy(self) -> None:
        """Fuzzy match returns True for contiguous substring."""
        assert _fuzzy_match("todo", "Complete all TODOs") is True

    def test_case_insensitive_fuzzy(self) -> None:
        """Fuzzy match is case-insensitive."""
        assert _fuzzy_match("TDO", "Complete all todos") is True

    def test_wrong_order_returns_false(self) -> None:
        """Fuzzy match returns False when chars not in order."""
        assert _fuzzy_match("odt", "Complete all TODOs") is False

    def test_extra_chars_in_query_returns_false(self) -> None:
        """Fuzzy match returns False when query has chars not in target."""
        assert _fuzzy_match("todoz", "Complete all TODOs") is False

    def test_empty_query_returns_true(self) -> None:
        """Fuzzy match returns True for empty query."""
        assert _fuzzy_match("", "anything") is True

    def test_short_query_in_long_description(self) -> None:
        """Fuzzy matches short abbreviations in long descriptions."""
        assert _fuzzy_match("cmp", "CountCommits present") is True


class TestMatchDispatcher:
    """Tests for the _match dispatcher."""

    def test_exact_mode_uses_exact_matcher(self) -> None:
        """_match with EXACT mode delegates to _exact_match."""
        assert _match(FilterMode.EXACT, "todo", "todo") is True
        assert _match(FilterMode.EXACT, "todo", "Complete all TODOs") is False

    def test_contains_mode_uses_contains_matcher(self) -> None:
        """_match with CONTAINS mode delegates to _contains_match."""
        assert (
            _match(FilterMode.CONTAINS, "todo", "Complete all TODOs") is True
        )
        assert (
            _match(FilterMode.CONTAINS, "todo", "Add documentation") is False
        )

    def test_fuzzy_mode_uses_fuzzy_matcher(self) -> None:
        """_match with FUZZY mode delegates to _fuzzy_match."""
        assert _match(FilterMode.FUZZY, "tdo", "Complete all TODOs") is True
        assert _match(FilterMode.FUZZY, "xyz", "Complete all TODOs") is False


# --- Field extraction tests ---


class TestGetFieldValue:
    """Tests for _get_field_value."""

    def test_description_on_shell_check(self) -> None:
        """_get_field_value returns description for ShellCheck."""
        check = _make_shell_check(description="Run a linter")
        result = _get_field_value(check, FilterBy.DESCRIPTION)
        assert result == "Run a linter"

    def test_description_on_gg_check(self) -> None:
        """_get_field_value returns description for GatorGraderCheck."""
        check = _make_gg_check(description="Complete all TODOs")
        result = _get_field_value(check, FilterBy.DESCRIPTION)
        assert result == "Complete all TODOs"

    def test_name_on_gg_check(self) -> None:
        """_get_field_value returns name from json_info for GatorGraderCheck."""
        check = _make_gg_check(name="MatchFileFragment")
        result = _get_field_value(check, FilterBy.NAME)
        assert result == "MatchFileFragment"

    def test_name_on_shell_check_uses_check_field(self) -> None:
        """_get_field_value returns json_info check field for ShellCheck NAME."""
        check = _make_shell_check(
            command="echo hello", check_name="ExecuteCommand"
        )
        result = _get_field_value(check, FilterBy.NAME)
        assert result == "ExecuteCommand"

    def test_hint_returns_empty_string_when_none(self) -> None:
        """_get_field_value returns empty string when hint is None."""
        check = _make_shell_check(hint=None)
        result = _get_field_value(check, FilterBy.HINT)
        assert result == ""

    def test_hint_returns_hint_when_set(self) -> None:
        """_get_field_value returns the hint value when set."""
        check = _make_shell_check(hint="Try using a loop")
        result = _get_field_value(check, FilterBy.HINT)
        assert result == "Try using a loop"


# --- filter_checks integration tests ---


class TestFilterChecksInclude:
    """Tests for filter_checks with INCLUDE type."""

    def _make_mixed_checks(self) -> list:
        """Create a mix of ShellCheck and GatorGraderCheck objects."""
        return [
            _make_shell_check(
                description="Complete all TODOs in the source code",
                command="echo test",
            ),
            _make_gg_check(
                description="Use an if statement",
                name="MatchFileRegex",
            ),
            _make_shell_check(
                description="Check code formatting",
                command="ruff format --check",
            ),
        ]

    def test_include_with_contains_description(self) -> None:
        """INCLUDE keeps checks whose description contains the query."""
        checks = self._make_mixed_checks()
        result = filter_checks(
            checks,
            mode=FilterMode.CONTAINS,
            by=FilterBy.DESCRIPTION,
            ftype=FilterType.INCLUDE,
            query="TODO",
        )
        assert len(result) == 1
        assert result[0].description == "Complete all TODOs in the source code"

    def test_include_with_exact_name(self) -> None:
        """INCLUDE keeps checks whose name exactly matches the query."""
        checks = self._make_mixed_checks()
        result = filter_checks(
            checks,
            mode=FilterMode.EXACT,
            by=FilterBy.NAME,
            ftype=FilterType.INCLUDE,
            query="MatchFileRegex",
        )
        assert len(result) == 1
        assert isinstance(result[0], GatorGraderCheck)
        json_info = result[0].json_info
        assert isinstance(json_info, dict)
        assert json_info["check"] == "MatchFileRegex"

    def test_include_with_fuzzy_hint(self) -> None:
        """INCLUDE keeps checks whose hint fuzzy-matches the query."""
        checks = [
            _make_shell_check(
                description="Test A",
                hint="Try using a loop structure",
            ),
            _make_shell_check(description="Test B", hint="Use a list"),
        ]
        result = filter_checks(
            checks,
            mode=FilterMode.FUZZY,
            by=FilterBy.HINT,
            ftype=FilterType.INCLUDE,
            query="lp",
        )
        assert len(result) == 1
        assert result[0].hint == "Try using a loop structure"

    def test_include_any_matches_any_field(self) -> None:
        """ANY matches a check if the query hits any field."""
        checks = self._make_mixed_checks()
        result = filter_checks(
            checks,
            mode=FilterMode.CONTAINS,
            by=FilterBy.ANY,
            ftype=FilterType.INCLUDE,
            query="MatchFileRegex",
        )
        assert len(result) == 1

    def test_no_matches_returns_empty(self) -> None:
        """INCLUDE with no matches returns empty list."""
        checks = self._make_mixed_checks()
        result = filter_checks(
            checks,
            mode=FilterMode.CONTAINS,
            by=FilterBy.DESCRIPTION,
            ftype=FilterType.INCLUDE,
            query="nonexistent_xyz",
        )
        assert result == []

    def test_empty_query_returns_all(self) -> None:
        """Empty query returns all checks unchanged (no filtering)."""
        checks = self._make_mixed_checks()
        result = filter_checks(
            checks,
            mode=FilterMode.CONTAINS,
            by=FilterBy.ANY,
            ftype=FilterType.INCLUDE,
            query="",
        )
        assert len(result) == len(checks)


class TestFilterChecksExclude:
    """Tests for filter_checks with EXCLUDE type."""

    def test_exclude_removes_matching_checks(self) -> None:
        """EXCLUDE drops checks whose description contains the query."""
        checks = [
            _make_shell_check(description="Complete all TODOs"),
            _make_shell_check(description="Check code formatting"),
        ]
        result = filter_checks(
            checks,
            mode=FilterMode.CONTAINS,
            by=FilterBy.DESCRIPTION,
            ftype=FilterType.EXCLUDE,
            query="TODO",
        )
        assert len(result) == 1
        assert result[0].description == "Check code formatting"

    def test_exclude_with_zero_matches(self) -> None:
        """EXCLUDE with no matches keeps all checks."""
        checks = [
            _make_shell_check(description="Complete all TODOs"),
        ]
        result = filter_checks(
            checks,
            mode=FilterMode.CONTAINS,
            by=FilterBy.DESCRIPTION,
            ftype=FilterType.EXCLUDE,
            query="xyz_nonexistent",
        )
        assert len(result) == 1


class TestFilterDefaults:
    """Tests that defaults behave correctly."""

    def test_defaults_are_contains_any_include(self) -> None:
        """Defaults: CONTAINS + ANY + INCLUDE."""
        assert DEFAULT_FILTER_MODE == FilterMode.CONTAINS
        assert DEFAULT_FILTER_BY == FilterBy.ANY
        assert DEFAULT_FILTER_TYPE == FilterType.INCLUDE

    def test_filter_with_query_only_uses_defaults(self) -> None:
        """Calling filter_checks with only a query uses CONTAINS+ANY+INCLUDE."""
        checks = [
            _make_shell_check(description="Complete all TODOs"),
            _make_gg_check(description="Use an if statement", name="IfCheck"),
        ]
        result = filter_checks(checks, query="TODO")
        assert len(result) == 1
        assert result[0].description == "Complete all TODOs"


class TestShellCheckNameField:
    """Tests that ShellCheck NAME comes from json_info["check"]."""

    def test_name_filter_matches_check_name(self) -> None:
        """NAME field on a ShellCheck matches against json_info check."""
        check = _make_shell_check(
            command="mdl .",
            description="Check markdown style",
            check_name="ExecuteCommand",
        )
        result = filter_checks(
            [check],
            mode=FilterMode.CONTAINS,
            by=FilterBy.NAME,
            ftype=FilterType.INCLUDE,
            query="ExecuteCommand",
        )
        assert len(result) == 1

    def test_name_filter_does_not_match_command(self) -> None:
        """NAME field on a ShellCheck does not match the command itself."""
        check = _make_shell_check(
            command="mdl .",
            description="Check markdown style",
            check_name="ShellCommand",
        )
        result = filter_checks(
            [check],
            mode=FilterMode.CONTAINS,
            by=FilterBy.NAME,
            ftype=FilterType.INCLUDE,
            query="mdl",
        )
        assert result == []


class TestHintNone:
    """Tests that None hint is treated as empty string."""

    def test_hint_none_does_not_match(self) -> None:
        """A check with None hint does not match non-empty queries."""
        check = _make_shell_check(
            description="Test",
            hint=None,
        )
        result = filter_checks(
            [check],
            mode=FilterMode.CONTAINS,
            by=FilterBy.HINT,
            ftype=FilterType.INCLUDE,
            query="anything",
        )
        assert result == []

    def test_empty_query_matches_none_hint_via_any(self) -> None:
        """Empty query matches all checks even with None hint."""
        check = _make_shell_check(
            description="Test",
            hint=None,
        )
        result = filter_checks(
            [check],
            mode=FilterMode.CONTAINS,
            by=FilterBy.ANY,
            ftype=FilterType.INCLUDE,
            query="",
        )
        assert len(result) == 1


class TestCaseInsensitivity:
    """Tests that all matching modes are case-insensitive."""

    def test_exact_case_insensitive(self) -> None:
        """EXACT matching is case-insensitive."""
        check = _make_gg_check(description="Complete All Todos")
        result = filter_checks(
            [check],
            mode=FilterMode.EXACT,
            by=FilterBy.DESCRIPTION,
            ftype=FilterType.INCLUDE,
            query="complete all todos",
        )
        assert len(result) == 1

    def test_contains_case_insensitive(self) -> None:
        """CONTAINS matching is case-insensitive."""
        check = _make_shell_check(description="Complete All Todos")
        result = filter_checks(
            [check],
            mode=FilterMode.CONTAINS,
            by=FilterBy.DESCRIPTION,
            ftype=FilterType.INCLUDE,
            query="ALL",
        )
        assert len(result) == 1

    def test_fuzzy_case_insensitive(self) -> None:
        """FUZZY matching is case-insensitive."""
        check = _make_shell_check(description="Complete All Todos")
        result = filter_checks(
            [check],
            mode=FilterMode.FUZZY,
            by=FilterBy.DESCRIPTION,
            ftype=FilterType.INCLUDE,
            query="cmplt",
        )
        assert len(result) == 1


# --- Property-based tests ---


@pytest.mark.propertybased
@given(st.text(min_size=0, max_size=20), st.text(min_size=0, max_size=100))
def test_monotonic_exact_implies_contains_implies_fuzzy(
    query: str, target: str
) -> None:
    """An EXACT match implies a CONTAINS match implies a FUZZY match."""
    exact = _exact_match(query, target)
    contains = _contains_match(query, target)
    fuzzy = _fuzzy_match(query, target)
    # if exact holds, contains must also hold
    if exact:
        assert contains, (
            f"EXACT match '{query}' in '{target}' should imply CONTAINS match"
        )
    # if contains holds, fuzzy must also hold
    if contains:
        assert fuzzy, (
            f"CONTAINS match '{query}' in '{target}' should imply FUZZY match"
        )


@pytest.mark.propertybased
@given(st.text(min_size=0, max_size=20), st.text(min_size=0, max_size=100))
def test_fuzzy_match_every_query_char_appears_in_target_in_order(
    query: str, target: str
) -> None:
    """For any FUZZY hit, every query char appears in target in order."""
    if _fuzzy_match(query, target):
        if not query:
            return
        target_lower = target.lower()
        query_lower = query.lower()
        idx = 0
        for char in target_lower:
            if idx < len(query_lower) and char == query_lower[idx]:
                idx += 1
        assert idx == len(query_lower), (
            f"FUZZY match '{query}' in '{target}' but "
            f"could not consume all query chars"
        )

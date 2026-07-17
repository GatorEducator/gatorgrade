"""Tests for the gatorgrade.input.filter module."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gatorgrade.input.checks import GatorGraderCheck, ShellCheck
from gatorgrade.input.filter import (
    DEFAULT_FILTER_BY,
    DEFAULT_FILTER_FUZZY_THRESHOLD,
    DEFAULT_FILTER_MODE,
    DEFAULT_FILTER_TYPE,
    FUZZY_LEVENSHTEIN_RATIO,
    FilterBy,
    FilterMode,
    FilterType,
    _contains_match,
    _exact_match,
    _fuzzy_match_multiword,
    _fuzzy_match_word,
    _fuzzy_subsequence,
    _get_field_value,
    _levenshtein_distance,
    _levenshtein_ratio,
    _match,
    filter_checks,
)


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


class TestFuzzySubsequence:
    """Tests for _fuzzy_subsequence."""

    def test_subsequence_match_returns_true(self) -> None:
        """Subsequence returns True when all query chars appear in order."""
        assert _fuzzy_subsequence("tdo", "Complete all TODOs") is True

    def test_exact_substring_is_subsequence(self) -> None:
        """Subsequence returns True for contiguous substring."""
        assert _fuzzy_subsequence("todo", "Complete all TODOs") is True

    def test_case_insensitive_subsequence(self) -> None:
        """Subsequence is case-insensitive."""
        assert _fuzzy_subsequence("TDO", "Complete all todos") is True

    def test_wrong_order_returns_false(self) -> None:
        """Subsequence returns False when chars not in order."""
        assert _fuzzy_subsequence("odt", "Complete all TODOs") is False

    def test_extra_chars_in_query_returns_false(self) -> None:
        """Subsequence returns False when query has chars not in target."""
        assert _fuzzy_subsequence("todoz", "Complete all TODOs") is False

    def test_empty_query_returns_true(self) -> None:
        """Subsequence returns True for empty query."""
        assert _fuzzy_subsequence("", "anything") is True

    def test_short_query_in_long_description(self) -> None:
        """Subsequence matches short abbreviations in long descriptions."""
        assert _fuzzy_subsequence("cmp", "CountCommits present") is True


class TestLevenshteinDistance:
    """Tests for _levenshtein_distance."""

    def test_identical_strings(self) -> None:
        """Identical strings have distance 0."""
        assert _levenshtein_distance("hello", "hello") == 0

    def test_one_substitution(self) -> None:
        """One character substitution."""
        assert _levenshtein_distance("cat", "cut") == 1

    def test_one_insertion(self) -> None:
        """One character insertion."""
        assert _levenshtein_distance("cat", "cats") == 1

    def test_one_deletion(self) -> None:
        """One character deletion."""
        assert _levenshtein_distance("cats", "cat") == 1

    def test_empty_strings(self) -> None:
        """Both empty strings have distance 0."""
        assert _levenshtein_distance("", "") == 0

    def test_empty_vs_nonempty(self) -> None:
        """Distance from empty to non-empty is the length of non-empty."""
        assert _levenshtein_distance("", "hello") == 5  # noqa: PLR2004

    def test_checking_vs_check(self) -> None:
        """Checking has distance 3 from check (insert ing)."""
        assert _levenshtein_distance("checking", "check") == 3  # noqa: PLR2004

    def test_conferm_vs_confirm(self) -> None:
        """Conferm has distance 1 from confirm (e to i)."""
        assert _levenshtein_distance("conferm", "confirm") == 1

    def test_completely_different(self) -> None:
        """Completely different strings have large distance."""
        assert _levenshtein_distance("abc", "xyz") == 3  # noqa: PLR2004


class TestLevenshteinRatio:
    """Tests for _levenshtein_ratio."""

    def test_identical_strings(self) -> None:
        """Identical strings have ratio 0.0."""
        assert _levenshtein_ratio("hello", "hello") == 0.0

    def test_checking_vs_check(self) -> None:
        """checking/check has ratio 3/8 = 0.375."""
        ratio = _levenshtein_ratio("checking", "check")
        assert ratio == 3 / 8
        assert ratio <= FUZZY_LEVENSHTEIN_RATIO

    def test_conferm_vs_confirm(self) -> None:
        """conferm/confirm has ratio 1/7 = 0.143."""
        ratio = _levenshtein_ratio("conferm", "confirm")
        assert ratio == 1 / 7
        assert ratio <= FUZZY_LEVENSHTEIN_RATIO

    def test_case_insensitive(self) -> None:
        """Ratio is case-insensitive."""
        assert _levenshtein_ratio("HELLO", "hello") == 0.0

    def test_completely_different(self) -> None:
        """Different strings have ratio above threshold."""
        ratio = _levenshtein_ratio("abc", "xyz")
        assert ratio > FUZZY_LEVENSHTEIN_RATIO

    def test_both_empty(self) -> None:
        """Both empty has ratio 0.0."""
        assert _levenshtein_ratio("", "") == 0.0


class TestFuzzyMatchWord:
    """Tests for _fuzzy_match_word."""

    def test_subsequence_match(self) -> None:
        """Word matches via subsequence."""
        assert _fuzzy_match_word("tdo", "Complete all TODOs") is True

    def test_levenshtein_morphology(self) -> None:
        """Word matches morphological variant via Levenshtein."""
        assert (
            _fuzzy_match_word("checking", "...with command 'ruff check'")
            is True
        )

    def test_levenshtein_typo(self) -> None:
        """Word matches a typo via Levenshtein against a similar-length target word."""
        # "conferm" vs the individual word "Confirm" in the CamelCase
        # compound: subsequence "conferm" in "ConfirmFileExists" fails,
        # but Levenshtein against the CamelCase prefix "Confirm" works
        # because "Confirm" is split as a separate word in the description
        assert (
            _fuzzy_match_word(
                "conferm",
                "Ensure ConfirmFileExists works properly",
            )
            is False
        )  # confirmFileExists is one word, too long for edit ratio
        # when the target has "confirm" as a separate word, it does match
        assert (
            _fuzzy_match_word("conferm", "Please confirm the file exists")
            is True
        )

    def test_no_match(self) -> None:
        """Word does not match at all."""
        assert _fuzzy_match_word("xyzzy", "Complete all TODOs") is False

    def test_empty_word(self) -> None:
        """Empty word returns True (trivially matches everything)."""
        assert _fuzzy_match_word("", "anything") is True


class TestFuzzyMatchMultiword:
    """Tests for _fuzzy_match_multiword."""

    def test_single_word_subsequence(self) -> None:
        """Single word matches via subsequence."""
        assert _fuzzy_match_multiword("tdo", "Complete all TODOs") is True

    def test_multi_word_all_via_subsequence(self) -> None:
        """Multiple words each match independently via subsequence."""
        assert (
            _fuzzy_match_multiword("cmp tdo", "CountCommits Complete TODOs")
            is True
        )

    def test_multi_word_with_levenshtein(self) -> None:
        """Multiple words with one matching via Levenshtein fallback."""
        target = "Ensure correct formatting with command 'ruff check'"
        assert (
            _fuzzy_match_multiword("ruff formatting checking", target) is True
        )

    def test_one_word_fails_whole_query_fails(self) -> None:
        """If any single word fails, the entire query is a miss."""
        assert (
            _fuzzy_match_multiword("tdo xyzzy", "Complete all TODOs") is False
        )

    def test_empty_query(self) -> None:
        """Empty query returns True."""
        assert _fuzzy_match_multiword("", "anything") is True

    def test_ruff_formatting_example(self) -> None:
        """The user's multi-word example matches via Levenshtein fallback."""
        target = (
            "Ensure that Question 1 has no Python files with"
            " incorrect formatting with command 'ruff check'"
        )
        assert (
            _fuzzy_match_multiword("ruff formatting ruff checking", target)
            is True
        )


class TestFuzzyThreshold:
    """Tests for the fuzzy threshold parameter."""

    def test_default_threshold_matches_constant(self) -> None:
        """Default threshold equals FUZZY_LEVENSHTEIN_RATIO."""
        assert DEFAULT_FILTER_FUZZY_THRESHOLD == FUZZY_LEVENSHTEIN_RATIO

    def test_zero_threshold_requires_subsequence_match(self) -> None:
        """At threshold 0.0, Levenshtein fallback never activates."""
        # "checking" does not match "check" via subsequence
        assert (
            _fuzzy_match_word("checking", "check", fuzzy_threshold=0.0)
            is False
        )
        # "tdo" still matches "TODOs" via subsequence
        assert (
            _fuzzy_match_word("tdo", "Complete all TODOs", fuzzy_threshold=0.0)
            is True
        )

    def test_low_threshold_rejects_loose_match(self) -> None:
        """A low threshold rejects words that are too different."""
        # "checking" vs "check" has ratio 3/8 = 0.375
        # at threshold 0.3, this should NOT match
        assert (
            _fuzzy_match_word("checking", "check", fuzzy_threshold=0.3)
            is False
        )

    def test_high_threshold_accepts_loose_match(self) -> None:
        """A high threshold allows looser word matches."""
        # "checking" vs "check" has ratio 3/8 = 0.375
        # at threshold 0.5, this SHOULD match
        assert (
            _fuzzy_match_word("checking", "check", fuzzy_threshold=0.5) is True
        )

    def test_threshold_passed_through_multiword(self) -> None:
        """Threshold is passed through _fuzzy_match_multiword."""
        target = "Ensure formatting with command 'ruff check'"
        # at 0.0, "checking" won't match "check" via Levenshtein
        assert (
            _fuzzy_match_multiword(
                "ruff formatting checking", target, fuzzy_threshold=0.0
            )
            is False
        )
        # at 0.5, "checking" matches "check" via Levenshtein
        assert (
            _fuzzy_match_multiword(
                "ruff formatting checking", target, fuzzy_threshold=0.5
            )
            is True
        )

    def test_threshold_passed_through_filter_checks(self) -> None:
        """Threshold is passed through filter_checks."""
        checks = [
            ShellCheck(
                command="ruff check",
                description="Ensure formatting with command 'ruff check'",
                json_info={"check": "ShellCommand", "description": "test"},
            ),
        ]
        # at 0.0, "checking" won't match "check"
        result = filter_checks(
            checks,
            mode=FilterMode.FUZZY,
            by=FilterBy.DESCRIPTION,
            ftype=FilterType.INCLUDE,
            query="ruff formatting checking",
            fuzzy_threshold=0.0,
        )
        assert len(result) == 0
        # at 0.5, "checking" matches "check"
        result = filter_checks(
            checks,
            mode=FilterMode.FUZZY,
            by=FilterBy.DESCRIPTION,
            ftype=FilterType.INCLUDE,
            query="ruff formatting checking",
            fuzzy_threshold=0.5,
        )
        assert len(result) == 1


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

    def test_fuzzy_mode_uses_multiword_matcher(self) -> None:
        """_match with FUZZY mode delegates to _fuzzy_match_multiword."""
        assert _match(FilterMode.FUZZY, "tdo", "Complete all TODOs") is True
        assert _match(FilterMode.FUZZY, "xyz", "Complete all TODOs") is False
        # multi-word with Levenshtein fallback
        assert (
            _match(
                FilterMode.FUZZY,
                "ruff formatting checking",
                "Ensure formatting with command 'ruff check'",
            )
            is True
        )


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


@pytest.mark.propertybased
@given(st.text(min_size=0, max_size=20), st.text(min_size=0, max_size=100))
def test_monotonic_exact_implies_contains_implies_fuzzy(
    query: str, target: str
) -> None:
    """An EXACT match implies a CONTAINS match implies a FUZZY match.

    The FUZZY mode uses multi-word subsequence + Levenshtein matching.
    If a query is a substring of the target, every word in the query
    is also a substring (hence subsequence) of the target, so FUZZY
    will match via subsequence.
    """
    exact = _exact_match(query, target)
    contains = _contains_match(query, target)
    fuzzy = _fuzzy_match_multiword(query, target)
    if exact:
        assert contains, (
            f"EXACT match '{query}' in '{target}' should imply CONTAINS match"
        )
    if contains:
        assert fuzzy, (
            f"CONTAINS match '{query}' in '{target}' should imply FUZZY match"
        )


@pytest.mark.propertybased
@given(
    st.text(min_size=0, max_size=15),
    st.text(min_size=0, max_size=80),
)
def test_fuzzy_subsequence_chars_in_order_property(
    query: str, target: str
) -> None:
    """For any _fuzzy_subsequence hit, every query char appears in target in order."""
    if _fuzzy_subsequence(query, target):
        if not query:
            return
        target_lower = target.lower()
        query_lower = query.lower()
        idx = 0
        for char in target_lower:
            if idx < len(query_lower) and char == query_lower[idx]:
                idx += 1
        assert idx == len(query_lower), (
            f"_fuzzy_subsequence match '{query}' in '{target}' but "
            f"could not consume all query chars"
        )


@pytest.mark.propertybased
@given(
    st.text(min_size=0, max_size=10),
    st.text(min_size=0, max_size=10),
)
def test_levenshtein_properties(s1: str, s2: str) -> None:
    """Levenshtein distance is symmetric and non-negative."""
    dist = _levenshtein_distance(s1, s2)
    # symmetry: distance(a, b) == distance(b, a)
    assert dist == _levenshtein_distance(s2, s1)
    # non-negative and bounded by the longer string length
    assert dist >= 0
    assert dist <= max(len(s1), len(s2))

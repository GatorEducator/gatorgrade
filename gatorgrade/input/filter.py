"""Pre-run check filtering for GatorGrade.

This module provides the filtering logic that narrows the list of checks
before they are executed. Filtering is triggered by --filter-query; when
it is provided (and non-empty), only the checks that match the query are
kept (INCLUDE) or removed (EXCLUDE), based on the three matching options.

Three matching modes, all case-insensitive:

- EXACT: whole-field equality via field.lower() == query.lower().
- CONTAINS: substring containment via the 'in' operator (default).
- FUZZY: subsequence match (characters of query appear in order with
  possible gaps, implemented via a hand-rolled character walk).

Four filter-by fields: DESCRIPTION (check.description), NAME (check name
or command for ShellCheck), HINT (check.hint, empty when None), and ANY
(check all three fields; hit if ANY matches).

IMPORTANT: Why NOT difflib.get_close_matches for FUZZY?

difflib is part of the standard library, so it passes the "no external
packages" rule, but it models the WRONG kind of fuzzy for this feature
and MUST NOT be used for FUZZY. Here is why:

- difflib.get_close_matches (and its engine
  difflib.SequenceMatcher.ratio()) scores similarity as
  2 * matching_chars / (len(query) + len(field)). That denominator
  normalizes by the sum of both lengths, so it harshly penalizes any
  length difference. Our whole feature is "short query in a long
  description," which is diametrically opposed to that math.

Measured examples (verified empirically):
  - "todo" in "Complete all TODOs" (the hero/spec example) scores only
    0.091 and get_close_matches returns []. It would silently match
    nothing at any usable cutoff.
  - "todo" in "Add documentation" scores 0.190 (higher than the
    we-want-it "todo"/"Complete all TODOs" pair), so no cutoff separates
    matches from non-matches.
  - "MatchFile" in "MatchFileFragment" scores 0.692 (works only when
    query and field lengths are comparable).
  - "todp" vs "todo" scores 0.750 (works for typo-tolerance on
    similar-length strings).

So difflib does typo-tolerance on similar-length strings, not
abbreviation matching. FUZZY in this feature means abbreviation matching
(short query, gaps allowed, no length penalty), which a ~6-line hand-
rolled subsequence walk provides directly with zero imports.

Verdict: difflib is the wrong tool for FUZZY. If typo-tolerance is ever
desired later, it would belong in a separate mode (e.g. a hypothetical
--filter-mode FUZZY_TYPO), not as a replacement for subsequence FUZZY.
"""

from enum import Enum
from typing import Any, List

from gatorgrade.input.checks import GatorGraderCheck


class FilterMode(Enum):
    """Matching strictness mode for filter queries."""

    EXACT = "EXACT"
    CONTAINS = "CONTAINS"
    FUZZY = "FUZZY"


class FilterBy(Enum):
    """Field to match the query against."""

    DESCRIPTION = "DESCRIPTION"
    NAME = "NAME"
    HINT = "HINT"
    ANY = "ANY"


class FilterType(Enum):
    """Whether to include or exclude matching checks."""

    INCLUDE = "INCLUDE"
    EXCLUDE = "EXCLUDE"


DEFAULT_FILTER_MODE = FilterMode.CONTAINS
DEFAULT_FILTER_BY = FilterBy.ANY
DEFAULT_FILTER_TYPE = FilterType.INCLUDE


def _exact_match(query: str, target: str) -> bool:
    """Return True if target equals query, case-insensitive.

    Args:
        query: The search query.
        target: The field value to search.

    Returns:
        True if target.lower() == query.lower().

    """
    return target.lower() == query.lower()


def _contains_match(query: str, target: str) -> bool:
    """Return True if query appears as a substring of target, case-insensitive.

    Args:
        query: The search query.
        target: The field value to search.

    Returns:
        True if query.lower() in target.lower().

    """
    return query.lower() in target.lower()


def _fuzzy_match(query: str, target: str) -> bool:
    """Return True if all chars of query appear in target in order (subsequence).

    Case-insensitive subsequence match implemented as a hand-rolled
    character walk. Does NOT use difflib (see module docstring).

    Args:
        query: The search query.
        target: The field value to search.

    Returns:
        True if all query characters appear in target in order.

    """
    if not query:
        return True
    query_lower = query.lower()
    target_lower = target.lower()
    query_index = 0
    query_len = len(query_lower)
    for char in target_lower:
        if char == query_lower[query_index]:
            query_index += 1
            if query_index == query_len:
                return True
    return False


def _match(mode: FilterMode, query: str, target: str) -> bool:
    """Dispatch to the correct matcher based on mode.

    Args:
        mode: The FilterMode to use.
        query: The search query.
        target: The field value to search.

    Returns:
        True if the target matches the query per the chosen mode.

    """
    if mode == FilterMode.EXACT:
        return _exact_match(query, target)
    if mode == FilterMode.CONTAINS:
        return _contains_match(query, target)
    return _fuzzy_match(query, target)


# --- Field extraction ---


def _get_field_value(check: Any, field: FilterBy) -> str:  # noqa: PLR0911
    """Extract the relevant string value from a check for the given field.

    For ShellCheck with NAME field, falls back to check.command since
    ShellCheck has no separate name attribute. For HINT, returns empty
    string when hint is None.

    Args:
        check: A ShellCheck or GatorGraderCheck instance.
        field: The FilterBy field to extract.

    Returns:
        The extracted field value as a string.

    """
    if field == FilterBy.DESCRIPTION:
        if isinstance(check, GatorGraderCheck):
            info = check.json_info
            if isinstance(info, dict):
                desc = info.get("description", "")
                return str(desc) if desc else ""
            return ""
        # ShellCheck has description attribute
        return check.description or ""
    if field == FilterBy.NAME:
        info = check.json_info
        if isinstance(info, dict):
            name = info.get("check", "")
            return str(name) if name else ""
        return str(info) if info else ""
    if field == FilterBy.HINT:
        return check.hint or ""
    return ""


def filter_checks(
    checks: List[Any],
    mode: FilterMode = DEFAULT_FILTER_MODE,
    by: FilterBy = DEFAULT_FILTER_BY,
    ftype: FilterType = DEFAULT_FILTER_TYPE,
    query: str = "",
) -> List[Any]:
    """Filter a list of checks based on the query and filter parameters.

    Filtering is active only when query is non-empty. When by is ANY, a
    check is a hit if the query matches at least one of DESCRIPTION, NAME,
    or HINT. INCLUDE keeps hits; EXCLUDE drops hits.

    Args:
        checks: The list of checks (ShellCheck and/or GatorGraderCheck).
        mode: The matching mode (default CONTAINS).
        by: The field(s) to search (default ANY).
        ftype: Whether to INCLUDE or EXCLUDE matching checks.
        query: The search query string.

    Returns:
        The filtered list of checks.

    """
    if not query:
        return list(checks)
    fields_to_check: List[FilterBy]
    if by == FilterBy.ANY:
        fields_to_check = [
            FilterBy.DESCRIPTION,
            FilterBy.NAME,
            FilterBy.HINT,
        ]
    else:
        fields_to_check = [by]
    result: List[Any] = []
    for check in checks:
        is_hit = any(
            _match(mode, query, _get_field_value(check, field))
            for field in fields_to_check
        )
        if ftype == FilterType.INCLUDE and is_hit:
            result.append(check)
        elif ftype == FilterType.EXCLUDE and not is_hit:
            result.append(check)
    return result

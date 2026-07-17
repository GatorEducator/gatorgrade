"""Pre-run check filtering for GatorGrade.

This module provides the filtering logic that narrows the list of checks
before they are executed. Filtering is triggered by --filter-query; when
it is provided (and non-empty), only the checks that match the query are
kept (INCLUDE) or removed (EXCLUDE), based on the three matching options.

Three matching modes, all case-insensitive:

- EXACT: whole-field equality via field.lower() == query.lower().
- CONTAINS: substring containment via the 'in' operator (default).
- FUZZY: multi-word subsequence matching with Levenshtein-distance
  fallback. Each whitespace-separated word in the query must match
  independently. A word matches if EITHER:
    (a) it appears as a case-insensitive subsequence anywhere in the
        target field (handles abbreviations: "tdo" finds "TODOs"), OR
    (b) it has a normalized Levenshtein edit distance at or below
        FUZZY_LEVENSHTEIN_RATIO against any individual word in the
        target field (handles typos and morphological variants:
        "checking" finds "check", "conferm" finds "Confirm").

  All query words must match (AND logic across words), which mirrors
  how fzf and similar fuzzy-finder tools handle multi-word queries.

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
abbreviation matching. FUZZY handles abbreviation matching through
subsequence search and handles typo-tolerance through a hand-rolled
Levenshtein distance check — both pure Python with zero imports beyond
the standard library (and the Levenshtein implementation imports
nothing at all).
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

# maximum normalized Levenshtein distance (edit_distance / max_len) for
# a fuzzy word-level match. At 0.4, "checking" (8 chars) vs "check"
# (5 chars) gives 3/8 = 0.375, which is below the threshold, so it
# matches. Raise this to allow looser matching, lower to tighten it.
FUZZY_LEVENSHTEIN_RATIO = 0.4


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


def _fuzzy_subsequence(query: str, target: str) -> bool:
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


# could also expose this as a future --filter-fuzzy-threshold CLI flag
def _levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein (edit) distance between two strings.

    The Levenshtein distance is the minimum number of single-character
    edits (insertions, deletions, or substitutions) needed to turn one
    string into the other. Uses a classic dynamic-programming approach
    with a single-row optimization, O(n*m) time and O(n) space.

    Args:
        s1: The first string.
        s2: The second string.

    Returns:
        The edit distance between s1 and s2.

    """
    # ensure s2 is the shorter dimension for the O(min(m,n)) row
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    prev_row = list(range(len(s2) + 1))
    for i, char1 in enumerate(s1, 1):
        curr_row = [i]
        for j, char2 in enumerate(s2, 1):
            cost = 0 if char1 == char2 else 1
            curr_row.append(
                min(
                    curr_row[j - 1] + 1,  # insertion
                    prev_row[j] + 1,  # deletion
                    prev_row[j - 1] + cost,  # substitution
                )
            )
        prev_row = curr_row
    return prev_row[-1]


def _levenshtein_ratio(word_a: str, word_b: str) -> float:
    """Return normalized edit distance between two words.

    This is levenshtein(a, b) / max(len(a), len(b)).
    A ratio of 0.0 means the words are identical; 1.0 means they
    share no characters in common (or one is empty). The comparison
    is case-insensitive.

    Args:
        word_a: The first word.
        word_b: The second word.

    Returns:
        The normalized edit distance as a float between 0.0 and 1.0.

    """
    max_len = max(len(word_a), len(word_b))
    if max_len == 0:
        return 0.0
    return _levenshtein_distance(word_a.lower(), word_b.lower()) / max_len


def _fuzzy_match_word(word: str, target: str) -> bool:
    """Check if a single query word matches a target string.

    A word matches if either:
    1. It appears as a case-insensitive subsequence anywhere in the
       target (handles abbreviations like "tdo" matching "TODOs").
    2. The target contains an individual word whose normalized
       Levenshtein distance to the query word is at or below
       FUZZY_LEVENSHTEIN_RATIO (handles typos like "conferm"
       matching "ConfirmFileExists" and morphological variants
       like "checking" matching "check").

    Args:
        word: A single query word (no internal whitespace).
        target: The full target field string to search against.

    Returns:
        True if the word matches the target via either strategy.

    """
    # strategy 1: the word is a subsequence of the whole target field
    if _fuzzy_subsequence(word, target):
        return True
    # strategy 2: some individual word in the target is close enough
    # via edit distance (handles typos and differently-ending variants
    # like "checking" vs "check" which subsequence alone would miss)
    for target_word in target.split():
        if _levenshtein_ratio(word, target_word) <= FUZZY_LEVENSHTEIN_RATIO:
            return True
    return False


def _fuzzy_match_multiword(query: str, target: str) -> bool:
    """Return True if all words in the query match the target, AND logic.

    The query is split on whitespace into individual words. Each word
    must independently match the target via _fuzzy_match_word. If ANY
    word fails to match, the whole query is considered a miss.

    This mirrors how fzf and similar fuzzy-finder tools interpret
    space-separated tokens: each token narrows the result set, and
    every token must be satisfied for an item to be included.

    Args:
        query: The full query string (may contain multiple words).
        target: The field value to search.

    Returns:
        True if every word in the query matches the target.

    """
    words = query.split()
    if not words:
        return True
    return all(_fuzzy_match_word(w, target) for w in words)


def _match(mode: FilterMode, query: str, target: str) -> bool:
    """Dispatch to the correct matcher based on mode.

    For FUZZY mode, uses multi-word matching with subsequence and
    Levenshtein fallback. For EXACT and CONTAINS, uses the simpler
    single-string matchers.

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
    return _fuzzy_match_multiword(query, target)


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

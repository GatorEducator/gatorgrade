"""Tests for the gatorgrade.validate module."""

import pytest
from click import BadParameter
from hypothesis import given
from hypothesis import strategies as st

from gatorgrade import validate


@pytest.mark.propertybased
@given(st.integers(min_value=1, max_value=1000))
def test_validate_output_limit_valid_property(value: int) -> None:
    """Property: positive ints pass through validation unchanged."""
    result = validate.validate_output_limit(value)
    assert result == value


@pytest.mark.propertybased
@given(st.integers(max_value=0))
def test_validate_output_limit_invalid_property(value: int) -> None:
    """Property: non-positive ints cause BadParameter."""
    with pytest.raises(BadParameter):
        validate.validate_output_limit(value)


@pytest.mark.propertybased
@given(st.integers(min_value=1, max_value=1000))
def test_validate_baseline_weight_valid_property(value: int) -> None:
    """Property: positive ints pass through validation unchanged."""
    result = validate.validate_baseline_weight(value)
    assert result == value


@pytest.mark.propertybased
@given(st.integers(max_value=0))
def test_validate_baseline_weight_invalid_property(value: int) -> None:
    """Property: non-positive ints cause BadParameter."""
    with pytest.raises(BadParameter):
        validate.validate_baseline_weight(value)


def test_validate_report_passes_for_invalid_destination() -> None:
    """validate_report rejects an invalid destination."""
    with pytest.raises(BadParameter, match="First report argument"):
        validate.validate_report(("html", "json", "report.json"))


def test_validate_report_passes_for_invalid_type() -> None:
    """validate_report rejects an invalid report type."""
    with pytest.raises(BadParameter, match="Second report argument"):
        validate.validate_report(("file", "html", "report.json"))


def test_validate_github_env_passes_for_invalid_format() -> None:
    """validate_github_env rejects an invalid format."""
    with pytest.raises(BadParameter, match="First github-env argument"):
        validate.validate_github_env(("html", "JSON_REPORT"))


def test_validate_github_env_passes_for_invalid_name() -> None:
    """validate_github_env rejects an invalid environment variable name."""
    with pytest.raises(BadParameter, match="Second github-env argument"):
        validate.validate_github_env(("json", "1invalid!"))


def test_validate_github_env_passes_for_none_values() -> None:
    """validate_github_env passes through None values."""
    result = validate.validate_github_env((None, None))
    assert result == (None, None)


def test_validate_report_passes_for_none_values() -> None:
    """validate_report passes through None values."""
    result = validate.validate_report((None, None, None))
    assert result == (None, None, None)


def test_validate_report_rejects_invalid_env_var_name() -> None:
    """validate_report rejects an invalid env var name with ENV destination."""
    with pytest.raises(BadParameter, match="Third report argument"):
        validate.validate_report(("ENV", "MD", "1invalid!"))


def test_validate_report_accepts_valid_env_destination() -> None:
    """validate_report passes a valid ENV destination with valid var name."""
    result = validate.validate_report(("ENV", "MD", "MY_REPORT_VAR"))
    assert result == ("ENV", "MD", "MY_REPORT_VAR")


def test_validate_report_handles_env_with_none_varname() -> None:
    """validate_report handles ENV destination when var name is None."""
    result = validate.validate_report(("ENV", "MD", None))
    assert result == ("ENV", "MD", None)


@pytest.mark.propertybased
@given(st.from_regex(r"^[A-Za-z_][A-Za-z0-9_]*$"))
def test_valid_env_var_names_match_property(value: str) -> None:
    """Property: valid env var names match the VALID_ENV_VAR_NAME pattern."""
    assert validate.VALID_ENV_VAR_NAME.match(value) is not None


@pytest.mark.propertybased
@given(
    st.one_of(
        # names starting with a digit are invalid
        st.from_regex(r"^[0-9].*$", fullmatch=True),
        # names containing spaces are invalid
        st.from_regex(r"^.*\\s+.*$", fullmatch=True),
        # names containing special characters (not underscore) are invalid
        st.from_regex(r"^.*[^A-Za-z0-9_].*$", fullmatch=True),
    )
)
def test_invalid_env_var_names_do_not_match_property(value: str) -> None:
    """Property: invalid env var names do not match the pattern."""
    assert validate.VALID_ENV_VAR_NAME.match(value) is None


class TestAutoHintOptionsValidation:
    """Tests for validate_auto_hint_options."""

    def test_all_valid_when_auto_hint_enabled(self) -> None:
        """No errors when all options are consistent with auto-hint enabled."""
        errors = validate.validate_auto_hint_options(
            auto_hint=True,
            auto_hint_model="custom/model",
            auto_hint_url="http://localhost:4000",
            auto_hint_api_key="sk-test-key",
        )
        assert errors == []

    def test_all_valid_with_default_model(self) -> None:
        """No errors with default model sentinel."""
        errors = validate.validate_auto_hint_options(
            auto_hint=True,
            auto_hint_model="__default_model__",
            auto_hint_url=None,
            auto_hint_api_key=None,
        )
        assert errors == []

    def test_model_requires_auto_hint(self) -> None:
        """Error when --auto-hint-model is used without --auto-hint."""
        errors = validate.validate_auto_hint_options(
            auto_hint=False,
            auto_hint_model="custom/model",
            auto_hint_url=None,
            auto_hint_api_key=None,
        )
        assert len(errors) >= 1
        assert "--auto-hint-model" in errors[0]
        assert "--auto-hint" in errors[0]

    def test_url_requires_auto_hint(self) -> None:
        """Error when --auto-hint-url is used without --auto-hint."""
        errors = validate.validate_auto_hint_options(
            auto_hint=False,
            auto_hint_model="__default_model__",
            auto_hint_url="http://localhost:4000",
            auto_hint_api_key=None,
        )
        assert len(errors) >= 1
        assert "--auto-hint-url" in errors[0]
        assert "--auto-hint" in errors[0]

    def test_api_key_requires_auto_hint(self) -> None:
        """Error when --auto-hint-api-key is used without --auto-hint."""
        errors = validate.validate_auto_hint_options(
            auto_hint=False,
            auto_hint_model="__default_model__",
            auto_hint_url=None,
            auto_hint_api_key="sk-test-key",
        )
        assert len(errors) >= 1
        assert "--auto-hint-api-key" in errors[0]
        assert "--auto-hint" in errors[0]

    def test_api_key_requires_url(self) -> None:
        """Error when --auto-hint-api-key is used without --auto-hint-url."""
        errors = validate.validate_auto_hint_options(
            auto_hint=True,
            auto_hint_model="__default_model__",
            auto_hint_url=None,
            auto_hint_api_key="sk-test-key",
        )
        assert len(errors) >= 1
        assert "--auto-hint-api-key" in errors[0]
        assert "--auto-hint-url" in errors[0]

    def test_multiple_errors_reported(self) -> None:
        """Multiple errors are reported when several flags are misused."""
        errors = validate.validate_auto_hint_options(
            auto_hint=False,
            auto_hint_model="custom/model",
            auto_hint_url=None,
            auto_hint_api_key="sk-test-key",
        )
        assert len(errors) >= 2  # noqa: PLR2004


class TestFilterOptionsValidation:
    """Tests for validate_filter_options."""

    def test_no_args_is_valid(self) -> None:
        """No filter args at all returns no errors (filtering off)."""
        errors = validate.validate_filter_options(
            filter_query=None,
            filter_mode=None,
            filter_by=None,
            filter_type=None,
        )
        assert errors == []

    def test_query_only_is_valid(self) -> None:
        """--filter-query alone returns no errors."""
        errors = validate.validate_filter_options(
            filter_query="todo",
            filter_mode=None,
            filter_by=None,
            filter_type=None,
        )
        assert errors == []

    def test_query_with_mode_is_valid(self) -> None:
        """--filter-query plus --filter-mode returns no errors."""
        errors = validate.validate_filter_options(
            filter_query="todo",
            filter_mode=validate.FilterMode.EXACT,
            filter_by=None,
            filter_type=None,
        )
        assert errors == []

    def test_query_with_by_is_valid(self) -> None:
        """--filter-query plus --filter-by returns no errors."""
        errors = validate.validate_filter_options(
            filter_query="todo",
            filter_mode=None,
            filter_by=validate.FilterBy.DESCRIPTION,
            filter_type=None,
        )
        assert errors == []

    def test_query_with_type_is_valid(self) -> None:
        """--filter-query plus --filter-type returns no errors."""
        errors = validate.validate_filter_options(
            filter_query="todo",
            filter_mode=None,
            filter_by=None,
            filter_type=validate.FilterType.EXCLUDE,
        )
        assert errors == []

    def test_query_with_all_four_is_valid(self) -> None:
        """All four filter args together returns no errors."""
        errors = validate.validate_filter_options(
            filter_query="todo",
            filter_mode=validate.FilterMode.EXACT,
            filter_by=validate.FilterBy.DESCRIPTION,
            filter_type=validate.FilterType.EXCLUDE,
        )
        assert errors == []

    def test_mode_without_query_is_invalid(self) -> None:
        """--filter-mode without --filter-query returns an error."""
        errors = validate.validate_filter_options(
            filter_query=None,
            filter_mode=validate.FilterMode.EXACT,
            filter_by=None,
            filter_type=None,
        )
        assert len(errors) >= 1
        assert "--filter-mode" in errors[0]
        assert "--filter-query" in errors[0]

    def test_by_without_query_is_invalid(self) -> None:
        """--filter-by without --filter-query returns an error."""
        errors = validate.validate_filter_options(
            filter_query=None,
            filter_mode=None,
            filter_by=validate.FilterBy.DESCRIPTION,
            filter_type=None,
        )
        assert len(errors) >= 1
        assert "--filter-by" in errors[0]
        assert "--filter-query" in errors[0]

    def test_type_without_query_is_invalid(self) -> None:
        """--filter-type without --filter-query returns an error."""
        errors = validate.validate_filter_options(
            filter_query=None,
            filter_mode=None,
            filter_by=None,
            filter_type=validate.FilterType.EXCLUDE,
        )
        assert len(errors) >= 1
        assert "--filter-type" in errors[0]
        assert "--filter-query" in errors[0]

    def test_empty_query_is_invalid(self) -> None:
        """--filter-query with empty string returns an error."""
        errors = validate.validate_filter_options(
            filter_query="",
            filter_mode=None,
            filter_by=None,
            filter_type=None,
        )
        assert len(errors) >= 1
        assert "empty" in errors[0]

    def test_default_values_are_not_flagged(self) -> None:
        """Passing default enum values without query does not error.

        The validation should only error when a non-default value is
        explicitly passed without --filter-query.
        """
        errors = validate.validate_filter_options(
            filter_query=None,
            filter_mode=validate.DEFAULT_FILTER_MODE,
            filter_by=validate.DEFAULT_FILTER_BY,
            filter_type=validate.DEFAULT_FILTER_TYPE,
        )
        assert errors == []

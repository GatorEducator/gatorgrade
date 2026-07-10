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
    result = validate._validate_output_limit(value)
    assert result == value


@pytest.mark.propertybased
@given(st.integers(max_value=0))
def test_validate_output_limit_invalid_property(value: int) -> None:
    """Property: non-positive ints cause BadParameter."""
    with pytest.raises(BadParameter):
        validate._validate_output_limit(value)


@pytest.mark.propertybased
@given(st.integers(min_value=1, max_value=1000))
def test_validate_baseline_weight_valid_property(value: int) -> None:
    """Property: positive ints pass through validation unchanged."""
    result = validate._validate_baseline_weight(value)
    assert result == value


@pytest.mark.propertybased
@given(st.integers(max_value=0))
def test_validate_baseline_weight_invalid_property(value: int) -> None:
    """Property: non-positive ints cause BadParameter."""
    with pytest.raises(BadParameter):
        validate._validate_baseline_weight(value)


def test_validate_report_passes_for_invalid_destination() -> None:
    """_validate_report rejects an invalid destination."""
    with pytest.raises(BadParameter, match="First report argument"):
        validate._validate_report(("html", "json", "report.json"))


def test_validate_report_passes_for_invalid_type() -> None:
    """_validate_report rejects an invalid report type."""
    with pytest.raises(BadParameter, match="Second report argument"):
        validate._validate_report(("file", "html", "report.json"))


def test_validate_github_env_passes_for_invalid_format() -> None:
    """_validate_github_env rejects an invalid format."""
    with pytest.raises(BadParameter, match="First github-env argument"):
        validate._validate_github_env(("html", "JSON_REPORT"))


def test_validate_github_env_passes_for_invalid_name() -> None:
    """_validate_github_env rejects an invalid environment variable name."""
    with pytest.raises(BadParameter, match="Second github-env argument"):
        validate._validate_github_env(("json", "1invalid!"))


def test_validate_github_env_passes_for_none_values() -> None:
    """_validate_github_env passes through None values."""
    result = validate._validate_github_env((None, None))
    assert result == (None, None)


def test_validate_report_passes_for_none_values() -> None:
    """_validate_report passes through None values."""
    result = validate._validate_report((None, None, None))
    assert result == (None, None, None)


def test_validate_report_rejects_invalid_env_var_name() -> None:
    """_validate_report rejects an invalid env var name with ENV destination."""
    with pytest.raises(BadParameter, match="Third report argument"):
        validate._validate_report(("ENV", "MD", "1invalid!"))


def test_validate_report_accepts_valid_env_destination() -> None:
    """_validate_report passes a valid ENV destination with valid var name."""
    result = validate._validate_report(("ENV", "MD", "MY_REPORT_VAR"))
    assert result == ("ENV", "MD", "MY_REPORT_VAR")


def test_validate_report_handles_env_with_none_varname() -> None:
    """_validate_report handles ENV destination when var name is None."""
    result = validate._validate_report(("ENV", "MD", None))
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
    """Tests for _validate_auto_hint_options."""

    def test_all_valid_when_auto_hint_enabled(self) -> None:
        """No errors when all options are consistent with auto-hint enabled."""
        errors = validate._validate_auto_hint_options(
            auto_hint=True,
            auto_hint_model="custom/model",
            auto_hint_url="http://localhost:4000",
            auto_hint_api_key="sk-test-key",
        )
        assert errors == []

    def test_all_valid_with_default_model(self) -> None:
        """No errors with default model sentinel."""
        errors = validate._validate_auto_hint_options(
            auto_hint=True,
            auto_hint_model="__default_model__",
            auto_hint_url=None,
            auto_hint_api_key=None,
        )
        assert errors == []

    def test_model_requires_auto_hint(self) -> None:
        """Error when --auto-hint-model is used without --auto-hint."""
        errors = validate._validate_auto_hint_options(
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
        errors = validate._validate_auto_hint_options(
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
        errors = validate._validate_auto_hint_options(
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
        errors = validate._validate_auto_hint_options(
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
        errors = validate._validate_auto_hint_options(
            auto_hint=False,
            auto_hint_model="custom/model",
            auto_hint_url=None,
            auto_hint_api_key="sk-test-key",
        )
        assert len(errors) >= 2  # noqa: PLR2004

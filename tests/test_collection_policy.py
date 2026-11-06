"""Exercise collection-time enforcement of property-test markers."""

from unittest.mock import Mock

import pytest
from hypothesis import given, strategies

from tests.conftest import pytest_collection_modifyitems

NODE_ID = "tests/example.py::test_property"
PROPERTY_MARKER = "propertybased"
ERROR_PATTERN = "Hypothesis tests require"


@given(strategies.integers())
def property_example(value: int) -> None:
    """Provide a Hypothesis function without collecting it as a test."""
    assert isinstance(value, int)


@pytest.mark.parametrize(
    ("property_based", "marked"), [(False, False), (True, True), (True, False)]
)
def test_collection_requires_property_markers(
    property_based: bool, marked: bool
) -> None:
    """Reject unmarked properties while allowing other collected tests."""
    item = Mock(spec=pytest.Item)
    item.nodeid = NODE_ID
    item.obj = (
        property_example if property_based else pytest_collection_modifyitems
    )
    item.get_closest_marker.return_value = marked or None
    if property_based and not marked:
        with pytest.raises(pytest.UsageError, match=ERROR_PATTERN):
            pytest_collection_modifyitems([item])
    else:
        pytest_collection_modifyitems([item])
    if property_based:
        item.get_closest_marker.assert_called_once_with(PROPERTY_MARKER)

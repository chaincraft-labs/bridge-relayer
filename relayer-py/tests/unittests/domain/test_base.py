import pytest
from src.relayer.domain.base import BaseResult


class TestResult:
    
    def test_result_dto_creation(self):
        """Create a default BaseResult DTO instance with ok and err set at None."""
        result = BaseResult()
        assert result.ok is None
        assert result.err is None
        
    @pytest.mark.parametrize("types, expected", [
        (True, True),
        (False, False),
        (123, 123),
        ("abc", "abc"),
        ([1, 2, 3], [1, 2, 3]),
        ((1, 2, 3), (1, 2, 3)),
        ({"k": "v"}, {"k": "v"}),
    ])
    def test_result_dto_can_be_set_with_any_types(
        self, 
        types, 
        expected
    ):
        """Set any types of values to ok or err."""
        result_ok = BaseResult()
        result_ok.ok = types
        result_err = BaseResult()
        result_err.err = types
        assert result_ok.ok == expected
        assert result_err.err == expected
        
    def test_result_dto_err_is_none_if_ok_is_set_and_vice_versa(self):
        """Only one property can be set, the other is set at None."""
        result = BaseResult()
        result.ok = 123
        result.err = "abc"
        result.ok = 456
        assert result.ok == 456
        assert result.err is None
        
    def test_equality_between_two_instances(self):
        """Test for equality between two instances of BaseResult DTO."""
        result_a = BaseResult()
        result_b = BaseResult()
        result_a.ok = 123
        result_b.ok = 123
        assert result_a == result_b
        
        
    def test_inequality_between_two_instances(self):
        """Test for inequality between two instances of BaseResult DTO."""
        result_a = BaseResult()
        result_b = BaseResult()
        result_a.ok = 123
        result_b.ok = 456
        assert result_a != result_b

    def test_base_result_as_bool_is_true(self):
        """Test BaseResult ok is set as True then as bool is True."""
        result = BaseResult()
        result.ok = 123
        assert bool(result) is True
        
    def test_base_result_as_bool_is_false(self):
        """Test BaseResult not set then as bool is False."""
        result = BaseResult()
        assert bool(result) is False

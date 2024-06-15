import pytest
from io import BytesIO

from src.utils.converter import (
    to_bytes, 
    from_bytes,
    _serialize_data
)
from tests.conftest import EVENT_SAMPLE


PARAM_TESTS = [
        (EVENT_SAMPLE['args']['params']), # type: ignore
        ("this is a string"),
        ({"k": "v"}),
        ({
            "k": {
                "k1": "a string",
                "k2": ["a list 1", "a list 2"],
                "k3": True,
                "k4": None,
                "k5": bytes("a string to bytes", encoding="utf-8"),
                "k6": 123
            }, 
        }),
        (["a list"])
    ]


class TestConverter:
    
    @pytest.mark.parametrize("data", PARAM_TESTS)
    def test__serialize_attributedict(self, data):
        """"""
        assert isinstance(_serialize_data(data), BytesIO)
    
    
    @pytest.mark.parametrize("data", PARAM_TESTS)    
    def test_to_bytes_convert_object(self, data):
        """"""
        params_bytes = to_bytes(data)
        params_deserialized = from_bytes(params_bytes)
        assert isinstance(params_bytes, bytes)
        assert params_deserialized == data

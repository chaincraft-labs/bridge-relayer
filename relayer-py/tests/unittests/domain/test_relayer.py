from dataclasses import asdict
import pytest

from src.relayer.domain.relayer import (
    BridgeTaskResult,
    RegisterEventResult,
    EventDTO,
    BridgeTaskDTO,
)

from tests.conftest import (
    DATA_TEST,
)
# -------------------------------------------------------
# F I X T U R E S
# -------------------------------------------------------
RESULT_DTOS = [
    RegisterEventResult,
    BridgeTaskResult,
]   
    
EVENT_DATA = DATA_TEST.EVENT_DTO # type: ignore

@pytest.fixture(scope="function", params=RESULT_DTOS)
def result_instance(request):
    """Instanciate all inherited BaseResult DTO."""
    return request.param()

# -------------------------------------------------------
# T E S T S
# -------------------------------------------------------

def test_default_values_at_result_dto_creation(result_instance):
    """
        Default value is None for ok and err at DTO creation.
    """
    assert result_instance.ok is None
    assert result_instance.err is None   

@pytest.mark.parametrize(
    "ok_value, ok_expected", 
    [
        (True, True),
        (False, False),
        (123, 123),
        ("abc", "abc"),
        ([1, 2, 3], [1, 2, 3]),
        ((1, 2, 3), (1, 2, 3)),
        ({"k": "v"}, {"k": "v"}),
    ]
)
def test_result_dto_can_be_set_with_any_types(
    result_instance,
    ok_value, 
    ok_expected
):
    """
        Set any types of values to ok or err.
    """
    result_instance.ok = ok_value
    assert result_instance.ok == ok_expected
    
def test_result_dto_err_is_none_if_ok_is_set_and_vice_versa(result_instance):
    """
        Only one property can be set, the other is set at None.
    """
    result_instance.ok = 123
    result_instance.err = "abc"
    result_instance.ok = 456
    assert result_instance.ok == 456
    assert result_instance.err is None
    
@pytest.mark.parametrize("dto", RESULT_DTOS)
def test_equality_between_two_instances(dto):
    """
        Test for equality between two instances of ResultDTO.
    """
    result_a = dto()
    result_b = dto()
    result_a.ok = 123
    result_b.ok = 123
    assert result_a == result_b
    
@pytest.mark.parametrize("dto", RESULT_DTOS)
def test_inequality_between_two_instances(dto):
    """
        Test for inequality between two instances of ResultDTO.
    """
    result_a = dto()
    result_b = dto()
    result_a.ok = 123
    result_b.ok = 456
    assert result_a != result_b

# EventDTO
def test_event_dto_creation():
    """
        Test creation for EventDTO.
    """
    event_dto = EventDTO(**EVENT_DATA)
    assert event_dto.name == EVENT_DATA['name']
    assert event_dto.data == EVENT_DATA['data']
    assert asdict(event_dto) == EVENT_DATA

# BridgeTaskDTO
def test_bridge_task_dto_creation():
    """
        Test creation for BridgeTaskDTO.
    """
    bridge_task_dto = BridgeTaskDTO(
        func_name="fake_event", 
        params={"k": "v"},
    )
    assert bridge_task_dto.func_name == "fake_event"
    assert bridge_task_dto.params == {"k": "v"}
    assert asdict(bridge_task_dto) == {
        'func_name': 'fake_event', 
        'params': {'k': 'v'}
    }

import asyncio
import logging
from typing import Coroutine, List
from unittest.mock import AsyncMock, patch
from hexbytes import HexBytes
import pytest

from attributedict.collections import AttributeDict

from web3 import AsyncWeb3
from web3.contract.async_contract import AsyncContract
from src.relayer.domain.config import RelayerBlockchainConfigDTO
from src.relayer.domain.relayer import BridgeTaskDTO, EventDTO
from src.relayer.domain.exception import (
    BridgeRelayerBlockchainNotConnected,
)
from src.relayer.provider.relayer_blockchain_web3 import (
    RelayerBlockchainProvider
)
from src.relayer.config import get_blockchain_config
from tests.conftest import EVENT_SAMPLE


pytest_plugins = ('pytest_asyncio',)


async def mock_client_version():
    return "7.7.7"

ROOT_PATH = "src.relayer.provider.relayer_blockchain_web3"
CHAIN_ID = 80002

bridge_task_dto = BridgeTaskDTO(
    func_name='receiveBridgeOrder_', 
    params={
        'params': [
            '0x66F91393Be9C04039997763AEE11b47c5d04A486', 
            '0xE4192BF486AeA10422eE097BC2Cf8c28597B9F11', 
            80002, 
            411, 
            '0x66F91393Be9C04039997763AEE11b47c5d04A486', 
            '0x0000000000000000000000000000000000000000', 
            100, 
            123, 
            b'\xf2\xc2\x98\xbe\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00 \x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06MyName\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        ]
    }
)

TX_RECEIPT = AttributeDict({'blockHash': HexBytes('0x21cf5a29ed75c26a669383c58a686fd8bdda55c2620e82ddca9e7ce490dd0547'), 'blockNumber': 7959797, 'contractAddress': None, 'cumulativeGasUsed': 383282, 'effectiveGasPrice': 1000000015, 'from': '0xE4192BF486AeA10422eE097BC2Cf8c28597B9F11', 'gasUsed': 288414, 'logs': [AttributeDict({'address': '0x0000000000000000000000000000000000001010', 'topics': [HexBytes('0x4dfe1bbbcf077ddc3e01291eea2d5c70c2b422b415d95645b9adcfd678cb1d63'), HexBytes('0x0000000000000000000000000000000000000000000000000000000000001010'), HexBytes('0x000000000000000000000000e4192bf486aea10422ee097bc2cf8c28597b9f11'), HexBytes('0x0000000000000000000000006ab3d36c46ecfb9b9c0bd51cb1c3da5a2c81cea6')], 'data': HexBytes('0x0000000000000000000000000000000000000000000000000001064f9e04ac00000000000000000000000000000000000000000000000000048d9bee3a75b1010000000000000000000000000000000000000000000001ac3ac84ce0f81bc7f8000000000000000000000000000000000000000000000000048c959e9c7105010000000000000000000000000000000000000000000001ac3ac95330962073f8'), 'blockNumber': 7959797, 'transactionHash': HexBytes('0xbe9e2d490f4026f18f2b1740e9b1c5d56268d0659ae7687546b1d256d706f2bf'), 'transactionIndex': 1, 'blockHash': HexBytes('0x21cf5a29ed75c26a669383c58a686fd8bdda55c2620e82ddca9e7ce490dd0547'), 'logIndex': 2, 'removed': False})], 'logsBloom': HexBytes('0x00000000080000000000000000000000000000000000000000000000000000000000000000000000000000000000000000008000000000000000000000000000000000080000000008000000000000800000000000000000000100000000000000000000000000000000000000000000000000000000000080000000000000000000000000000000000000000000000000000000000000000000400000000000200000000000000000000000000000000000000000000000000000000000004000000000000000000001020000000000000000010000000000100000000000000000000000000000000000000000000000000000000000000000000000100000'), 'status': 1, 'to': '0xc8f81a3F84a3E96c1676c7F303e191b3E688E8e5', 'transactionHash': HexBytes('0xbe9e2d490f4026f18f2b1740e9b1c5d56268d0659ae7687546b1d256d706f2bf'), 'transactionIndex': 1, 'type': 2})


class TestRelayerBlockchainProvider:

    # -----------------------------------------------------------------
    # F I X T U R E S
    # -----------------------------------------------------------------  
    @pytest.fixture
    def provider(self):
        """Create a relayer blockchain provider."""        
        provider = RelayerBlockchainProvider(debug=False,)
        provider.set_chain_id(chain_id=123)
        return provider
    
    @pytest.fixture
    def provider_logging(self):
        """Create a relayer blockchain provider with debug."""        
        provider = RelayerBlockchainProvider(debug=True)
        provider.set_chain_id(chain_id=123)
        return provider
        
    
    @pytest.fixture
    def func(self):
        """"""
        class TransactionBuilder:
            def __init__(self, **data):
                self.data = data

            async def build_transaction(self, **data):
                return {}

        def func(**data):
            return TransactionBuilder(**data)
        
        return func
    
    
    # -----------------------------------------------------------------
    # T E S T S
    # -----------------------------------------------------------------  
    def test_relayer_blockchain_provider_init_success(
        self, 
    ):
        """Test RelayerBlockchainProvider that init with proper attributes."""
        # blockchain_config: RelayerBlockchainConfigDTO = get_blockchain_config(chain_id=CHAIN_ID)
        provider = RelayerBlockchainProvider(debug=False,)
        assert provider.debug is False

    def test_relayer_blockchain_not_connected(self):
        """Test that the relayer_blockchain is not connected and raise RelayerBlockchainNotConnected."""
        provider = RelayerBlockchainProvider(debug=False)
        with pytest.raises(BridgeRelayerBlockchainNotConnected):
            provider.client_version()
           
    def test_client_version_with_blockchain_conneted(
        self, 
        provider
    ):
        """Test that the w3 is a mock using EthereumTester."""
        with patch.object(provider, "w3") as mock_provider:
            mock_provider.client_version = mock_client_version()
            assert provider.client_version() == asyncio.run(mock_client_version())

    def test__set_provider_returns_asyncweb3_instance(
        self, 
        provider
    ):
        """Test _set_provider that returns a AsyncWeb3 instance."""
        assert isinstance(provider._set_provider(), AsyncWeb3)
    
    def test__set_contract_returns_AsyncContract_instance(self, 
        provider
    ):
        """Test _set_contract that returns a AsyncContract instance."""
        r = provider._set_contract()
        assert isinstance(provider._set_contract(), AsyncContract)    
    
    def test__create_event_filters_returns_list_event_filter(
        self, 
        provider
    ):
        """Test _create_event_filters that returns a list of event filter."""
        log: List[Coroutine] = provider._create_event_filters()
        assert isinstance(log[0], Coroutine)
    
    def test_create_event_dto_return_event_dto(
        self,
        provider
    ):
        """Test create_event_dto that returns a EventDTO instance."""
        event_dto: EventDTO = provider.create_event_dto(EVENT_SAMPLE)
        assert isinstance(event_dto, EventDTO)
        assert event_dto.name == EVENT_SAMPLE.event # type: ignore
        assert event_dto.data == EVENT_SAMPLE.args # type: ignore
        
    def test__handle_event_execute_callback(
        self,
        provider
    ):
        """
        Test _handle_event that should execute a callback function with EventDTO.
        
        args:
            event: Must be an EventDTO
            callback: Can be anything that an EventDTO as parameters. 
                The callback is defined and used in tha applciation layer.
        """
        def foo(event: EventDTO):
            assert event.name == EVENT_SAMPLE.event # type: ignore
            
        provider._handle_event(EVENT_SAMPLE, foo)
        
    def test__execute_event_filters_returns_list_event_filter(
        self, 
        provider
    ):
        """Test _execute_event_filters that returns a list of event filter log."""        
        async def foo():
            return 777
        event_filters = [foo()]
                
        with patch.object(provider, "_create_event_filters") as mock_create_event_filters:
            mock_create_event_filters.return_value = event_filters
            result = provider._execute_event_filters()
            assert result[0] == 777
        
    @pytest.mark.asyncio
    async def test__handle_event_execute_callback_func(
        self,
        provider
    ):       
        """Test _log_loop that execute the callbak function."""       
        def callback(event_dto):
            assert isinstance(event_dto, EventDTO)

        mock_event_filter = AsyncMock()
        attrs = {'get_new_entries.return_value': [EVENT_SAMPLE]}
        mock_event_filter.configure_mock(**attrs)
        await provider._loop_handle_event(
            event_filter=mock_event_filter,
            poll_interval=0,
            callback=callback,   
        )

    # ---------------------------------------------------------------
    # L O G G I N G
    # ---------------------------------------------------------------
    def test_logging_for__set_provider(
        self, 
        caplog,
        provider_logging
    ):
        """Test _set_provider that log INFO."""
        caplog.set_level(logging.INFO)     
        provider_logging._set_provider()
        
        for record in caplog.records:
            assert record.levelname == "INFO"
        assert "Setting the w3 provider instance!" in caplog.text
        
    def test_logging_for__set_contract(
        self, 
        caplog,
        provider_logging
    ):
        """Test _set_contract that log INFO."""
        caplog.set_level(logging.INFO)        
        provider_logging._set_contract()
        
        for record in caplog.records:
            assert record.levelname == "INFO"
        assert "Setting the w3 contract instance!" in caplog.text

    def test_logging_for__create_event_filters(
        self, 
        caplog,
        provider_logging
    ):
        """Test _create_event_filters that log INFO."""
        caplog.set_level(logging.INFO)        
        provider_logging._create_event_filters()
        for record in caplog.records:
            assert record.levelname == "INFO"
        assert "Create the event filters list!" in caplog.text
        
    def test_logging_for__execute_event_filters(
        self, 
        caplog,
        provider_logging
    ):
        """Test _execute_event_filters that log INFO."""
        caplog.set_level(logging.INFO)
        with patch.object(provider_logging, "_create_event_filters"):
            provider_logging._execute_event_filters()
            for record in caplog.records:
                assert record.levelname == "INFO"
            assert "Execute the event filters!" in caplog.text
    
    
    def test_logging_for_create_event_dto(
        self, 
        caplog,
        provider_logging
    ):
        """Test create_event_dto that log INFO."""
        caplog.set_level(logging.INFO)
        provider_logging.create_event_dto(EVENT_SAMPLE)
        for record in caplog.records:
            assert record.levelname == "INFO"
        assert "Create event DTO from the event!" in caplog.text
        
    def test_logging_for__handle_event(
        self, 
        caplog,
        provider_logging
    ):
        """Test _handle_event that log INFO."""
        def callback(event):
            pass
    
        caplog.set_level(logging.INFO)
        provider_logging._handle_event(EVENT_SAMPLE, callback)
        for record in caplog.records:
            assert record.levelname == "INFO"
        assert "Handle the event!" in caplog.text
            
    def test_logging_for_listen_events(
        self, 
        caplog,
        provider_logging
    ):
        """Test listen_events that log INFO."""
        def callback(event):
            pass
    
        caplog.set_level(logging.INFO)
        with patch.object(provider_logging, "_execute_event_filters", return_value=[]):
            provider_logging.listen_events(callback)
            for record in caplog.records:
                assert record.levelname == "INFO"
            assert "Listens events (main)" in caplog.text
    
    
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._get_nonce")
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._get_function_by_name")
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._build_tx")
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._sign_tx")
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._send_raw_tx")
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._wait_for_transaction_receipt", return_value=TX_RECEIPT)
    @pytest.mark.asyncio
    async def test_logging_for_call_contract_func(
        self, 
        m1, m2, m3, m4, m5, m6,
        caplog,
        provider_logging,
    ):
        """Test call_contract_func that log INFO."""
        caplog.set_level(logging.INFO)
        await provider_logging.call_contract_func(bridge_task_dto)
        for record in caplog.records:
            assert record.levelname == "INFO"
        assert "Call smart contract's function " in caplog.text
        
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._get_nonce")
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._get_function_by_name")
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._build_tx")
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._sign_tx")
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._send_raw_tx")
    @patch(f"{ROOT_PATH}.RelayerBlockchainProvider._wait_for_transaction_receipt")
    @pytest.mark.asyncio
    async def test_logging_for_call_contract_func_error_with_exception(
        self, 
        m1, m2, m3, m4, m5, m6,
        caplog,
        provider_logging,
    ):
        """Test call_contract_func that log ERROR on Exception."""
        caplog.set_level(logging.ERROR)
        m1.side_effect = Exception("fake error")
        
        await provider_logging.call_contract_func(bridge_task_dto)
        for record in caplog.records:
            assert record.levelname == "ERROR"
        assert "failed with error : fake error" in caplog.text
        
        
    @pytest.mark.asyncio
    async def test__get_nonce(
        self,
        caplog,
        provider_logging
    ):
        """Test _get_nonce that returns a Nonce."""
        caplog.set_level(logging.INFO)
        with patch.object(provider_logging.w3.eth, "get_transaction_count"):
            pk = provider_logging.relay_blockchain_config.pk
            account = provider_logging.w3.eth.account.from_key(pk)
            
            await provider_logging._get_nonce(account)
            for record in caplog.records:
                assert record.levelname == "INFO"
            assert "Get nonce for address :" in caplog.text
        
        
    def test__get_function_by_name(
        self,
        caplog,
        provider_logging
    ):
        """Test _get_function_by_name that returns a Callable."""
        caplog.set_level(logging.INFO)
        with patch.object(provider_logging.w3_contract, "get_function_by_name"):
            provider_logging._get_function_by_name(bridge_task_dto)
            for record in caplog.records:
                assert record.levelname == "INFO"
            assert "Get smart contract's function " in caplog.text
        
    @pytest.mark.asyncio
    async def test__build_tx(
        self,
        caplog,
        provider_logging,
        func
    ):
        """Test _build_tx that returns a Dict."""
        caplog.set_level(logging.INFO)
                       
        pk = provider_logging.relay_blockchain_config.pk
        account = provider_logging.w3.eth.account.from_key(pk)
                
        await provider_logging._build_tx(
            func=func,
            bridge_task_dto=bridge_task_dto,
            account=account,
            nonce=1
        )
        for record in caplog.records:
            assert record.levelname == "INFO"
        assert "Build a transaction with " in caplog.text
        
    def test__sign_tx(
        self,
        caplog,
        provider_logging
    ):
        """Test _sign_tx that returns a SignedTransaction."""
        caplog.set_level(logging.INFO)
        pk = provider_logging.relay_blockchain_config.pk
        account = provider_logging.w3.eth.account.from_key(pk)
        built_tx = {}
        with patch.object(provider_logging.w3.eth.account, 'sign_transaction'):
            provider_logging._sign_tx(built_tx, account)
            
            for record in caplog.records:
                assert record.levelname == "INFO"
            assert "Sign the transaction : " in caplog.text
    
    @pytest.mark.asyncio
    async def test__send_raw_tx(
        self,
        caplog,
        provider_logging
    ):
        """Test _send_raw_tx that returns a HexBytes."""
        caplog.set_level(logging.INFO)
        from eth_account.datastructures import SignedTransaction
        signed_tx = SignedTransaction(HexBytes(""), HexBytes(""), 1, 2, 3)
        with patch.object(provider_logging.w3.eth, 'send_raw_transaction'):
            await provider_logging._send_raw_tx(signed_tx)
            for record in caplog.records:
                assert record.levelname == "INFO"
            assert "Send the raw transaction signed_tx : " in caplog.text
    
    
    @pytest.mark.asyncio
    async def test__wait_for_transaction_receipt(
        self,
        caplog,
        provider_logging
    ):
        """Test _wait_for_transaction_receipt that returns a TxReceipt."""
        caplog.set_level(logging.INFO)
        with patch.object(provider_logging.w3.eth, 'wait_for_transaction_receipt'):
            await provider_logging._wait_for_transaction_receipt(HexBytes(""))
            for record in caplog.records:
                assert record.levelname == "INFO"
            assert "Wait for the transaction receipt for tx_hash : " in caplog.text
    
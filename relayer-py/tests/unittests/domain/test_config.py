from dataclasses import asdict

import pytest
from src.relayer.domain.config import RelayerBlockchainConfigDTO, RelayerRegisterConfigDTO
from tests.conftest import DATA_TEST

class TestRealyerConfig:
        
    @pytest.fixture
    def blockchain_config(self):
        return RelayerBlockchainConfigDTO(
            chain_id=DATA_TEST.CHAIN_ID,
            rpc_url=DATA_TEST.RPC_URL,
            project_id=DATA_TEST.PROJECT_ID,
            pk=DATA_TEST.PK,
            wait_block_validation=DATA_TEST.WAIT_BLOCK_VALIDATION,
            smart_contract_address=DATA_TEST.SMART_CONTRACT_ADDRESS,
            genesis_block=DATA_TEST.GENESIS_BLOCK,
            abi=DATA_TEST.ABI[DATA_TEST.ABI_NAME],
        )
        
    @pytest.fixture
    def register_config(self):
        return RelayerRegisterConfigDTO(
            host=DATA_TEST.REGISTER_CONFIG.host,
            port=DATA_TEST.REGISTER_CONFIG.port,
            user=DATA_TEST.REGISTER_CONFIG.user,
            password=DATA_TEST.REGISTER_CONFIG.password,
            queue_name=DATA_TEST.REGISTER_CONFIG.queue_name,
        )
    
    # -----------------------------------------------------
    # Tests
    # -----------------------------------------------------
    def test_relayer_blockchain_config_dto_instantiate_success(
        self, 
        blockchain_config
    ):
        """Test RelayProviderConfigDTO that instatiate a correct DTO."""
        assert blockchain_config.chain_id == DATA_TEST.CHAIN_ID
        assert blockchain_config.rpc_url == DATA_TEST.RPC_URL
        assert blockchain_config.smart_contract_address == DATA_TEST.SMART_CONTRACT_ADDRESS
        assert blockchain_config.genesis_block == DATA_TEST.GENESIS_BLOCK
        assert blockchain_config.abi == DATA_TEST.ABI[DATA_TEST.ABI_NAME]
        assert blockchain_config.pk == DATA_TEST.PK
        assert blockchain_config.wait_block_validation == DATA_TEST.WAIT_BLOCK_VALIDATION
        
    def test_relayer_blockchain_config_dto_as_dict(
        self,
        blockchain_config
    ):
        """Test RelayProviderConfigDTO that returns a dict."""
        expected = {
            "chain_id": DATA_TEST.CHAIN_ID,
            "rpc_url": DATA_TEST.RPC_URL,
            "smart_contract_address": DATA_TEST.SMART_CONTRACT_ADDRESS,
            "genesis_block": DATA_TEST.GENESIS_BLOCK,
            "project_id": DATA_TEST.PROJECT_ID,
            "abi": DATA_TEST.ABI[DATA_TEST.ABI_NAME],
            "pk": DATA_TEST.PK,
            "wait_block_validation": DATA_TEST.WAIT_BLOCK_VALIDATION
        }
        assert asdict(blockchain_config) == expected

    def test_relayer_blockchain_config_dto_as_string(
        self,
        blockchain_config
    ):
        """Test RelayProviderConfigDTO that returns a dict."""
        assert str(blockchain_config) == f"ChainId{DATA_TEST.CHAIN_ID}"

    def test_relayer_register_config_dto_instantiate_success(
        self, 
        register_config
    ):
        """Test RelayProviderConfigDTO that instatiate a correct DTO."""
        assert register_config.host == DATA_TEST.REGISTER_CONFIG.host
        assert register_config.port == DATA_TEST.REGISTER_CONFIG.port
        assert register_config.user == DATA_TEST.REGISTER_CONFIG.user
        assert register_config.password == DATA_TEST.REGISTER_CONFIG.password
        assert register_config.queue_name == DATA_TEST.REGISTER_CONFIG.queue_name
        
    def test_relayer_register_config_dto_returns_dict(
        self,
        register_config
    ):
        """Test RelayProviderConfigDTO that returns a dict."""
        expected = {
            "host": DATA_TEST.REGISTER_CONFIG.host,
            "port": DATA_TEST.REGISTER_CONFIG.port,
            "user": DATA_TEST.REGISTER_CONFIG.user,
            "password": DATA_TEST.REGISTER_CONFIG.password,
            "queue_name": DATA_TEST.REGISTER_CONFIG.queue_name,
        }
        assert asdict(register_config) == expected
import os
import sys

# Ajouter le répertoire parent de src au chemin de recherche des modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.relayer.domain.relayer import (
    BridgeTaskDTO,
)
from src.relayer.application.relayer_blockchain import ExecuteContractTask 
from src.relayer.provider.config import RelayerBlockchainConfigProvider as p_relayer_blockchain_config
from src.relayer.provider.relayer_blockchain_web3 import RelayerBlockchainProvider as p_relayer_blockchain

def main():
    
    chain_id = 80002
    relayer_blockchain = p_relayer_blockchain(chain_id=chain_id, debug=False)
    
    # Instanciate ExecuteContractTask
    tasker = ExecuteContractTask(
        relayer_blockchain_provider=relayer_blockchain,
    )
    
    bridge_task_dto = BridgeTaskDTO(
        func_name='closeBridgeOrder',
        params={
            "operationHash": b'\x97\xf6c\xf04)f\xfc\xd3\xa6\xca\x07\xbb\xe8+\x96\x8d_eiq\x16\xd4\xf0>\xe0\t\x8ep]\xf6\xba'
        }
    )
    
    bridge_task_dto = BridgeTaskDTO(
        func_name='validateFeesLocked',
        params={
            "operationHash": b'\x97\xf6c\xf04)f\xfc\xd3\xa6\xca\x07\xbb\xe8+\x96\x8d_eiq\x16\xd4\xf0>\xe0\t\x8ep]\xf6\xba',
            'newStatus': 1, 
            'blockStep': 7846542
        }
    )
    
    bridge_task_dto = BridgeTaskDTO(
        func_name='receiveBridgeOrder', 
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
        
        
    # Execute function
    tasker(
        chain_id=chain_id, 
        bridge_task_dto=bridge_task_dto,
    )

if __name__ == "__main__":
    main()

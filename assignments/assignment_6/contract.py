import solcx
from web3 import Web3
from solcx import compile_source, install_solc, set_solc_version
import json

def setup_solc():
    try:
        # Install solc if not already installed
        install_solc('0.8.0')
        # Set the version to use
        set_solc_version('0.8.0')
        print("Solc setup completed successfully")
    except Exception as e:
        print(f"Error setting up solc: {e}")
        raise

class GiftContract:
    """
    A class to manage the deployment and interaction with a shared gift smart contract on the Sepolia test network.
    """

    def __init__(self, infura_url):
        self.web3 = Web3(Web3.HTTPProvider(infura_url))

    def deploy_contract(self, target_amount_wei, private_key):
        """
        Deploys the shared gift contract with the specified target amount.

        :param target_amount_wei: The target amount in Wei for the shared gift.
        :param private_key: The private key of the account deploying the contract.
        :return: The address of the deployed contract.
        """
        with open('shared_gift.sol', 'r') as file:
            contract_source = file.read()

        compiled_sol = compile_source(contract_source)
        contract_interface = compiled_sol['<stdin>:SharedGift']

        account = self.web3.eth.account.from_key(private_key)

        contract = self.web3.eth.contract(
            abi=contract_interface['abi'],
            bytecode=contract_interface['bin']
        )

        nonce = self.web3.eth.get_transaction_count(account.address)

        transaction = contract.constructor(target_amount_wei).build_transaction({
            'chainId': 11155111,  # Sepolia
            'gas': 2000000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': nonce,
        })

        signed_txn = self.web3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

        return tx_receipt.contractAddress

    def contribute(self, contract_address, amount_wei, private_key):
        """
        Contributes a specified amount of Wei to the deployed contract.

        :param contract_address: The address of the deployed contract.
        :param amount_wei: The amount of Wei to contribute.
        :param private_key: The private key of the account making the contribution.
        :return: The transaction receipt of the contribution.
        """
        with open('shared_gift.sol', 'r') as file:
            contract_source = file.read()

        compiled_sol = compile_source(contract_source)
        contract_interface = compiled_sol['<stdin>:SharedGift']

        contract = self.web3.eth.contract(
            address=contract_address,
            abi=contract_interface['abi']
        )

        account = self.web3.eth.account.from_key(private_key)
        nonce = self.web3.eth.get_transaction_count(account.address)

        transaction = contract.functions.contribute().build_transaction({
            'from': account.address,
            'value': amount_wei,
            'chainId': 11155111,
            'gas': 200000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': nonce,
        })

        signed_txn = self.web3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)


def main():
    INFURA_URL = "https://sepolia.infura.io/v3/62a758774e20472b9bbd03c00839bccb"
    PRIVATE_KEY = "0x4a8f7b838f539de1392bf281f92808ed6f1aa76ec254db501a82b4d4a98b8ce1"

    setup_solc()

    try:
        print("Initializing GiftContract...")
        gift = GiftContract(INFURA_URL)

        # Deploy contract for a 0.1 ETH gift
        print("Deploying contract...")
        target_amount = Web3.to_wei(0.1, 'ether')
        contract_address = gift.deploy_contract(target_amount, PRIVATE_KEY)
        print(f"Contract deployed at: {contract_address}")

        # Contribute 0.03 ETH
        print("Making contribution...")
        contribution = Web3.to_wei(0.03, 'ether')
        tx_receipt = gift.contribute(contract_address, contribution, PRIVATE_KEY)
        print(f"Contribution made: {tx_receipt.transactionHash.hex()}")

    except Exception as e:
        print(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main()
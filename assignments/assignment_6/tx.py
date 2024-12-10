from web3 import Web3
import requests


class TransactionHandler:
    """
    A class to handle Ethereum transactions and interact with the Sepolia test network.
    """
    def __init__(self, api_key):
        self.web3 = Web3(Web3.HTTPProvider('https://sepolia.infura.io/v3/62a758774e20472b9bbd03c00839bccb'))
        self.api_key = api_key
        self.etherscan_url = "https://api-sepolia.etherscan.io/api"

    def create_transaction(self, from_address, to_address, amount_eth, private_key):
        """
        Creates and sends a transaction from one address to another.

        :param from_address: The address to send the transaction from.
        :param to_address: The address to send the transaction to.
        :param amount_eth: The amount of Ether to send.
        :param private_key: The private key of the sender's address.
        :return: The transaction hash.
        """
        try:
            amount_wei = self.web3.to_wei(amount_eth, 'ether')

            transaction = {
                'nonce': self.web3.eth.get_transaction_count(self.web3.to_checksum_address(from_address)),
                'to': self.web3.to_checksum_address(to_address),
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': self.web3.eth.gas_price,
                'chainId': 11155111  # Sepolia chain ID
            }

            signed_txn = self.web3.eth.account.sign_transaction(transaction, private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            return tx_hash.hex()

        except Exception as e:
            raise ValueError(f"Transaction failed: {e}")

    def get_transaction_status(self, tx_hash):
        """
        Retrieves the status of a transaction using its hash.

        :param tx_hash: The hash of the transaction.
        :return: A dictionary containing the status and hash of the transaction.
        """
        params = {
            'module': 'transaction',
            'action': 'gettxreceiptstatus',
            'txhash': '0x' + tx_hash,
            'apikey': self.api_key
        }

        response = requests.get(self.etherscan_url, params=params)
        data = response.json()

        if data['status'] == '1':
            return {
                'status': 'Confirmed' if data['result']['status'] == '1' else 'Failed',
                'hash': '0x' + tx_hash
            }
        return {'status': 'Pending', 'hash': tx_hash}


def main():
    ETHERSCAN_API_KEY = "U7FHTRE238ZGSPJYH4PP41XDQ52NNJP6PV"

    tx_handler = TransactionHandler(ETHERSCAN_API_KEY)

    # Example transaction
    from_address = "0x46E5EC2565669Aa83d4757D15d0014A3cd4dB953"
    to_address = "0x2BBBAd09aFaFc47b4EBa4848432E6c2999417435"
    private_key = "0x4a8f7b838f539de1392bf281f92808ed6f1aa76ec254db501a82b4d4a98b8ce1"
    amount = 0.05  # ETH

    # Send transaction
    tx_hash = tx_handler.create_transaction(from_address, to_address, amount, private_key)
    print(f"Transaction hash: {tx_hash}")

    # Check status
    status = tx_handler.get_transaction_status(tx_hash)
    print(f"Transaction status: {status}")


if __name__ == "__main__":
    ETHERSCAN_API_KEY = "U7FHTRE238ZGSPJYH4PP41XDQ52NNJP6PV"

    tx_handler = TransactionHandler(ETHERSCAN_API_KEY)

    # status = tx_handler.get_transaction_status("e064e80e20de97ee6873c85f4de0b2ab30bc468fa2f2d0c768117eee0f6f55ce")
    status = tx_handler.get_transaction_status("4d92b27e83be252b278f3b59c0db886d9d040627b1cb20fde6cfc956834faf33")
    print(f"Transaction status: {status}")
    # main()
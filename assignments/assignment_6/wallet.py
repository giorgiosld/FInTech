from web3 import Web3
from eth_account import Account
import requests

class EthereumWallet:
    """
        A class to manage Ethereum wallets and interact with the Sepolia test network.
    """
    def __init__(self, network_url, api_key):
        self.web3 = Web3(Web3.HTTPProvider(network_url))
        self.api_key = api_key
        self.base_url = "https://api-sepolia.etherscan.io/api"
        self.wallets = {}

    def create_wallet(self):
        """
        Creates a new Ethereum wallet and returns its address and private key.
        :return: wallet_info: dict containing the wallet address and private key
        """
        account = Account.create()
        wallet_info = {
            'address': account.address,
            'private_key': account.key.hex()
        }
        self.wallets[account.address] = wallet_info
        return wallet_info

    def import_wallet(self, private_key):
        """
        Imports an existing Ethereum wallet using its private key and returns its address and private key.
        :param private_key: the private key of the wallet to import
        :return: wallet_info: dict containing the wallet address and private key
        """
        if private_key.startswith('0x'):
            private_key = private_key[2:]
        try:
            account = Account.from_key('0x' + private_key)
            wallet_info = {
                'address': account.address,
                'private_key': account.key.hex()
            }
            self.wallets[account.address] = wallet_info
            return wallet_info
        except Exception as e:
            raise ValueError(f"Invalid private key: {e}")

    def get_balance(self, address):
        """
        Gets the balance of an Ethereum wallet in ETH and Wei.
        :param address: the address of the wallet
        :return: balance: dict containing the wallet address, balance in Wei and balance in ETH
        """
        params = {
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': 'latest',
            'apikey': self.api_key
        }

        response = requests.get(self.base_url, params=params)
        data = response.json()

        if data['status'] == '1':
            balance_wei = int(data['result'])
            balance_eth = self.web3.from_wei(balance_wei, 'ether')
            return {
                'address': address,
                'balance_wei': balance_wei,
                'balance_eth': balance_eth
            }
        else:
            raise ValueError(f"Error getting balance: {data['message']}")


def main():
    ETHERSCAN_API_KEY = "U7FHTRE238ZGSPJYH4PP41XDQ52NNJP6PV"
    SEPOLIA_URL = "https://api-sepolia.etherscan.io/api"

    wallet_manager = EthereumWallet(SEPOLIA_URL, ETHERSCAN_API_KEY)

    # Test wallet operations
    # new_wallet = wallet_manager.create_wallet()
    # print("Created new Wallet: ")
    # print(f"New wallet: {new_wallet['address']}")
    # print(f"Private key: 0x{new_wallet['private_key']}")
    # balance = wallet_manager.get_balance(new_wallet['address'])
    # print(f"Balance: {balance['balance_eth']} ETH\n")

    # Test importing wallet
    # pk wallet generated
    # private_key = "0x1f05d303ae67c5479a1bf55608aa127f4bc519545af688409021f0b5716ef7dc"
    # Personal pk metamask
    private_key = "0x4a8f7b838f539de1392bf281f92808ed6f1aa76ec254db501a82b4d4a98b8ce1"
    imported_wallet = wallet_manager.import_wallet(private_key)
    print(f"Personal Metamask Wallet: \n")
    print(f"Imported wallet address: {imported_wallet['address']}")
    balance = wallet_manager.get_balance(imported_wallet['address'])
    print(f"Balance: {balance['balance_eth']} ETH")


if __name__ == "__main__":
    main()
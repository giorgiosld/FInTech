import hashlib
import ecdsa
import os
import bech32
import requests

from persistence_tx import PersistentTransactionManager

class BitcoinWallet:
    def __init__(self):
        self.private_key = None
        self.public_key = None
        self.public_key_hex = None
        self.address = None
        self.MEMPOOL_API = "https://mempool.space/testnet4/api"

    def generate_wallet(self):
        self.private_key = os.urandom(32)

        signing_key = ecdsa.SigningKey.from_string(self.private_key, curve=ecdsa.SECP256k1)
        verifying_key = signing_key.get_verifying_key()
        public_key_bytes = verifying_key.to_string()

        # Store both raw and compressed public key
        self.public_key = public_key_bytes
        self.public_key_hex = (b'\x02' + public_key_bytes[0:32]).hex()

        # Generate Native SegWit address
        sha256_hash = hashlib.sha256(bytes.fromhex(self.public_key_hex)).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        keyhash = ripemd160.digest()

        witver = 0
        witprog = keyhash
        self.address = bech32.encode('tb', witver, witprog)

    def import_wallet(self, private_key_hex):
        self.private_key = bytes.fromhex(private_key_hex)

        signing_key = ecdsa.SigningKey.from_string(self.private_key, curve=ecdsa.SECP256k1)
        verifying_key = signing_key.get_verifying_key()
        public_key_bytes = verifying_key.to_string()

        self.public_key = public_key_bytes
        self.public_key_hex = (b'\x02' + public_key_bytes[0:32]).hex()

        sha256_hash = hashlib.sha256(bytes.fromhex(self.public_key_hex)).digest()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(sha256_hash)
        keyhash = ripemd160.digest()

        witver = 0
        witprog = keyhash
        self.address = bech32.encode('tb', witver, witprog)

    def get_balance(self):
        try:
            response = requests.get(f"{self.MEMPOOL_API}/address/{self.address}")
            if response.status_code == 200:
                data = response.json()
                stats = data.get('chain_stats', {})
                mempool = data.get('mempool_stats', {})

                # Convert from satoshis
                confirmed = stats.get('funded_txo_sum', 0) - stats.get('spent_txo_sum', 0)
                unconfirmed = mempool.get('funded_txo_sum', 0) - mempool.get('spent_txo_sum', 0)

                return {
                    'confirmed_balance': confirmed,
                    'unconfirmed_balance': unconfirmed,
                    'total_balance': confirmed + unconfirmed,
                    'btc_balance': confirmed / 100000000  # Convert to BTC
                }
            return None
        except requests.RequestException:
            return None

    def export_keys(self):
        return {
            'private_key': self.private_key.hex(),
            'public_key': self.public_key_hex,
            'address': self.address,
            'balance': self.get_balance()
        }


if __name__ == "__main__":
    # Create a new wallet
    # wallet = BitcoinWallet()
    # wallet.generate_wallet()
    # data = wallet.export_keys()
    #
    # print(f"Address (SegWit): {data['address']}")
    # print(f"Private key: {data['private_key']}")
    # print(f"Public key (compressed): {data['public_key']}")
    # print(f"Balance: {data['balance']}")

    # Create a persistent transaction manager
    manager = PersistentTransactionManager()

    # Wallet 1
    wallet1 = BitcoinWallet()
    wallet1.generate_wallet()
    manager.initialize_wallet(wallet1, 5)  # Initialize with 5 BTC

    # Wallet 2
    wallet2 = BitcoinWallet()
    wallet2.generate_wallet()
    manager.initialize_wallet(wallet2, 2)  # Initialize with 2 BTC

    # Print wallet details
    print(f"Wallet 1 Details: {manager.get_wallet_details(wallet1.address)}")
    print(f"Wallet 2 Details: {manager.get_wallet_details(wallet2.address)}")

    # Perform an internal transaction
    result = manager.transfer(wallet1.address, wallet2.address, 1.5)
    print(result)

    print(f"Wallet 1 Balance: {manager.get_wallet_balance(wallet1.address)} BTC")
    print(f"Wallet 2 Balance: {manager.get_wallet_balance(wallet2.address)} BTC")
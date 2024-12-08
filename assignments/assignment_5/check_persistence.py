import json
import os

class LedgerReader:
    def __init__(self, filename="ledger.json"):
        self.filename = filename
        self.ledger = self.load_ledger()

    def load_ledger(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as file:
                return json.load(file)
        return {}

    def get_all_wallets(self):
        return self.ledger

    def get_wallet_details(self, address):
        return self.ledger.get(address, "Wallet not found.")

# Example usage
if __name__ == "__main__":
    reader = LedgerReader()

    # Load all wallets
    wallets = reader.get_all_wallets()
    if not wallets:
        print("No wallets found in ledger.")
    else:
        print("Persisted Wallets:")
        for address, details in wallets.items():
            print(f"Address: {address}")
            print(f"  Private Key: {details['private_key']}")
            print(f"  Public Key: {details['public_key']}")
            print(f"  Balance: {details['balance']} BTC")
            print()

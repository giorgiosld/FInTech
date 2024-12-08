import json
import os


class PersistentTransactionManager:
    def __init__(self, filename="ledger.json"):
        self.filename = filename
        self.ledger = self.load_ledger()

    def load_ledger(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as file:
                return json.load(file)
        return {}

    def save_ledger(self):
        with open(self.filename, 'w') as file:
            json.dump(self.ledger, file)

    def initialize_wallet(self, wallet, initial_balance=0):
        wallet_details = wallet.export_keys()
        address = wallet_details['address']
        if address not in self.ledger:
            self.ledger[address] = {
                'private_key': wallet_details['private_key'],
                'public_key': wallet_details['public_key'],
                'balance': initial_balance
            }
            self.save_ledger()

    def get_wallet_balance(self, address):
        wallet = self.ledger.get(address)
        return wallet['balance'] if wallet else 0

    def transfer(self, sender_address, recipient_address, amount):
        sender_wallet = self.ledger.get(sender_address)
        recipient_wallet = self.ledger.get(recipient_address)
        if not sender_wallet:
            return "Sender wallet not found in ledger."
        if not recipient_wallet:
            return "Recipient wallet not found in ledger."
        if sender_wallet['balance'] < amount:
            return "Insufficient funds."

        sender_wallet['balance'] -= amount
        recipient_wallet['balance'] += amount
        self.save_ledger()
        return f"Transfer of {amount} BTC from {sender_address} to {recipient_address} completed."

    def get_wallet_details(self, address):
        return self.ledger.get(address, "Wallet not found.")


# Reuse wallets from the ledger
if __name__ == "__main__":
    manager = PersistentTransactionManager()

    # Load persisted wallets
    ledger = manager.load_ledger()
    if len(ledger) < 2:
        print("Not enough wallets in the ledger for a transaction.")
    else:
        addresses = list(ledger.keys())
        wallet1_address = addresses[0]
        wallet2_address = addresses[1]

        print(f"Wallet 1 Balance: {manager.get_wallet_balance(wallet1_address)} BTC")
        print(f"Wallet 2 Balance: {manager.get_wallet_balance(wallet2_address)} BTC")

        # Perform a transaction
        amount = 1.0  # BTC to transfer
        result = manager.transfer(wallet1_address, wallet2_address, amount)
        print(result)

        # Check updated balances
        print(f"Updated Wallet 1 Balance: {manager.get_wallet_balance(wallet1_address)} BTC")
        print(f"Updated Wallet 2 Balance: {manager.get_wallet_balance(wallet2_address)} BTC")

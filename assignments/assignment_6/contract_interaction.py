from web3 import Web3
from solcx import compile_source, set_solc_version
from eth_account import Account
import sys


class GiftContractMenu:
    """
    A class to manage the interaction with a shared gift smart contract on the Sepolia test network.
    """
    def __init__(self, infura_url, contract_address):
        self.web3 = Web3(Web3.HTTPProvider(infura_url))
        self.contract_address = contract_address
        set_solc_version('0.8.0')

        # Compile contract to get ABI
        with open('shared_gift.sol', 'r') as file:
            contract_source = file.read()

        compiled_sol = compile_source(contract_source)
        contract_interface = compiled_sol['<stdin>:SharedGift']

        # Create contract instance
        self.contract = self.web3.eth.contract(
            address=contract_address,
            abi=contract_interface['abi']
        )

    def get_target_amount(self):
        """
        Retrieves the target amount of the contract.

        :return: A dictionary containing the target amount in Wei and Ether.
        """
        target_wei = self.contract.functions.targetAmount().call()
        return {
            'wei': target_wei,
            'eth': self.web3.from_wei(target_wei, 'ether')
        }

    def get_total_contributed(self):
        """
        Retrieves the total amount contributed to the contract.

        :return: A dictionary containing the total amount contributed in Wei and Ether.
        """
        total_wei = self.contract.functions.totalContributed().call()
        return {
            'wei': total_wei,
            'eth': self.web3.from_wei(total_wei, 'ether')
        }

    def get_contribution(self, address):
        """
        Retrieves the contribution of a specific address.

        :param address: The address to check the contribution for.
        :return: A dictionary containing the contribution amount in Wei and Ether.
        """
        contribution_wei = self.contract.functions.contributions(address).call()
        return {
            'wei': contribution_wei,
            'eth': self.web3.from_wei(contribution_wei, 'ether')
        }

    def get_all_contributors(self):
        """
        Retrieves all contributors to the contract.

        :return: A list of addresses that have contributed to the contract.
        """
        return self.contract.functions.getContributors().call()

    def is_completed(self):
        """
        Checks if the gift has been purchased.

        :return: True if the gift has been purchased, False otherwise.
        """
        return self.contract.functions.isCompleted().call()

    def contribute(self, amount_eth, private_key):
        """
        Contributes a specified amount of Ether to the contract.

        :param amount_eth: The amount of Ether to contribute.
        :param private_key: The private key of the contributor.
        :return: The transaction receipt if the contribution is successful, None otherwise.
        """
        try:
            account = Account.from_key(private_key)
            amount_wei = self.web3.to_wei(amount_eth, 'ether')

            print("\nPreparing transaction...")

            # Get current gas price and add 10% to speed up transaction
            gas_price = int(self.web3.eth.gas_price * 1.1)

            transaction = self.contract.functions.contribute().build_transaction({
                'from': account.address,
                'value': amount_wei,
                'gas': 200000,
                'gasPrice': gas_price,
                'nonce': self.web3.eth.get_transaction_count(account.address),
                'chainId': 11155111
            })

            print("Signing transaction...")
            signed_txn = self.web3.eth.account.sign_transaction(transaction, private_key)

            print("Sending transaction...")
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"Transaction hash: {tx_hash.hex()}")
            print("Waiting for transaction confirmation...")

            # Increase timeout to 300 seconds (5 minutes)
            tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)

            if tx_receipt['status'] == 1:
                return tx_receipt
            else:
                raise Exception("Transaction failed")

        except Exception as e:
            print(f"Error contributing: {e}")
            print("\nPossible reasons for failure:")
            print("1. Network congestion")
            print("2. Insufficient funds for gas")
            print("3. Transaction underpriced")
            print("\nYou can check the transaction status on Sepolia Etherscan:")
            print(f"https://sepolia.etherscan.io/tx/0x{tx_hash.hex()}")
            return None

    def purchase_gift(self, recipient_address, private_key):
        """
        Purchases the gift for the specified recipient.

        :param recipient_address: The address of the recipient.
        :param private_key: The private key of the purchaser.
        :return: The transaction receipt of the purchase.
        """
        account = Account.from_key(private_key)

        transaction = self.contract.functions.purchaseGift(recipient_address).build_transaction({
            'from': account.address,
            'gas': 200000,
            'gasPrice': self.web3.eth.gas_price,
            'nonce': self.web3.eth.get_transaction_count(account.address),
            'chainId': 11155111
        })

        signed_txn = self.web3.eth.account.sign_transaction(transaction, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
        return self.web3.eth.wait_for_transaction_receipt(tx_hash)


def print_menu():
    print("\n=== Shared Gift Contract Menu ===")
    print("1. View Target Amount")
    print("2. View Total Contributions")
    print("3. View My Contribution")
    print("4. View All Contributors")
    print("5. Make a Contribution")
    print("6. Purchase Gift")
    print("7. Check if Gift is Purchased")
    print("8. Exit")
    print("=============================")


def main():
    INFURA_URL = "https://sepolia.infura.io/v3/62a758774e20472b9bbd03c00839bccb"
    CONTRACT_ADDRESS = "0x9Efa66858191795c83000F1F9ffF10c2c620dE26"

    # Initialize contract
    gift = GiftContractMenu(INFURA_URL, CONTRACT_ADDRESS)

    while True:
        print_menu()
        choice = input("Enter your choice (1-8): ")

        if choice == '1':
            target = gift.get_target_amount()
            print(f"\nTarget amount: {target['eth']} ETH")

        elif choice == '2':
            total = gift.get_total_contributed()
            print(f"\nTotal contributed: {total['eth']} ETH")

        elif choice == '3':
            address = input("\nEnter your wallet address: ")
            try:
                contribution = gift.get_contribution(address)
                print(f"Your contribution: {contribution['eth']} ETH")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == '4':
            contributors = gift.get_all_contributors()
            print("\nContributors:")
            for contributor in contributors:
                contribution = gift.get_contribution(contributor)
                print(f"Address: {contributor}")
                print(f"Contributed: {contribution['eth']} ETH")

        elif choice == '5':
            amount = float(input("\nEnter amount to contribute (in ETH): "))
            private_key = input("Enter your private key: ")
            try:
                print("\nInitiating contribution...")
                tx_receipt = gift.contribute(amount, private_key)
                if tx_receipt:
                    print(f"\nContribution successful!")
                    print(f"Transaction hash: {tx_receipt['transactionHash'].hex()}")
                    print(f"Gas used: {tx_receipt['gasUsed']}")
                    print(f"Block number: {tx_receipt['blockNumber']}")
                    print(f"\nView on Etherscan: https://sepolia.etherscan.io/tx/{tx_receipt['transactionHash'].hex()}")
            except Exception as e:
                print(f"Error: {e}")


        elif choice == '6':
            if not gift.is_completed():
                recipient = input("\nEnter recipient address: ")
                private_key = input("Enter your private key: ")
                try:
                    tx_receipt = gift.purchase_gift(recipient, private_key)
                    print(f"Gift purchased! Transaction: {tx_receipt.transactionHash.hex()}")
                except Exception as e:
                    print(f"Error: {e}")
            else:
                print("\nGift has already been purchased!")

        elif choice == '7':
            completed = gift.is_completed()
            print(f"\nGift purchased: {'Yes' if completed else 'No'}")

        elif choice == '8':
            print("\nGoodbye!")
            sys.exit()

        else:
            print("\nInvalid choice. Please try again.")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
from bitcoinlib.transactions import Transaction
from bitcoinlib.keys import Key
import requests


def get_utxos_from_mempool(address):
    url = f"https://mempool.space/testnet4/api/address/{address}/utxo"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    raise Exception(f"Failed to get UTXOs: {response.text}")


def send_raw_transaction(raw_tx):
    url = "https://mempool.space/testnet4/api/tx"
    headers = {'Content-Type': 'text/plain'}
    response = requests.post(url, data=raw_tx, headers=headers)
    if response.status_code == 200:
        return response.text
    raise Exception(f"Failed to broadcast: {response.text}")


def create_and_sign_transaction(from_address, from_private_key, to_address, amount_satoshi, fee=1000):
    # Create signing key
    key = Key(from_private_key, network='testnet')

    # Get UTXOs
    utxos = get_utxos_from_mempool(from_address)
    if not utxos:
        raise Exception("No UTXOs found")

    total_input = 0

    # Create transaction
    tx = Transaction(network='testnet', witness_type='segwit')

    # Add all necessary inputs
    for utxo in utxos:
        if total_input < amount_satoshi + fee:
            tx.add_input(
                utxo['txid'],
                utxo['vout'],
                keys=key,
                value=utxo['value'],
                sequence=0xffffffff,
                script_type='sig_pubkey',
                address=from_address
            )
            total_input += utxo['value']
            print(f"Added input: {utxo['txid']}:{utxo['vout']} with value {utxo['value']}")

    if total_input < amount_satoshi + fee:
        raise Exception(f"Insufficient funds. Need {amount_satoshi + fee}, got {total_input}")

    # Add the payment output
    tx.add_output(amount_satoshi, to_address)

    # Add change output if necessary
    change = total_input - amount_satoshi - fee
    if change > 0:
        tx.add_output(change, from_address)

    # Sign each input
    tx.sign(key)

    # Get the raw transaction
    raw_tx = tx.raw_hex()

    # Print details for verification
    print("\nTransaction Details:")
    print(f"From: {from_address}")
    print(f"To: {to_address}")
    print(f"Amount: {amount_satoshi} satoshis")
    print(f"Fee: {fee} satoshis")
    if change > 0:
        print(f"Change: {change} satoshis")
    print(f"Raw transaction: {raw_tx}")

    # Broadcast transaction
    txid = send_raw_transaction(raw_tx)
    return txid


# Your wallet details
from_address = "tb1q9p3l9vw0cys52whwwcqlyfrx0e79hhw6tcarph"
from_private_key = "411305c15a463e07a3c79275377b4c89d5bb024c9570242f9e042a6add2a10f8"
to_address = "tb1qvluudwjwumquymeyzddww9z6v6x6rw3ld07kk3"
amount = 100000  # 0.001 BTC in satoshis
fee = 1000  # 1000 satoshis fee

try:
    txid = create_and_sign_transaction(from_address, from_private_key, to_address, amount, fee)
    print(f"\nTransaction successful!")
    print(f"Transaction ID: {txid}")
    print(f"View at: https://mempool.space/testnet4/tx/{txid}")
except Exception as e:
    print(f"Error: {str(e)}")
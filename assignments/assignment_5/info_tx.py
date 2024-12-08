import requests

def get_tx_details(txid):
    url = f"https://mempool.space/testnet4/api/tx/{txid}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        raise ValueError(f"Failed to fetch transaction data: {response.text}")

# Get details of the input transaction
# tx_details = get_tx_details("d37b3a00a6be292689e4ea02b4b8f00bde3776b556e6ae03abdf7e7fa2edda16")
tx_details = get_tx_details("7a99bbfc63a040c8035272e147f7ff125463c189c4a90b6ee8736c0879e452f4")
print("Transaction details:", tx_details)
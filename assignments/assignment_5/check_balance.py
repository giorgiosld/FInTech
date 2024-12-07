from wallet import BitcoinWallet
import requests


def check_balance_by_private_key(private_key):
    wallet = BitcoinWallet()
    wallet.import_wallet(private_key)
    return wallet.get_balance()


def check_balance_by_address(address):
    MEMPOOL_API = "https://mempool.space/testnet4/api"
    try:
        response = requests.get(f"{MEMPOOL_API}/address/{address}")
        if response.status_code == 200:
            data = response.json()
            chain_stats = data.get('chain_stats', {})
            mempool_stats = data.get('mempool_stats', {})

            confirmed = chain_stats.get('funded_txo_sum', 0) - chain_stats.get('spent_txo_sum', 0)
            unconfirmed = mempool_stats.get('funded_txo_sum', 0) - mempool_stats.get('spent_txo_sum', 0)

            return {
                'confirmed_balance': confirmed,
                'unconfirmed_balance': unconfirmed,
                'total_balance': confirmed + unconfirmed,
                'btc_balance': confirmed / 100000000
            }
    except requests.RequestException:
        return None


private_key = "411305c15a463e07a3c79275377b4c89d5bb024c9570242f9e042a6add2a10f8"
address = "tb1q9p3l9vw0cys52whwwcqlyfrx0e79hhw6tcarph"

print("Balance Wallet 1 using private key:", check_balance_by_private_key(private_key))
print("Balance Wallet 1 using address:", check_balance_by_address(address))

private_key = "3f79fc4b208a7618a7dfc68684b0eb23efbcbc874c2565af941717c3cbb43d94"
address = "tb1qvluudwjwumquymeyzddww9z6v6x6rw3ld07kk3"

print("Balance Wallet 2 using private key:", check_balance_by_private_key(private_key))
print("Balance Wallet 2 using address:", check_balance_by_address(address))
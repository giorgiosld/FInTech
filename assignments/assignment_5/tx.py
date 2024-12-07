import hashlib
import ecdsa
import struct
import requests
from bech32 import decode

def decode_bech32(addr):
    """Decode a bech32 address and return the witness program."""
    hrp = "tb"
    hrp, data = decode(hrp, addr)
    if data is None:
        raise ValueError("Invalid address")
    return bytes(data)

def hash160(data):
    """Perform the RIPEMD160(SHA256()) operation on data."""
    sha256_hash = hashlib.sha256(data).digest()
    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
    return ripemd160_hash

def hex_to_bytes(hex_str):
    return bytes.fromhex(hex_str)

def int_to_little_endian(value, length):
    return value.to_bytes(length, byteorder='little')

def double_sha256(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()

# Transaction parameters
sender_address = "tb1q9p3l9vw0cys52whwwcqlyfrx0e79hhw6tcarph"
recipient_address = "tb1qvluudwjwumquymeyzddww9z6v6x6rw3ld07kk3"
private_key_hex = "411305c15a463e07a3c79275377b4c89d5bb024c9570242f9e042a6add2a10f8"
sender_public_key_hex = "02bb9dc904e8c43f8945ef26f7e601d230797ea39f4ef9d92908b3a70338ebb89c"

# UTXO data
utxo_txid = "4134a6ee0657f1c6b257e0b41562a47f52c1f1bb5c506d22f81ef1ad2dd637dc"
utxo_vout = 0
utxo_amount = 100000

# Calculate P2WPKH script from public key
pubkey_hash = hash160(hex_to_bytes(sender_public_key_hex))
p2wpkh_script = bytes([0x19, 0x76, 0xa9, 0x14]) + pubkey_hash + bytes([0x88, 0xac])

# Transaction amounts
recipient_amount = 50000
fee = 10000
change_amount = utxo_amount - recipient_amount - fee

# Create transaction structure
version = int_to_little_endian(2, 4)
marker = b'\x00'
flag = b'\x01'
input_count = b'\x01'
output_count = b'\x02'
locktime = b'\x00\x00\x00\x00'

# Input
txid = bytes.fromhex(utxo_txid)[::-1]
vout = int_to_little_endian(utxo_vout, 4)
sequence = b'\xff\xff\xff\xff'
script_sig = b''
script_sig_length = b'\x00'

input_field = (
    txid +
    vout +
    script_sig_length +
    script_sig +
    sequence
)

# Outputs
recipient_value = int_to_little_endian(recipient_amount, 8)
recipient_witness_program = decode_bech32(recipient_address)
recipient_script_pubkey = b'\x00\x14' + recipient_witness_program
recipient_script_length = struct.pack('B', len(recipient_script_pubkey))

change_value = int_to_little_endian(change_amount, 8)
change_witness_program = decode_bech32(sender_address)
change_script_pubkey = b'\x00\x14' + change_witness_program
change_script_length = struct.pack('B', len(change_script_pubkey))

output_field = (
    recipient_value +
    recipient_script_length +
    recipient_script_pubkey +
    change_value +
    change_script_length +
    change_script_pubkey
)

# Create the BIP143 sighash
hashPrevouts = double_sha256(txid + vout)
hashSequence = double_sha256(sequence)
hashOutputs = double_sha256(output_field)

# Build the preimage
sighash_preimage = (
    version +
    hashPrevouts +
    hashSequence +
    txid +
    vout +
    p2wpkh_script +  # Use P2WPKH script for signing
    int_to_little_endian(utxo_amount, 8) +
    sequence +
    hashOutputs +
    locktime +
    int_to_little_endian(1, 4)  # SIGHASH_ALL
)

# Calculate sighash and sign
sighash = double_sha256(sighash_preimage)
private_key_bytes = hex_to_bytes(private_key_hex)
sk = ecdsa.SigningKey.from_string(private_key_bytes, curve=ecdsa.SECP256k1)

# Sign with low-S value
vk = sk.get_verifying_key()
while True:
    signature = sk.sign_digest(sighash, sigencode=ecdsa.util.sigencode_der)
    r, s = ecdsa.util.sigdecode_der(signature, sk.curve.generator.order())
    if s <= sk.curve.generator.order() // 2:
        break
    s = sk.curve.generator.order() - s
    signature = ecdsa.util.sigencode_der(r, s, sk.curve.generator.order())

signature = signature + b'\x01'  # Append SIGHASH_ALL

# Create witness
witness = (
    b'\x02' +  # Number of witness items
    struct.pack('B', len(signature)) + signature +
    struct.pack('B', len(hex_to_bytes(sender_public_key_hex))) + hex_to_bytes(sender_public_key_hex)
)

# Construct final transaction
final_tx = (
    version +
    marker +
    flag +
    input_count +
    input_field +
    output_count +
    output_field +
    witness +
    locktime
)

# Convert to hex and broadcast
raw_transaction = final_tx.hex()
print("Raw Transaction:", raw_transaction)

# Broadcast transaction
response = requests.post(
    "https://mempool.space/testnet4/api/tx",
    headers={"Content-Type": "text/plain"},
    data=raw_transaction
)

if response.status_code == 200:
    print("Transaction successfully broadcasted!")
    print("Transaction ID:", response.text)
else:
    print("Failed to broadcast transaction:", response.text)
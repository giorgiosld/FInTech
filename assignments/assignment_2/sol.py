import hashlib
import secrets
import string
import time


def generate_random_token(size: int = 64) -> str:
    """Generate a cryptographically secure random token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(size))


def calculate_hash(sequence: int, payload: str, nonce: int, prev_hash: str) -> str:
    """Calculate SHA256 hash of the block contents."""
    content = f"{sequence}{payload}{nonce}{prev_hash}".encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def mine_block(sequence: int, prev_hash: str, target_zeros: int) -> tuple[str, str, int, int]:
    """
    Mine a single block with required leading zeros.
    Returns: (payload, hash, nonce, attempts)
    """
    payload = generate_random_token()
    nonce = secrets.randbelow(2 ** 32)
    attempts = 0
    target = '0' * target_zeros

    while True:
        attempts += 1
        current_hash = calculate_hash(sequence, payload, nonce, prev_hash)

        if current_hash.startswith(target):
            return payload, current_hash, nonce, attempts

        nonce = (nonce + 1) & 0xffffffff


def mine_chain(target_zeros: int, max_blocks: int = 1000, time_limit_minutes: int = 90) -> tuple[list[dict], dict]:
    """
    Mine a chain of blocks with given difficulty.
    Returns the chain and mining statistics.
    """
    chain = []
    time_limit = time_limit_minutes * 60
    start_time = time.time()
    prev_hash = '0'
    attempts_list = []

    for i in range(max_blocks):
        # Check time limit
        if time.time() - start_time > time_limit:
            print(f"Time limit reached after {i} blocks")
            break

        # Mine next block
        payload, curr_hash, nonce, attempts = mine_block(i, prev_hash, target_zeros)

        # Store block
        block = {
            'sequence': i,
            'payload': payload,
            'nonce': nonce,
            'prev_hash': prev_hash,
            'curr_hash': curr_hash,
            'attempts': attempts
        }
        chain.append(block)
        attempts_list.append(attempts)

        prev_hash = curr_hash

        if i % 10 == 0:
            print(f"Mined block {i}, took {attempts} attempts")

    # Calculate statistics
    stats = {
        'chain_length': len(chain),
        'total_attempts': sum(attempts_list),
        'avg_attempts': sum(attempts_list) / len(attempts_list) if attempts_list else 0,
        'min_attempts': min(attempts_list) if attempts_list else 0,
        'max_attempts': max(attempts_list) if attempts_list else 0,
        'duration': time.time() - start_time
    }

    return chain, stats


def run_experiment(k: int, blocks: int = 1000) -> None:
    """Run mining experiment for specific number of leading zeros."""
    print(f"\nExperiment with k={k} leading zeros:")
    chain, stats = mine_chain(target_zeros=k, max_blocks=blocks)

    print(f"Chain length: {stats['chain_length']} blocks")
    print(f"Duration: {stats['duration']:.2f} seconds")
    print(f"Average attempts per block: {stats['avg_attempts']:.2f}")
    print(f"Min attempts: {stats['min_attempts']}")
    print(f"Max attempts: {stats['max_attempts']}")
    print(f"Total hash calculations: {stats['total_attempts']}")


if __name__ == "__main__":
    debug_blocks = 1000

    for k in [4, 6, 8]:
        run_experiment(k, debug_blocks)
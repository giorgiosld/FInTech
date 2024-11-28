import random
import time
from typing import List, Tuple


def is_prime(n: int, k: int = 5) -> bool:
    """
    Miller-Rabin primality test implementation.
    """
    if n <= 3:
        return n == 2 or n == 3
    if n % 2 == 0:
        return False

    # Write n - 1 as 2^s * d
    s = 0
    d = n - 1
    while d % 2 == 0:
        d //= 2
        s += 1

    # Witness Loop
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)

        if x == 1 or x == n - 1:
            continue

        for __ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def find_primes(n: int) -> Tuple[List[int], float, int]:
    """
    Find 5 random prime numbers in the range [2, n-1].
    """
    primes_found: List[int] = []
    total_start = time.time()
    attempts = 0

    while len(primes_found) < 5:
        num = random.randint(2, n - 1)
        attempts += 1
        if is_prime(num):
            print(f"Prime found: {num}")
            primes_found.append(num)

    total_time = time.time() - total_start
    print(f"Total Time Elapsed: {total_time:.6f} seconds over {attempts} attempts")
    return primes_found, total_time, attempts


def main() -> None:
    """
    Main function to test primality in different Mersenne number fields.
    Tests primality for numbers in fields of size 2^a - 1 where a is in [64, 128, 256, 1024, 4096].
    """
    a_values: List[int] = [64, 128, 256, 1024, 4096]

    for a in a_values:
        n = 2 ** a - 1
        print(f"\nPrimality Testing in Z_{n} where a = {a}")
        find_primes(n)


if __name__ == "__main__":
    main()
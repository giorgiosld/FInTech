import random
import time
from typing import List


def generate_random_numbers(n: int, k: int) -> List[int]:
    """Generate k random numbers in Zn."""
    return [random.randint(0, n - 1) for _ in range(k)]


def modular_add(numbers: List[int], n: int) -> int:
    """Perform modular addition."""
    result = 0
    for num in numbers:
        result = (result + num) % n
    return result


def modular_subtract(numbers: List[int], n: int) -> int:
    """Perform modular subtraction."""
    result = numbers[0]
    for num in numbers[1:]:
        result = (result - num) % n
    return result


def modular_multiply(numbers: List[int], n: int) -> int:
    """Perform modular multiplication."""
    result = 1
    for num in numbers:
        result = (result * num) % n
    return result


def modular_divide(numbers: List[int], n: int) -> int:
    """
    Perform modular division using Fermat's Little Theorem.
    For prime modulus n, a^(n-2) ≡ a^(-1) (mod n)
    """
    result = numbers[0]
    for num in numbers[1:]:
        inverse = pow(num, n - 2, n)
        result = (result * inverse) % n
    return result


def modular_exponentiation(numbers: List[int], n: int) -> int:
    """Perform modular exponentiation starting with 1."""
    result = 1
    for num in numbers:
        result = pow(result, num, n)
    return result


def benchmark_operations(n: int, k: int, iterations: int = 100) -> dict:
    """Benchmark different modular operations."""
    operations = {
        'Addition': modular_add,
        'Subtraction': modular_subtract,
        'Multiplication': modular_multiply,
        'Division': modular_divide,
        'Exponentiation': modular_exponentiation
    }

    times = {op: 0.0 for op in operations}
    times_per_iteration = {op: [] for op in operations}

    for _ in range(iterations):
        numbers = generate_random_numbers(n, k)
        for op_name, op_func in operations.items():
            start_time = time.time()
            try:
                _ = op_func(numbers, n)
                elapsed = time.time() - start_time
                times[op_name] += elapsed
                times_per_iteration[op_name].append(elapsed)
            except Exception as e:
                print(f"Error in {op_name}: {str(e)}")
                times[op_name] += 0
                times_per_iteration[op_name].append(0)

    avg_times = {op: sum(t) / len(t) for op, t in times_per_iteration.items()}
    total_time = sum(times.values())
    percentages = {op: (t / total_time) * 100 for op, t in times.items()}

    return {
        'total_time': total_time,
        'operation_times': times,
        'average_times': avg_times,
        'percentages': percentages
    }


def main():
    k = 10000
    a_values = [64, 128, 256, 1024, 4096]

    for a in a_values:
        n = 2 ** a - 1
        print(f"\nBenchmarking for n = 2^{a} - 1 ({n})")
        print("-" * 80)

        try:
            results = benchmark_operations(n, k)

            print(f"Total execution time: {results['total_time']:.4f} seconds\n")
            print("Detailed breakdown per operation:")
            print("{:<15} {:<15} {:<15} {:<15}".format(
                "Operation", "Total Time(s)", "Avg Time(s)", "Percentage(%)"
            ))
            print("-" * 60)

            for op in results['operation_times'].keys():
                print("{:<15} {:<15.4f} {:<15.6f} {:<15.2f}".format(
                    op,
                    results['operation_times'][op],
                    results['average_times'][op],
                    results['percentages'][op]
                ))

        except Exception as e:
            print(f"Error processing n = 2^{a} - 1: {str(e)}")
            continue


if __name__ == "__main__":
    main()
import subprocess
import sys
import time


def bootstrap_network(n: int):
    processes = []
    base_port = 8000

    # Start all peers almost simultaneously
    for i in range(n):
        cmd = ["python", "peer.py", str(i), str(n), str(base_port + i)]
        process = subprocess.Popen(cmd)
        processes.append(process)
        time.sleep(0.1)

    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        for process in processes:
            process.terminate()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python bootstrap.py <number_of_peers>")
        sys.exit(1)

    n = int(sys.argv[1])
    bootstrap_network(n)
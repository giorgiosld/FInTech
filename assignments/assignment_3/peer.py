import socket
import threading
import time
import random
import json
import sys
import signal
from datetime import datetime


class Peer:
    def __init__(self, port, total_peers, peer_ports):
        self.port = port
        self.peer_id = port - peer_ports[0]
        self.N = total_peers
        self.peer_ports = peer_ports
        self.connections = {}
        self.connected_peers = set()
        self.received_messages = 0
        self.start_time = datetime.now()
        self.active_time = None
        self.fully_connected_time = None
        self.lock = threading.Lock()
        self.terminated = False

        # Initialize connection status
        for p in peer_ports:
            if p != port:
                self.connections[p] = False

        print(f"Peer {self.peer_id} starting on port {port}")
        print(f"Looking for peers on ports: {[p for p in peer_ports if p != port]}")

        # Setup server socket
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', port))
            self.server_socket.listen(total_peers)
            print(f"Peer {self.peer_id} listening on port {port}")
        except Exception as e:
            print(f"Error setting up server socket: {e}")
            sys.exit(1)

        # Start listener thread
        self.listener_thread = threading.Thread(target=self.listen_for_connections)
        self.listener_thread.daemon = True
        self.listener_thread.start()

        # Start connection thread
        self.connector_thread = threading.Thread(target=self.connect_to_peers)
        self.connector_thread.daemon = True
        self.connector_thread.start()

        # Start status printing thread
        self.status_thread = threading.Thread(target=self.print_status)
        self.status_thread.daemon = True
        self.status_thread.start()

    def print_status(self):
        """Periodically print peer status"""
        while not self.terminated:
            with self.lock:
                connected = len(self.connected_peers)
                total = self.N - 1
                messages = self.received_messages
                print(f"\nPeer {self.peer_id} Status:")
                print(f"Connected to {connected}/{total} peers")
                print(f"Received {messages} messages")
                print(f"Connected peers: {sorted(list(self.connected_peers))}")
            time.sleep(5)  # Update every 5 seconds

    def listen_for_connections(self):
        """Listen for incoming connections from other peers"""
        print(f"Peer {self.peer_id} starting listener thread")
        while not self.terminated:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"Peer {self.peer_id} accepted connection from {addr}")
                thread = threading.Thread(target=self.handle_connection, args=(client_socket,))
                thread.daemon = True
                thread.start()
            except Exception as e:
                if not self.terminated:
                    print(f"Listener error: {e}")
                break

    def handle_connection(self, client_socket):
        """Handle incoming messages from connected peers"""
        while not self.terminated:
            try:
                data = client_socket.recv(4096)
                if not data:
                    break

                message = json.loads(data.decode())

                if message['type'] == 'status_update':
                    with self.lock:
                        self.received_messages += 1
                        peer_connections = message['connections']
                        for port, status in peer_connections.items():
                            if int(port) in self.connections:
                                self.connections[int(port)] = status

                        print(f"\nPeer {self.peer_id} received status update. Total messages: {self.received_messages}")

                        # Check if we've received enough messages to terminate
                        if self.received_messages >= (2 * self.N) // 3:
                            print(f"Peer {self.peer_id} received enough messages, broadcasting terminate")
                            self.broadcast_terminate()

                elif message['type'] == 'terminate':
                    print(f"Peer {self.peer_id} received terminate message")
                    self.terminate()

            except Exception as e:
                print(f"Handle connection error: {e}")
                break

        client_socket.close()

    def connect_to_peers(self):
        """Attempt to connect to all other peers"""
        print(f"Peer {self.peer_id} starting connector thread")
        while not self.terminated:
            for peer_port in self.peer_ports:
                if peer_port != self.port and peer_port not in self.connected_peers:
                    try:
                        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client_socket.connect(('localhost', peer_port))
                        with self.lock:
                            self.connected_peers.add(peer_port)
                            self.connections[peer_port] = True
                            print(f"\nPeer {self.peer_id} connected to peer on port {peer_port}")

                            if len(self.connected_peers) > self.N // 2 and not self.active_time:
                                self.active_time = (datetime.now() - self.start_time).total_seconds()
                                print(f"Peer {self.peer_id} is now active (>N/2 connections)")

                            if len(self.connected_peers) == self.N - 1 and not self.fully_connected_time:
                                self.fully_connected_time = (datetime.now() - self.start_time).total_seconds()
                                print(f"Peer {self.peer_id} is fully connected")

                        thread = threading.Thread(target=self.status_message_loop, args=(client_socket,))
                        thread.daemon = True
                        thread.start()

                    except Exception as e:
                        time.sleep(0.1)

            time.sleep(0.1)

    def status_message_loop(self, socket):
        """Periodically send status messages once sufficiently connected"""
        while not self.terminated:
            if len(self.connected_peers) > self.N // 2:
                try:
                    message = {
                        'type': 'status_update',
                        'peer_id': self.peer_id,
                        'connections': {str(k): v for k, v in self.connections.items()}
                    }
                    socket.send(json.dumps(message).encode())
                    time.sleep(random.uniform(1.0, 2.0))  # Increased interval for better visibility
                except Exception as e:
                    print(f"Status message error: {e}")
                    break
            else:
                time.sleep(0.1)

    def broadcast_terminate(self):
        """Broadcast terminate message to all connected peers"""
        print(f"Peer {self.peer_id} broadcasting terminate message")
        message = {
            'type': 'terminate',
            'peer_id': self.peer_id
        }
        for peer_port in self.connected_peers:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', peer_port))
                sock.send(json.dumps(message).encode())
                sock.close()
            except Exception as e:
                print(f"Error broadcasting terminate to port {peer_port}: {e}")
                continue
        self.terminate()

    def terminate(self):
        """Clean shutdown of the peer"""
        if not self.terminated:
            self.terminated = True
            print(f"\nPeer {self.peer_id} Terminating:")
            print(f"Time to active: {self.active_time:.2f} seconds" if self.active_time else "Never became active")
            print(
                f"Time to fully connected: {self.fully_connected_time:.2f} seconds" if self.fully_connected_time else "Never fully connected")
            print("Connected peers:", sorted(list(self.connected_peers)))
            self.server_socket.close()
            sys.exit(0)


def main():
    if len(sys.argv) != 3:
        print("Usage: python script.py <peer_id> <total_peers>")
        sys.exit(1)

    peer_id = int(sys.argv[1])
    total_peers = int(sys.argv[2])
    base_port = 5000
    peer_ports = [base_port + i for i in range(total_peers)]

    print(f"Starting peer {peer_id} of {total_peers} total peers")
    peer = Peer(base_port + peer_id, total_peers, peer_ports)

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda s, f: peer.terminate())

    # Keep main thread alive
    while not peer.terminated:
        time.sleep(0.1)


if __name__ == "__main__":
    main()
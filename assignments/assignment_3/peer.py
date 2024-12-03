import asyncio
import json
import random
import time
from asyncio import StreamReader, StreamWriter
import logging
from typing import Dict, Set
import sys


class Peer:
    def __init__(self, host: str, port: int, peer_id: int, total_peers: int):
        self.host = host
        self.port = port
        self.id = peer_id
        self.total_peers = total_peers
        self.peers: Dict[int, tuple] = {}
        self.connected: Set[int] = set()
        self.messages_received: Dict[int, bool] = {}
        self.start_time = time.time()
        self.active_time = None
        self.fully_connected_time = None
        self.server = None
        self.terminate_received = False
        self.writers: Dict[int, StreamWriter] = {}
        self.is_active = False
        self.all_peers_connected = asyncio.Event()
        self.can_terminate = False
        self.tasks = set()

        # Configure logging
        self.logger = logging.getLogger(f"peer_{self.id}")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - Peer %(peer_id)s - %(message)s', datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log(self, msg: str, level: str = 'info'):
        getattr(self.logger, level)(msg, extra={'peer_id': self.id})

    async def start(self):
        try:
            self.server = await asyncio.start_server(
                self.handle_connection, self.host, self.port
            )
            self.log(f"Listening on {self.host}:{self.port}")

            await asyncio.sleep(1)

            base_port = 8000
            for i in range(self.total_peers):
                if i != self.id:
                    self.peers[i] = (self.host, base_port + i)

            connect_task = self.create_task(self.connect_to_peers())
            await connect_task

            async with self.server:
                await self.server.serve_forever()
        except asyncio.CancelledError:
            self.log("Peer disconnected")
        except Exception as e:
            self.log(f"Start error: {e}", 'error')

    def create_task(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def connect_to_peers(self):
        retry_count = 0
        max_retries = 10

        while len(self.connected) < self.total_peers - 1 and retry_count < max_retries:
            connection_attempts = []
            for peer_id, (host, port) in self.peers.items():
                if peer_id not in self.connected:
                    connection_attempts.append(self.try_connect_peer(host, port, peer_id))

            await asyncio.gather(*connection_attempts)

            if len(self.connected) >= self.total_peers // 2 and not self.is_active:
                self.is_active = True
                self.active_time = time.time() - self.start_time
                self.log(f"Became active with connections to peers: {sorted(list(self.connected))}")
                self.create_task(self.periodic_status_broadcast())

            if len(self.connected) == self.total_peers - 1:
                self.fully_connected_time = time.time() - self.start_time
                self.log(f"Fully connected to peers: {sorted(list(self.connected))}")
                self.all_peers_connected.set()
                break

            retry_count += 1
            await asyncio.sleep(1)

    async def try_connect_peer(self, host: str, port: int, peer_id: int):
        try:
            reader, writer = await asyncio.open_connection(host, port)
            self.connected.add(peer_id)
            self.writers[peer_id] = writer

            msg = {
                "type": "connect",
                "peer_id": self.id,
                "host": self.host,
                "port": self.port
            }
            writer.write(json.dumps(msg).encode() + b'\n')
            await writer.drain()

            self.create_task(self.handle_messages(reader, writer, peer_id))
        except (ConnectionRefusedError, OSError):
            pass

    async def handle_connection(self, reader: StreamReader, writer: StreamWriter):
        try:
            data = await reader.readline()
            message = json.loads(data.decode())

            if message["type"] == "connect":
                peer_id = message["peer_id"]
                self.connected.add(peer_id)
                self.writers[peer_id] = writer

                if len(self.connected) >= self.total_peers // 2 and not self.is_active:
                    self.is_active = True
                    self.active_time = time.time() - self.start_time
                    self.log(f"Became active with connections to peers: {sorted(list(self.connected))}")
                    self.create_task(self.periodic_status_broadcast())

                if len(self.connected) == self.total_peers - 1:
                    self.fully_connected_time = time.time() - self.start_time
                    self.log(f"Fully connected to peers: {sorted(list(self.connected))}")
                    self.all_peers_connected.set()

                self.create_task(self.handle_messages(reader, writer, peer_id))
        except Exception as e:
            self.log(f"Connection error: {e}", 'error')

    async def close_gracefully(self):
        try:
            # Cancel all tasks except the current one
            current_task = asyncio.current_task()
            tasks = [t for t in self.tasks if t is not current_task]

            if tasks:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

            # Close connections
            for peer_id, writer in list(self.writers.items()):
                await self.close_connection(peer_id, writer)

            if self.server:
                self.server.close()
                await self.server.wait_closed()

        except Exception as e:
            self.log(f"Error during graceful shutdown: {e}", 'error')

    async def handle_messages(self, reader: StreamReader, writer: StreamWriter, peer_id: int):
        try:
            while not self.terminate_received:
                data = await reader.readline()
                if not data:
                    break

                message = json.loads(data.decode())

                if message["type"] == "status" and self.is_active:
                    sender_id = message["peer_id"]
                    self.messages_received[sender_id] = True
                    self.log(f"Received status from peer {sender_id}")

                    if len(self.messages_received) >= (2 * self.total_peers) // 3:
                        await self.broadcast_terminate()

                elif message["type"] == "terminate":
                    self.log(f"Received termination message from peer {message['peer_id']}")
                    await self.handle_terminate()
                    return

        except Exception as e:
            self.log(f"Message handling error from peer {peer_id}: {e}", 'error')
        finally:
            await self.close_connection(peer_id, writer)

    async def close_connection(self, peer_id: int, writer: StreamWriter):
        try:
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()
            if peer_id in self.connected:
                self.connected.remove(peer_id)
            if peer_id in self.writers:
                del self.writers[peer_id]
        except Exception as e:
            self.log(f"Error closing connection to peer {peer_id}: {e}", 'error')

    async def periodic_status_broadcast(self):
        try:
            while not self.terminate_received and self.is_active:
                await asyncio.sleep(random.uniform(1, 3))
                await self.broadcast_status()
        except asyncio.CancelledError:
            pass

    async def broadcast_status(self):
        if not self.is_active:
            return

        message = {
            "type": "status",
            "peer_id": self.id,
            "connected_peers": sorted(list(self.connected))
        }
        await self.broadcast_message(message)
        self.log("Broadcasting status to all peers")

    async def broadcast_terminate(self):
        if not self.can_terminate:
            await self.all_peers_connected.wait()
            self.can_terminate = True

        self.log(f"Sending termination message to all peers")
        message = {
            "type": "terminate",
            "peer_id": self.id
        }
        await self.broadcast_message(message)
        await self.handle_terminate()

    async def broadcast_message(self, message: dict):
        writers_copy = self.writers.copy()
        message_str = json.dumps(message) + '\n'
        message_bytes = message_str.encode()

        for peer_id, writer in writers_copy.items():
            try:
                if not writer.is_closing():
                    writer.write(message_bytes)
                    await writer.drain()
            except Exception as e:
                self.log(f"Broadcast error to peer {peer_id}: {e}", 'error')

    async def handle_terminate(self):
        if not self.terminate_received:
            self.terminate_received = True
            self.log(f"Terminating with connections to peers: {sorted(list(self.connected))}")
            self.log(f"Time to active: {self.active_time:.2f}s")
            if self.fully_connected_time:
                self.log(f"Time to fully connected: {self.fully_connected_time:.2f}s")

            await self.close_gracefully()
            raise asyncio.CancelledError()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python peer.py <peer_id> <total_peers> <port>")
        sys.exit(1)

    peer_id = int(sys.argv[1])
    total_peers = int(sys.argv[2])
    port = int(sys.argv[3])

    peer = Peer("localhost", port, peer_id, total_peers)
    asyncio.run(peer.start())
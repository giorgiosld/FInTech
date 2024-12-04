import asyncio
import json
import random
import time
from asyncio import StreamReader, StreamWriter
from typing import Dict
import sys


class PeerNetwork:
    def __init__(self, host: str, port: int, peer_id: int, total_peers: int):
        self.host = host
        self.port = port
        self.id = peer_id
        self.total_peers = total_peers
        self.connected = set()
        self.writers: Dict[int, StreamWriter] = {}
        self.start_time = time.time()
        self.active_time = None
        self.fully_connected_time = None
        self.messages_received = set()
        self.is_terminating = False
        self.is_active = False
        self.is_fully_connected = False
        self.tasks = set()

    def log(self, msg: str):
        print(f"{time.strftime('%H:%M:%S')} - Peer {self.id} - {msg}")

    def create_task(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def start(self):
        server = await asyncio.start_server(self._handle_connection, self.host, self.port)
        print(f"Peer {self.id} listening on port {self.port}")
        await asyncio.sleep(1)
        await self._connect_peers()

        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            await self._cleanup()

    async def _connect_peers(self):
        peer_ports = {i: 8000 + i for i in range(self.total_peers) if i != self.id}
        for peer_id, port in peer_ports.items():
            if peer_id not in self.connected:
                try:
                    reader, writer = await asyncio.open_connection(self.host, port)
                    self.writers[peer_id] = writer
                    self.connected.add(peer_id)
                    writer.write(json.dumps({"type": "connect", "peer_id": self.id}).encode() + b'\n')
                    await writer.drain()
                    self._check_connections()
                    self.create_task(self._handle_messages(reader, writer, peer_id))
                except ConnectionRefusedError:
                    continue

    def _check_connections(self):
        if len(self.connected) >= self.total_peers // 2 and not self.is_active:
            self.is_active = True
            self.active_time = time.time() - self.start_time
            self.log(f"Became active with connections to peers: {sorted(list(self.connected))}")
            self.create_task(self._status_broadcast())

        if len(self.connected) == self.total_peers - 1 and not self.is_fully_connected:
            self.is_fully_connected = True
            self.fully_connected_time = time.time() - self.start_time
            self.log(f"Fully connected to peers: {sorted(list(self.connected))}")

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter):
        try:
            msg = json.loads((await reader.readline()).decode())
            if msg["type"] == "connect":
                peer_id = msg["peer_id"]
                self.writers[peer_id] = writer
                self.connected.add(peer_id)
                self._check_connections()
                await self._handle_messages(reader, writer, peer_id)
        except Exception:
            pass

    async def _handle_messages(self, reader: StreamReader, writer: StreamWriter, peer_id: int):
        try:
            while not self.is_terminating:
                data = await reader.readline()
                if not data:
                    break

                msg = json.loads(data.decode())
                if msg["type"] == "status":
                    self.log(f"Received status from peer {msg['peer_id']}")
                    self.messages_received.add(msg['peer_id'])

                    if len(self.messages_received) >= (2 * self.total_peers) // 3:
                        self.log("Sending termination message to all peers")
                        await self._terminate()
                        return

                elif msg["type"] == "terminate" and not self.is_terminating:
                    self.log(f"Received termination message from peer {msg['peer_id']}")
                    await self._terminate()
                    return
        except Exception:
            pass

    async def _status_broadcast(self):
        while not self.is_terminating:
            try:
                await asyncio.sleep(random.uniform(1, 3))
                if not self.is_terminating:
                    self.log("Broadcasting status to all peers")
                    msg = json.dumps({"type": "status", "peer_id": self.id}).encode() + b'\n'
                    await self._broadcast_message(msg)
            except Exception:
                break

    async def _broadcast_message(self, msg: bytes):
        for writer in self.writers.values():
            try:
                if not writer.is_closing():
                    writer.write(msg)
                    await writer.drain()
            except Exception:
                continue

    async def _terminate(self):
        if self.is_terminating:
            return

        self.is_terminating = True
        self.log(f"Terminating with connections to peers: {sorted(list(self.connected))}")
        if self.active_time:
            self.log(f"Time to active: {self.active_time:.2f}s")
        if self.fully_connected_time:
            self.log(f"Time to fully connected: {self.fully_connected_time:.2f}s")
        self.log("Peer disconnected")

        msg = json.dumps({"type": "terminate", "peer_id": self.id}).encode() + b'\n'
        await self._broadcast_message(msg)
        await self._cleanup()

        for task in self.tasks:
            task.cancel()

        # Give tasks time to clean up
        await asyncio.sleep(0.1)
        raise asyncio.CancelledError()

    async def _cleanup(self):
        for writer in self.writers.values():
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python peer.py <peer_id> <total_peers> <port>")
        sys.exit(1)

    peer = PeerNetwork("localhost", int(sys.argv[3]), int(sys.argv[1]), int(sys.argv[2]))
    try:
        asyncio.run(peer.start())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
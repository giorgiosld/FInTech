import asyncio
import json
import random
import time
from asyncio import StreamReader, StreamWriter
from typing import Dict, Set
import sys
from consensus_protocol import ConsensusProtocol, Transaction, ConsensusMessage


class PeerNetwork:
    def __init__(self, host: str, port: int, peer_id: int, total_peers: int):
        # Network properties
        self.host = host
        self.port = port
        self.id = peer_id
        self.total_peers = total_peers

        # Connection management
        self.connected: Set[int] = set()
        self.writers: Dict[int, StreamWriter] = {}
        self.tasks = set()

        # State management
        self.start_time = time.time()
        self.active_time = None
        self.fully_connected_time = None
        self.is_terminating = False
        self.is_active = False
        self.is_fully_connected = False

        # Message tracking
        self.messages_received = set()

        # Consensus protocol
        self.consensus = ConsensusProtocol(peer_id, total_peers)
        self.round_timer = None
        self.consensus_active = False

    def log(self, msg: str):
        """Log messages with timestamp and peer ID."""
        print(f"{time.strftime('%H:%M:%S')} - Peer {self.id} - {msg}")

    def create_task(self, coro):
        """Create and track asyncio tasks."""
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def start(self):
        """Start the peer network and consensus protocol."""
        server = await asyncio.start_server(
            self._handle_connection,
            self.host,
            self.port
        )
        self.log(f"Listening on port {self.port}")

        # Allow time for server to start
        await asyncio.sleep(1)

        # Connect to other peers
        await self._connect_peers()

        # Start consensus when network is ready
        self.create_task(self._run_consensus())

        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            await self._cleanup()

    async def _connect_peers(self):
        """Connect to other peers in the network."""
        peer_ports = {
            i: 8000 + i
            for i in range(self.total_peers)
            if i != self.id
        }

        for peer_id, port in peer_ports.items():
            if peer_id not in self.connected:
                try:
                    reader, writer = await asyncio.open_connection(
                        self.host,
                        port
                    )
                    self.writers[peer_id] = writer
                    self.connected.add(peer_id)

                    # Send connection message
                    writer.write(
                        json.dumps({
                            "type": "connect",
                            "peer_id": self.id
                        }).encode() + b'\n'
                    )
                    await writer.drain()

                    # Check network status
                    self._check_connections()

                    # Handle messages from this peer
                    self.create_task(
                        self._handle_messages(reader, writer, peer_id)
                    )
                except ConnectionRefusedError:
                    continue

    def _check_connections(self):
        """Check and update network connection status."""
        # Check for active status
        if (len(self.connected) >= self.total_peers // 2 and
                not self.is_active):
            self.is_active = True
            self.active_time = time.time() - self.start_time
            self.log(
                f"Became active with connections to peers: "
                f"{sorted(list(self.connected))}"
            )
            self.create_task(self._status_broadcast())
            self.consensus_active = True

        # Check for fully connected status
        if (len(self.connected) == self.total_peers - 1 and
                not self.is_fully_connected):
            self.is_fully_connected = True
            self.fully_connected_time = time.time() - self.start_time
            self.log(f"Fully connected to peers: {sorted(list(self.connected))}")

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter):
        """Handle incoming peer connections."""
        try:
            msg = json.loads((await reader.readline()).decode())
            if msg["type"] == "connect":
                peer_id = msg["peer_id"]
                self.writers[peer_id] = writer
                self.connected.add(peer_id)
                self._check_connections()
                await self._handle_messages(reader, writer, peer_id)
        except Exception as e:
            self.log(f"Error handling connection: {e}")

    async def _handle_messages(self, reader: StreamReader, writer: StreamWriter, peer_id: int):
        """Handle incoming messages from peers."""
        try:
            while not self.is_terminating:
                data = await reader.readline()
                if not data:
                    break

                msg = json.loads(data.decode())

                # Handle different message types
                if msg["type"] == "status":
                    await self._handle_status_message(msg)
                elif msg["type"] == "terminate":
                    await self._handle_terminate_message(msg)
                elif msg["type"] == "ADD_TX":
                    await self._handle_add_tx(msg)
                elif msg["type"] == "CONFIRM_TX":
                    await self._handle_confirm_tx(msg)
                elif msg["type"] == "COMMIT_TX":
                    await self._handle_commit_tx(msg)

        except Exception as e:
            self.log(f"Error handling messages from peer {peer_id}: {e}")
            if peer_id in self.connected:
                self.connected.remove(peer_id)
                if peer_id in self.writers:
                    del self.writers[peer_id]

    async def _handle_status_message(self, msg: dict):
        """Handle status messages."""
        self.log(f"Received status from peer {msg['peer_id']}")
        self.messages_received.add(msg['peer_id'])

        if len(self.messages_received) >= (2 * self.total_peers) // 3:
            self.log("Sending termination message to all peers")
            await self._terminate()

    async def _handle_terminate_message(self, msg: dict):
        """Handle termination messages."""
        if not self.is_terminating:
            self.log(f"Received termination message from peer {msg['peer_id']}")
            await self._terminate()

    async def _status_broadcast(self):
        """Broadcast status messages periodically."""
        while not self.is_terminating:
            try:
                await asyncio.sleep(random.uniform(1, 3))
                if not self.is_terminating:
                    self.log("Broadcasting status to all peers")
                    msg = json.dumps({
                        "type": "status",
                        "peer_id": self.id
                    }).encode() + b'\n'
                    await self._broadcast_message(msg)
            except Exception as e:
                self.log(f"Error in status broadcast: {e}")
                break

    async def _run_consensus(self):
        """Run the consensus protocol."""
        while not self.is_terminating:
            if not self.consensus_active:
                await asyncio.sleep(1)
                continue

            try:
                # Leader creates and broadcasts transaction
                if self.consensus.is_leader(self.consensus.current_round):
                    self.log(f"Attempting to create transaction for round {self.consensus.current_round}")
                    tx = self.consensus.create_transaction(
                        self.consensus.current_round
                    )
                    if tx:
                        self.log(
                            f"Successfully created and mined transaction for round "
                            f"{self.consensus.current_round}"
                        )
                        msg = ConsensusMessage.create_add_tx(tx)
                        await self._broadcast_message(
                            json.dumps(msg).encode() + b'\n'
                        )
                    else:
                        self.log(f"Failed to create transaction for round {self.consensus.current_round}")

                await asyncio.sleep(1)  # Wait before next round

            except Exception as e:
                self.log(f"Error in consensus protocol: {str(e)}")
                await asyncio.sleep(1)

    async def _handle_add_tx(self, msg: dict):
        """Handle ADD_TX consensus messages."""
        tx = Transaction.from_dict(msg['transaction'])

        if tx.round_id < self.consensus.current_round:
            return  # Ignore old transactions

        if self.consensus.verify_transaction(tx):
            self.log(
                f"Verified transaction for round {tx.round_id}, "
                f"sending confirmation"
            )
            # Store pending transaction
            self.consensus.pending_tx[tx.round_id] = tx

            # Send confirmation to leader
            confirm_msg = ConsensusMessage.create_confirm_tx(
                tx.round_id,
                self.id
            )
            leader_id = tx.round_id % self.total_peers
            if leader_id in self.writers:
                self.writers[leader_id].write(
                    json.dumps(confirm_msg).encode() + b'\n'
                )
                await self.writers[leader_id].drain()

    async def _handle_confirm_tx(self, msg: dict):
        """Handle CONFIRM_TX consensus messages."""
        round_id = msg['round_id']
        peer_id = msg['peer_id']

        if (round_id < self.consensus.current_round or
                round_id in self.consensus.committed_rounds):
            return  # Ignore old rounds

        if (self.consensus.is_leader(round_id) and
                round_id in self.consensus.pending_tx):
            if self.consensus.add_confirmation(round_id, peer_id):
                self.log(
                    f"Received enough confirmations for round {round_id}, "
                    f"committing transaction"
                )
                tx = self.consensus.pending_tx[round_id]
                commit_msg = ConsensusMessage.create_commit_tx(tx)
                await self._broadcast_message(
                    json.dumps(commit_msg).encode() + b'\n'
                )
                # Leader also commits the transaction
                self.consensus.commit_transaction(tx)

    async def _handle_commit_tx(self, msg: dict):
        """Handle COMMIT_TX consensus messages."""
        tx = Transaction.from_dict(msg['transaction'])
        if self.consensus.verify_transaction(tx):
            self.log(f"Committing transaction for round {tx.round_id}")
            if self.consensus.commit_transaction(tx):
                self.log(
                    f"Successfully committed transaction for round {tx.round_id}, chain length: {len(self.consensus.chain)}")
            else:
                self.log(f"Failed to commit transaction for round {tx.round_id}")

    async def _broadcast_message(self, msg: bytes):
        """Broadcast a message to all connected peers."""
        for writer in self.writers.values():
            try:
                if not writer.is_closing():
                    writer.write(msg)
                    await writer.drain()
            except Exception as e:
                continue

    async def _terminate(self):
        """Handle peer termination."""
        if self.is_terminating:
            return

        self.is_terminating = True
        self.log(f"Terminating with connections to peers: {sorted(list(self.connected))}")

        # Log timing information
        if self.active_time:
            self.log(f"Time to active: {self.active_time:.2f}s")
        if self.fully_connected_time:
            self.log(f"Time to fully connected: {self.fully_connected_time:.2f}s")

        # Log consensus and mining information
        stats = self.consensus.get_mining_stats()
        self.log(f"Final chain length: {stats['total_blocks']}")
        if stats['total_blocks'] > 0:
            self.log(f"Mining statistics:")
            self.log(f"  Average attempts per block: {stats['avg_attempts']:.2f}")
            self.log(f"  Min attempts: {stats['min_attempts']}")
            self.log(f"  Max attempts: {stats['max_attempts']}")
            self.log(f"  Total time: {stats['total_time']:.2f}s")

        # Send termination message
        msg = json.dumps({
            "type": "terminate",
            "peer_id": self.id
        }).encode() + b'\n'
        await self._broadcast_message(msg)

        # Cleanup
        await self._cleanup()

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Allow time for cleanup
        await asyncio.sleep(0.1)
        raise asyncio.CancelledError()

    async def _cleanup(self):
        """Clean up network connections."""
        for writer in self.writers.values():
            if not writer.is_closing():
                writer.close()
                await writer.wait_closed()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python peer.py <peer_id> <total_peers> <port>")
        sys.exit(1)

    peer = PeerNetwork(
        "localhost",
        int(sys.argv[3]),
        int(sys.argv[1]),
        int(sys.argv[2])
    )

    try:
        asyncio.run(peer.start())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
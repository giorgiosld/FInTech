import asyncio
import json
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

        # Consensus protocol
        self.consensus = ConsensusProtocol(peer_id, total_peers)
        self.consensus_active = False

    def log(self, msg: str):
        """Log messages with peer ID."""
        print(f"Peer {self.id} - {msg}")

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

                    # Handle messages from this peer
                    self.create_task(
                        self._handle_messages(reader, writer, peer_id)
                    )
                except ConnectionRefusedError:
                    continue

        # Start consensus when connected to all peers
        if len(self.connected) == self.total_peers - 1:
            self.consensus_active = True
            self.log("Connected to all peers, starting consensus")

    async def _handle_connection(self, reader: StreamReader, writer: StreamWriter):
        """Handle incoming peer connections."""
        try:
            msg = json.loads((await reader.readline()).decode())
            if msg["type"] == "connect":
                peer_id = msg["peer_id"]
                self.writers[peer_id] = writer
                self.connected.add(peer_id)
                if len(self.connected) == self.total_peers - 1:
                    self.consensus_active = True
                    self.log("Connected to all peers, starting consensus")
                await self._handle_messages(reader, writer, peer_id)
        except Exception as e:
            self.log(f"Error handling connection: {e}")

    async def _handle_messages(self, reader: StreamReader, writer: StreamWriter, peer_id: int):
        """Handle incoming messages from peers."""
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                msg = json.loads(data.decode())

                print(f"Peer {self.id} received message from peer {peer_id}: {msg}")

                # Handle consensus messages
                if msg["type"] == "ADD_TX":
                    await self._handle_add_tx(msg)
                elif msg["type"] == "CONFIRM_TX":
                    await self._handle_confirm_tx(msg)
                elif msg["type"] == "COMMIT_TX":
                    await self._handle_commit_tx(msg)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.log(f"Error handling messages from peer {peer_id}: {e}")
            if peer_id in self.connected:
                self.connected.remove(peer_id)
                if peer_id in self.writers:
                    del self.writers[peer_id]

    async def _run_consensus(self):
        """Run the consensus protocol."""
        while True:
            try:
                if not self.consensus_active:
                    await asyncio.sleep(1)
                    continue

                if self.consensus.is_leader(self.consensus.current_round):
                    tx = self.consensus.create_transaction(
                        self.consensus.current_round
                    )
                    if tx:
                        self.log(
                            f"Creating and broadcasting transaction for round {self.consensus.current_round}"
                        )
                        # Store the transaction in pending_tx before broadcasting
                        self.consensus.pending_tx[self.consensus.current_round] = tx
                        msg = ConsensusMessage.create_add_tx(tx)
                        await self._broadcast_message(
                            json.dumps(msg).encode() + b'\n'
                        )

                await asyncio.sleep(1)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.log(f"Error in consensus protocol: {e}")
                await asyncio.sleep(1)

    async def _handle_add_tx(self, msg: dict):
        """Handle ADD_TX consensus messages."""
        tx = Transaction.from_dict(msg['transaction'])
        self.log(f"Received ADD_TX for round {tx.round_id} from leader {tx.leader_id}")

        if self.consensus.verify_transaction(tx):
            self.log(f"Verified transaction for round {tx.round_id}, sending confirmation")
            # Store pending transaction
            self.consensus.pending_tx[tx.round_id] = tx

            # Send confirmation to leader
            confirm_msg = ConsensusMessage.create_confirm_tx(
                tx.round_id,
                self.id
            )
            leader_id = tx.leader_id
            if leader_id in self.writers:
                self.log(f"Sending confirmation for round {tx.round_id} to leader {leader_id}")
                self.writers[leader_id].write(
                    json.dumps(confirm_msg).encode() + b'\n'
                )
                await self.writers[leader_id].drain()
        else:
            self.log(f"Transaction verification failed for round {tx.round_id}")

    async def _handle_confirm_tx(self, msg: dict):
        """Handle CONFIRM_TX consensus messages."""
        round_id = msg['round_id']
        peer_id = msg['peer_id']

        self.log(f"Received confirmation for round {round_id} from peer {peer_id}")

        if self.consensus.is_leader(round_id):
            if self.consensus.add_confirmation(round_id, peer_id):
                self.log(f"Received enough confirmations for round {round_id}, committing and broadcasting")

                # Get the pending transaction for this round
                if round_id in self.consensus.pending_tx:
                    tx = self.consensus.pending_tx[round_id]

                    # Create and broadcast commit message
                    commit_msg = ConsensusMessage.create_commit_tx(tx)
                    self.log(f"Broadcasting commit message for round {round_id}")
                    await self._broadcast_message(
                        json.dumps(commit_msg).encode() + b'\n'
                    )

                    # Commit transaction locally
                    self.log(f"Local commit for round {round_id}")
                    self.consensus.commit_transaction(tx)
                else:
                    self.log(f"No pending transaction found for round {round_id}")

    async def _handle_commit_tx(self, msg: dict):
        """Handle COMMIT_TX consensus messages."""
        tx = Transaction.from_dict(msg['transaction'])
        self.log(f"Received COMMIT_TX for round {tx.round_id}")

        # Always commit valid transactions
        if self.consensus.verify_transaction(tx):
            self.log(f"Committing transaction for round {tx.round_id}")
            self.consensus.commit_transaction(tx)

            # Check if we should terminate
            if self.consensus.chain_length() >= self.total_peers:
                self.log("Chain length reached total peers count. Terminating...")
                stats = self.consensus.get_mining_stats()
                self.log(f"Final chain length: {stats['total_blocks']}")
                if stats['total_blocks'] > 0:
                    self.log(f"Mining statistics:")
                    self.log(f"  Average attempts per block: {stats['avg_attempts']:.2f}")
                    self.log(f"  Min attempts: {stats['min_attempts']}")
                    self.log(f"  Max attempts: {stats['max_attempts']}")
                    self.log(f"  Total time: {stats['total_time']:.2f}s")
                await self._cleanup()
                raise asyncio.CancelledError()

    async def _broadcast_message(self, msg: bytes):
        """Broadcast a message to all connected peers."""
        for writer in self.writers.values():
            try:
                if not writer.is_closing():
                    writer.write(msg)
                    await writer.drain()
            except Exception as e:
                continue

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
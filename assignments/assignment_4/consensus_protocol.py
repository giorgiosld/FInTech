from dataclasses import dataclass
from typing import Optional, Set, Dict, List
import hashlib
import string
import time
import secrets
from collections import defaultdict


@dataclass
class Transaction:
    sequence: int  # Block number in chain
    payload: str  # Random 64-char token
    nonce: int  # Mining nonce
    prev_hash: str  # Previous block's hash
    curr_hash: str  # Current block's hash
    leader_id: int  # Leader who created the block
    round_id: int  # Consensus round number
    timestamp: float = None

    def to_dict(self) -> dict:
        return {
            'sequence': self.sequence,
            'payload': self.payload,
            'nonce': self.nonce,
            'prev_hash': self.prev_hash,
            'curr_hash': self.curr_hash,
            'leader_id': self.leader_id,
            'round_id': self.round_id,
            'timestamp': self.timestamp or time.time()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        return cls(**data)

    def calculate_hash(self, nonce: int) -> str:
        """Calculate block hash with given nonce."""
        data = f"{self.sequence}{self.payload}{nonce}{self.prev_hash}{self.round_id}{self.leader_id}"
        return hashlib.sha256(data.encode()).hexdigest()


class ConsensusProtocol:
    def __init__(self, peer_id: int, total_peers: int, target_zeros: int = 4):
        self.peer_id = peer_id
        self.total_peers = total_peers
        self.current_round = 0
        self.chain: List[Transaction] = []
        self.pending_tx: Dict[int, Transaction] = {}
        self.confirmations: Dict[int, Set[int]] = defaultdict(set)
        self.required_confirmations = (total_peers // 3) + 1

        # Mining parameters
        self.target_zeros = target_zeros
        self.target_prefix = '0' * target_zeros

        # Mining statistics
        self.mining_attempts = []
        self.start_time = time.time()

        # Track committed rounds
        self.committed_rounds = set()

    def is_leader(self, round_id: int) -> bool:
        """Determine if this peer is the leader for the given round."""
        return round_id % self.total_peers == self.peer_id

    def _mine_block(self, tx: Transaction) -> tuple[int, str, int]:
        """Mine a block to find nonce that gives hash with required zeros."""
        nonce = 0
        attempts = 0
        while True:
            attempts += 1
            curr_hash = tx.calculate_hash(nonce)
            if curr_hash.startswith(self.target_prefix):
                return nonce, curr_hash, attempts
            nonce += 1
            # Optional: Add a maximum attempts limit
            if attempts > 1000000:  # 1M attempts max
                raise Exception("Mining failed: exceeded maximum attempts")

    def create_transaction(self, round_id: int) -> Optional[Transaction]:
        """Create a new transaction with mining."""
        if round_id in self.committed_rounds:
            return None

        if not self.is_leader(round_id):
            return None

        # Generate random payload (64 chars)
        payload = ''.join(secrets.choice(string.ascii_letters + string.digits)
                          for _ in range(64))

        # Get previous hash
        prev_hash = self.chain[-1].curr_hash if self.chain else '0' * 64
        sequence = len(self.chain)

        # Create transaction without hash
        tx = Transaction(
            sequence=sequence,
            payload=payload,
            nonce=0,  # Will be set during mining
            prev_hash=prev_hash,
            curr_hash='',  # Will be set during mining
            leader_id=self.peer_id,
            round_id=round_id
        )

        try:
            # Mine the block
            nonce, curr_hash, attempts = self._mine_block(tx)

            # Update mining statistics
            self.mining_attempts.append(attempts)

            # Update transaction with mining results
            tx.nonce = nonce
            tx.curr_hash = curr_hash
            tx.timestamp = time.time()

            return tx
        except Exception as e:
            print(f"Mining failed: {e}")
            return None

    def verify_transaction(self, tx: Transaction) -> bool:
        """Verify transaction integrity and proof of work."""
        if tx.round_id in self.committed_rounds:
            return False

        # Verify round and leader
        if tx.leader_id != (tx.round_id % self.total_peers):
            return False

        # Verify chain linkage
        if self.chain:
            if tx.prev_hash != self.chain[-1].curr_hash:
                return False
            if tx.sequence != len(self.chain):
                return False
        elif tx.prev_hash != '0' * 64 or tx.sequence != 0:
            return False

        # Verify proof of work
        if not tx.curr_hash.startswith(self.target_prefix):
            return False

        # Verify hash calculation
        if tx.calculate_hash(tx.nonce) != tx.curr_hash:
            return False

        return True

    def add_confirmation(self, round_id: int, peer_id: int) -> bool:
        """Add confirmation and check if we have enough."""
        if round_id in self.committed_rounds:
            return False

        self.confirmations[round_id].add(peer_id)
        return len(self.confirmations[round_id]) >= self.required_confirmations

    def commit_transaction(self, tx: Transaction) -> bool:
        """Commit a transaction to the chain."""
        if tx.round_id in self.committed_rounds:
            return False

        # Verify the transaction can be added to our chain
        if self.verify_transaction(tx):
            self.chain.append(tx)
            self.committed_rounds.add(tx.round_id)

            # Clean up pending state for this round
            if tx.round_id in self.pending_tx:
                del self.pending_tx[tx.round_id]
            if tx.round_id in self.confirmations:
                del self.confirmations[tx.round_id]

            # Move to next round
            self.current_round = max(self.current_round, tx.round_id + 1)
            return True

        return False

    def get_mining_stats(self) -> dict:
        """Get mining statistics."""
        if not self.mining_attempts:
            return {
                'total_blocks': len(self.chain),
                'avg_attempts': 0,
                'min_attempts': 0,
                'max_attempts': 0,
                'total_time': time.time() - self.start_time
            }

        return {
            'total_blocks': len(self.chain),
            'avg_attempts': sum(self.mining_attempts) / len(self.mining_attempts),
            'min_attempts': min(self.mining_attempts),
            'max_attempts': max(self.mining_attempts),
            'total_time': time.time() - self.start_time
        }


class ConsensusMessage:
    @staticmethod
    def create_add_tx(tx: Transaction) -> dict:
        return {
            'type': 'ADD_TX',
            'transaction': tx.to_dict()
        }

    @staticmethod
    def create_confirm_tx(round_id: int, peer_id: int) -> dict:
        return {
            'type': 'CONFIRM_TX',
            'round_id': round_id,
            'peer_id': peer_id
        }

    @staticmethod
    def create_commit_tx(tx: Transaction) -> dict:
        return {
            'type': 'COMMIT_TX',
            'transaction': tx.to_dict()
        }
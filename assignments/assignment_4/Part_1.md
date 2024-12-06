# Analysis of the Protocol
---

## Protocol Properties

### Safety

Safety ensures that all non-faulty nodes agree on the same value proposed by the leader. The protocol achieves this by requiring the leader to broadcast an `AddTX` message, followed by a quorum of confirmations ($\lfloor n/3 \rfloor + 1$) before committing a transaction. 

However, this threshold is insufficient in Byzantine fault scenarios, where malicious nodes could send conflicting confirmations, leading to inconsistencies. To address this, the confirmation threshold should be raised to $2n/3 + 1$, ensuring consensus among a supermajority of nodes. Incorporating Byzantine Fault Tolerance (BFT) mechanisms, such as multi-phase consensus, would further strengthen safety.

### Liveliness

Liveliness ensures the protocol makes progress and avoids deadlock. While the protocol’s round-robin leader rotation guarantees fairness, it risks stalling if a leader is faulty or unresponsive. Adding a timeout mechanism to replace inactive leaders can ensure progress. Fault detection mechanisms can further improve liveliness by allowing nodes to bypass or exclude problematic leaders.

### Termination

Termination guarantees that every non-faulty process eventually decides on a transaction. The current protocol depends on the leader collecting enough confirmations, which may fail if there are too many faulty nodes. Raising the confirmation threshold and improving inter-node communication, such as sharing confirmations across nodes, can ensure eventual termination.

---

## Suitability for Blockchain

### Decentralization

The protocol exhibits partial decentralization by allowing all nodes to act as leaders. However, reliance on a single leader per round introduces temporary centralization, making it better suited for **permissioned blockchains** where participants are known and trusted. For **permissionless blockchains**, additional measures such as randomized leader selection or leaderless consensus are needed.

### Finality

The protocol provides deterministic finality, where transactions are considered final once the leader broadcasts a `CommitTX` message. However, the low confirmation threshold risks conflicting commits. Increasing the threshold to $2n/3 + 1$ and adding consensus phases, such as prepare and commit stages, can ensure consistent and robust finality.

### Scalability and Performance

The protocol’s communication cost scales linearly with O \( n \), as each transaction requires broadcasts and confirmations. This limits scalability in large networks, as bandwidth usage and latency increase with O \( n \). Optimizations such as batching transactions, message aggregation, and parallel processing can improve throughput. However, the protocol is best suited for permissioned networks.


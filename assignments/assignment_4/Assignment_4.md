# Consensus in a p2p network

A p2p network of n nodes. Assume n is known, as well as all the members, which we enumerate from 0, ..., n - 1.

Consider a protocol where each round is given a unique identifier r.

A client accesses any node in the network, with a request.

A leader-based protocol based on round robin, such that leader l = r mod n, as follows:

Protocol: For each round:

- The leader selects the next tx in its queue and broadcasts to all an AddTX(Leader id, round id, tx, prev hash, hash(of all) )
- All receivers of AddTX, after some verification, reply with a confirmTX message
- Once leader receives floor(n/3) + 1 messages, it broadcasts a commitTX.

## Part 1
PART I: Due Thursday December 5th

Show that this protocol has the following properties:

- Safety – Non-faulty nodes agree on the same value, proposed by the leader
- Liveliness – The protocol makes progress, regardless of faults (no live- or deadlock)
- Termination – Every non-faulty process must eventually decide (??).
IF NOT, explain why, and suggest what is needed to rectify it.

Suitability for Blockchain, address each of the following:

1) Decentralization: P2P properties. Level of decentralization.
2) Finality and Confirmation: What type of finality is provided for ”committed” transactions
3) Scalability and performance: Cost as a function of n. Tx per sec. Latency

## Part 2
Part II: Due Friday December 6th 

Using your P2P network from the previous HW, implement the above.

Use it to create a chain of events, where the chain has the properties described in the Mining HW, i.e. each having a random Payload, with a chain structure such that the current chain entry contains the hash of the previous entry.

For simplicity rather than implementing proper client(s), have the leader of the round generate the next event.
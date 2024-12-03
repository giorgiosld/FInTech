# P2P Network
Create A peer-to-peer network of size N

On boot, each node, connects to each peer in the network (and maintains the connections)

Once connection is established to >N/2 nodes, at random intervals
transmits to all nodes connected the connected status of all peers. 
First Peer to receive 2/3N  messages from all N peers, broadcasts a Terminate

Nodes receiving a Terminate – output their connected status and terminate.

Report on bootstrapping, time until active, time until completely connected.

Demonstrate in class

If implemented on a single system, each node should be a separate process
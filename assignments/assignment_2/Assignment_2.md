## Goal I: Working with secrets module and hash in Python

## Goal II: Elementary mining

Generate a ”chain” of 1000 blocks as [ i = Sequence #, Payload, nonce, p, h], where:

Payload – is a random token of size 64 drawn from letters and digits
p(i) : is h(i - 1) with p(0) = 0.
h : is the SHA256 hash of the current block [excluding itself] with k leading zeros
Return the aggregate, ave, max and min number of SHA256 calls needed for each block, and the length of the chain.

Run experiment for k == 4, 6, 8 still limited to 90 minutes. If timer expires, report how long the chain is.

[Also, play with less than 1000 blocks when debugging]
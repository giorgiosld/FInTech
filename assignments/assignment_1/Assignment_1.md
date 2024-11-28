# Programming with large numbers

Goal I: Getting started with programming in Python

Goal II: Time complexity for real ::: Playing with large numbers

## Part I: Programming in Python

Set up Python on your computer and a development environment: Git/Github, editor, whatever else is needed, and do a simple program to demonstrate your setup.

## Part II: Playing with large integers

Python supports integers of arbitrary length, beyond what your machine can (64 bits)

Familiarize yourself with large number support in Python



### A) Basic operations

Let n, k be integers, and ⊕ be an operation in {+, 1, *, / } on integers in Zn

Repeat 100 times:

Generate a set of k random numbers in Zn
Apply ⊕ on the set for each operation {+, 1, *, / }.
Report on the total elapsed time for the run, and break-down into individual operations as a fraction of the total time for k = 10000

Repeat the exercise, with ⊕ as the exponentiation, with the initial value of 1.

Do the above with n = 2a - 1, where a is in { 64, 128, 256, 1024, 4096 }

### B) Primality testing using the Miller Rabin test

Generate a stream of random numbers in Zn

Test each number in the set for primality, using the Miller Rabin test, printing out each prime
Break when the FIVE primes have been found
Report total time elapsed

Repeat the above with n = 2a-1, where a is in { 64, 128, 256, 1024, 4096 }
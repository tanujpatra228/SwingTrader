"""Pure numeric functions.

LAW (engineering-standards.md §0.1): everything here takes a DataFrame (or plain
numbers) and returns a DataFrame (or plain numbers). No database, no network, no
clock, no config reads. This is what lets the numbers be tested against handmade
cases with a known answer instead of a live system.
"""

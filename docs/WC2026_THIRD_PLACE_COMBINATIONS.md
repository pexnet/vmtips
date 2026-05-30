# FIFA World Cup 2026 — Official Third-Place Combination Table

This document explains how VMTips applies the FIFA Regulations Annex C table for assigning the eight advancing third-place teams to Round of 32 slots.

The full table is stored in `backend/third_place_table.py`. The Wikipedia template mirror was used as the extraction source for the code table.

## Format

Each combination defines:
- `advancing_groups`: set of 8 groups (A-L) whose third-place teams advance
- `assignments`: mapping from match number to the specific third-place group assigned to that slot

The 8 group winners that play a third-place team are fixed to these matches/sides:
- 1A -> match 79, away side
- 1B -> match 85, away side
- 1D -> match 81, away side
- 1E -> match 74, away side
- 1G -> match 82, away side
- 1I -> match 77, away side
- 1K -> match 87, away side
- 1L -> match 80, away side

## Combination Table

The full 495-combination table is stored in `backend/third_place_table.py`.
It maps every possible set of 8 advancing third-place groups to the exact R32 matchup assignments from FIFA Annex C.

The bracket engine uses that static lookup directly; no generated or ranking-order-based assignment is used at runtime.

## Candidate Sets Reference

These are the candidate sets:
- match 79 away (1A): groups C, E, F, H, I
- match 85 away (1B): groups E, F, G, I, J
- match 81 away (1D): groups B, E, F, I, J
- match 74 away (1E): groups A, B, C, D, F
- match 82 away (1G): groups A, E, H, I, J
- match 77 away (1I): groups C, D, F, G, H
- match 87 away (1K): groups D, E, I, J, L
- match 80 away (1L): groups E, H, I, J, K

## Runtime Flow

When actual group-stage results are known:
1. Compute the 12 third-place teams and rank them.
2. Determine which 8 groups have advancing third-place teams.
3. Look up the combination by those 8 groups in this table.
4. Assign each third-place team to its exact match/side per the table.
5. Admin API can then populate the actual R32 matches with real team IDs.

## Sources

- FIFA Regulations Annex C: third-place assignment table.
- https://en.wikipedia.org/wiki/Template:2026_FIFA_World_Cup_third-place_table

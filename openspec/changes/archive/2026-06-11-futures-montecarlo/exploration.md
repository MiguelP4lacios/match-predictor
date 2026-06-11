# Exploration: futures-montecarlo

**Change:** futures-montecarlo  
**Date:** 2026-06-11  
**Source:** Official FIFA World Cup 26 Competition Regulations PDF (Annex C), Wikipedia 2026 WC Knockout Stage, codebase inspection + DB queries.

---

## Current State

The system has a fully scaffolded group-stage engine: 12 groups (A–L), 48 teams seeded, 72 GROUP fixtures SCHEDULED (group stage started 2026-06-11). There is NO Monte Carlo module, NO knockout fixture rows in the DB, and NO futures odds capture. The prediction table supports `OUTRIGHT_WINNER` and `GROUP_ADVANCE` market types via the `MarketType` enum but nothing writes to them for futures yet.

---

## 1. 2026 WC Format — Exact Structure

### Group Stage
- 48 teams, 12 groups of 4 (A–L), 6 matches per group = **72 total group matches**
- Top 2 per group (24 teams) + **8 best 3rd-placed** = 32 advance to knockout

### Third-Place Ranking Criteria (cross-group, FIFA official order)
1. Points  
2. Goal difference  
3. Goals scored  
4. Fair-play (cards) — **not currently tracked in DB**; omit for Monte Carlo, document as gap  
5. FIFA ranking — use Elo as proxy since no FIFA ranking table in DB

### Knockout Structure
```
R32 (16 matches) → R16 (8 matches) → QF (4) → SF (2) → [3rd place + Final]
```

### Round of 32 — Exact Pairings (from FIFA regulations + Wikipedia)

| Match | Pairing |
|-------|---------|
| M73 | 2A vs 2B |
| M74 | 1E vs Best3rd(A/B/C/D/F) |
| M75 | 1F vs 2C |
| M76 | 1C vs 2F |
| M77 | 1I vs Best3rd(C/D/F/G/H) |
| M78 | 2E vs 2I |
| M79 | 1A vs Best3rd(C/E/F/H/I) |
| M80 | 1L vs Best3rd(E/H/I/J/K) |
| M81 | 1D vs Best3rd(B/E/F/I/J) |
| M82 | 1G vs Best3rd(A/E/H/I/J) |
| M83 | 2K vs 2L |
| M84 | 1H vs 2J |
| M85 | 1B vs Best3rd(E/F/G/I/J) |
| M86 | 1J vs 2H |
| M87 | 1K vs Best3rd(D/E/I/J/L) |
| M88 | 2D vs 2G |

### R16 Advancement (from FIFA regulations Annex, Article 12.7)

| Match | Pairing |
|-------|---------|
| M89 | W74 vs W77 |
| M90 | W73 vs W75 |
| M91 | W76 vs W78 |
| M92 | W79 vs W80 |
| M93 | W83 vs W84 |
| M94 | W81 vs W82 |
| M95 | W86 vs W88 |
| M96 | W85 vs W87 |

### Quarterfinals
| Match | Pairing |
|-------|---------|
| M97 | W89 vs W90 |
| M98 | W93 vs W94 |
| M99 | W91 vs W92 |
| M100 | W95 vs W96 |

### Semifinals
| Match | Pairing |
|-------|---------|
| M101 | W97 vs W98 |
| M102 | W99 vs W100 |

3rd place: L101 vs L102  
Final: W101 vs W102

---

## 2. Third-Place Slot Assignment — Annex C (COMPLETE, 495 rows)

Source: Official FIFA World Cup 26 Competition Regulations PDF, Annex C (pages 80–97), fully extracted.

**Table header:** `Option | 1A | 1B | 1D | 1E | 1G | 1I | 1K | 1L`

The columns represent the Group Winners whose R32 match receives a 3rd-placed opponent:
- `1A` → M79 (1A vs Best3rd)
- `1B` → M85 (1B vs Best3rd)
- `1D` → M81 (1D vs Best3rd)
- `1E` → M74 (1E vs Best3rd)
- `1G` → M82 (1G vs Best3rd)
- `1I` → M77 (1I vs Best3rd)
- `1K` → M87 (1K vs Best3rd)
- `1L` → M80 (1L vs Best3rd)

Each row's 8 cell values (e.g., `3E, 3J, 3I, 3F, 3H, 3G, 3L, 3K`) tell you which 3rd-placed group gets assigned to each slot. The qualifying groups for that option = the set of groups appearing in the cells.

**Lookup algorithm for Monte Carlo:**
1. After simulating group stage, determine the 8 best 3rd-placed teams → record their 8 group letters
2. Find the Annex C row where the union of cell values = that set of 8 groups
3. Apply the cell assignments

**Implementation:** Embed as a Python constant `ANNEX_C: dict[frozenset[str], dict[str, str]]` where key = frozenset of qualifying group letters, value = `{"1A": "E", "1B": "J", ...}`.

Complete Annex C (all 495 options):

```
Opt | 1A | 1B | 1D | 1E | 1G | 1I | 1K | 1L    (qualifying groups)
  1 | 3E | 3J | 3I | 3F | 3H | 3G | 3L | 3K    {E,F,G,H,I,J,K,L}
  2 | 3H | 3G | 3I | 3D | 3J | 3F | 3L | 3K    {D,F,G,H,I,J,K,L}
  3 | 3E | 3J | 3I | 3D | 3H | 3G | 3L | 3K    {D,E,G,H,I,J,K,L}
  4 | 3E | 3J | 3I | 3D | 3H | 3F | 3L | 3K    {D,E,F,H,I,J,K,L}
  5 | 3E | 3G | 3I | 3D | 3J | 3F | 3L | 3K    {D,E,F,G,I,J,K,L}
  6 | 3E | 3G | 3J | 3D | 3H | 3F | 3L | 3K    {D,E,F,G,H,J,K,L}
  7 | 3E | 3G | 3I | 3D | 3H | 3F | 3L | 3K    {D,E,F,G,H,I,K,L}
  8 | 3E | 3G | 3J | 3D | 3H | 3F | 3L | 3I    {D,E,F,G,H,I,J,L}
  9 | 3E | 3G | 3J | 3D | 3H | 3F | 3I | 3K    {D,E,F,G,H,I,J,K}
 10 | 3H | 3G | 3I | 3C | 3J | 3F | 3L | 3K    {C,F,G,H,I,J,K,L}
 11 | 3E | 3J | 3I | 3C | 3H | 3G | 3L | 3K    {C,E,G,H,I,J,K,L}
 12 | 3E | 3J | 3I | 3C | 3H | 3F | 3L | 3K    {C,E,F,H,I,J,K,L}
 13 | 3E | 3G | 3I | 3C | 3J | 3F | 3L | 3K    {C,E,F,G,I,J,K,L}
 14 | 3E | 3G | 3J | 3C | 3H | 3F | 3L | 3K    {C,E,F,G,H,J,K,L}
 15 | 3E | 3G | 3I | 3C | 3H | 3F | 3L | 3K    {C,E,F,G,H,I,K,L}
 16 | 3E | 3G | 3J | 3C | 3H | 3F | 3L | 3I    {C,E,F,G,H,I,J,L}
 17 | 3E | 3G | 3J | 3C | 3H | 3F | 3I | 3K    {C,E,F,G,H,I,J,K}
 18 | 3H | 3G | 3I | 3C | 3J | 3D | 3L | 3K    {C,D,G,H,I,J,K,L}
 19 | 3C | 3J | 3I | 3D | 3H | 3F | 3L | 3K    {C,D,F,H,I,J,K,L}
 20 | 3C | 3G | 3I | 3D | 3J | 3F | 3L | 3K    {C,D,F,G,I,J,K,L}
 21 | 3C | 3G | 3J | 3D | 3H | 3F | 3L | 3K    {C,D,F,G,H,J,K,L}
 22 | 3C | 3G | 3I | 3D | 3H | 3F | 3L | 3K    {C,D,F,G,H,I,K,L}
 23 | 3C | 3G | 3J | 3D | 3H | 3F | 3L | 3I    {C,D,F,G,H,I,J,L}
 24 | 3C | 3G | 3J | 3D | 3H | 3F | 3I | 3K    {C,D,F,G,H,I,J,K}
 25 | 3E | 3J | 3I | 3C | 3H | 3D | 3L | 3K    {C,D,E,H,I,J,K,L}
 26 | 3E | 3G | 3I | 3C | 3J | 3D | 3L | 3K    {C,D,E,G,I,J,K,L}
 27 | 3E | 3G | 3J | 3C | 3H | 3D | 3L | 3K    {C,D,E,G,H,J,K,L}
 28 | 3E | 3G | 3I | 3C | 3H | 3D | 3L | 3K    {C,D,E,G,H,I,K,L}
 29 | 3E | 3G | 3J | 3C | 3H | 3D | 3L | 3I    {C,D,E,G,H,I,J,L}
 30 | 3E | 3G | 3J | 3C | 3H | 3D | 3I | 3K    {C,D,E,G,H,I,J,K}
 31 | 3C | 3J | 3E | 3D | 3I | 3F | 3L | 3K    {C,D,E,F,I,J,K,L}
 32 | 3C | 3J | 3E | 3D | 3H | 3F | 3L | 3K    {C,D,E,F,H,J,K,L}
 33 | 3C | 3E | 3I | 3D | 3H | 3F | 3L | 3K    {C,D,E,F,H,I,K,L}
 34 | 3C | 3J | 3E | 3D | 3H | 3F | 3L | 3I    {C,D,E,F,H,I,J,L}
 35 | 3C | 3J | 3E | 3D | 3H | 3F | 3I | 3K    {C,D,E,F,H,I,J,K}
 36 | 3C | 3G | 3E | 3D | 3J | 3F | 3L | 3K    {C,D,E,F,G,J,K,L}
 37 | 3C | 3G | 3E | 3D | 3I | 3F | 3L | 3K    {C,D,E,F,G,I,K,L}
 38 | 3C | 3G | 3E | 3D | 3J | 3F | 3L | 3I    {C,D,E,F,G,I,J,L}
 39 | 3C | 3G | 3E | 3D | 3J | 3F | 3I | 3K    {C,D,E,F,G,I,J,K}
 40 | 3C | 3G | 3E | 3D | 3H | 3F | 3L | 3K    {C,D,E,F,G,H,K,L}
 41 | 3C | 3G | 3J | 3D | 3H | 3F | 3L | 3E    {C,D,E,F,G,H,J,L}
 42 | 3C | 3G | 3J | 3D | 3H | 3F | 3E | 3K    {C,D,E,F,G,H,J,K}
 43 | 3C | 3G | 3E | 3D | 3H | 3F | 3L | 3I    {C,D,E,F,G,H,I,L}
 44 | 3C | 3G | 3E | 3D | 3H | 3F | 3I | 3K    {C,D,E,F,G,H,I,K}
 45 | 3C | 3G | 3J | 3D | 3H | 3F | 3E | 3I    {C,D,E,F,G,H,I,J}
 46 | 3H | 3J | 3B | 3F | 3I | 3G | 3L | 3K    {B,F,G,H,I,J,K,L}
 47 | 3E | 3J | 3I | 3B | 3H | 3G | 3L | 3K    {B,E,G,H,I,J,K,L}
 48 | 3E | 3J | 3B | 3F | 3I | 3H | 3L | 3K    {B,E,F,H,I,J,K,L} (note: typo risk; 1B col=3J,1D=3B)
 49 | 3E | 3J | 3B | 3F | 3I | 3G | 3L | 3K    {B,E,F,G,I,J,K,L}
 50 | 3E | 3J | 3B | 3F | 3H | 3G | 3L | 3K    {B,E,F,G,H,J,K,L}
 51 | 3E | 3G | 3B | 3F | 3I | 3H | 3L | 3K    {B,E,F,G,H,I,K,L}
 52 | 3E | 3J | 3B | 3F | 3H | 3G | 3L | 3I    {B,E,F,G,H,I,J,L}
 53 | 3E | 3J | 3B | 3F | 3H | 3G | 3I | 3K    {B,E,F,G,H,I,J,K}
 54 | 3H | 3J | 3B | 3D | 3I | 3G | 3L | 3K    {B,D,G,H,I,J,K,L}
 55 | 3H | 3J | 3B | 3D | 3I | 3F | 3L | 3K    {B,D,F,H,I,J,K,L}
 56 | 3I | 3G | 3B | 3D | 3J | 3F | 3L | 3K    {B,D,F,G,I,J,K,L}
 57 | 3H | 3G | 3B | 3D | 3J | 3F | 3L | 3K    {B,D,F,G,H,J,K,L}
 58 | 3H | 3G | 3B | 3D | 3I | 3F | 3L | 3K    {B,D,F,G,H,I,K,L}
 59 | 3H | 3G | 3B | 3D | 3J | 3F | 3L | 3I    {B,D,F,G,H,I,J,L}
 60 | 3H | 3G | 3B | 3D | 3J | 3F | 3I | 3K    {B,D,F,G,H,I,J,K}
 61 | 3E | 3J | 3B | 3D | 3I | 3H | 3L | 3K    {B,D,E,H,I,J,K,L}
 62 | 3E | 3J | 3B | 3D | 3I | 3G | 3L | 3K    {B,D,E,G,I,J,K,L}
 63 | 3E | 3J | 3B | 3D | 3H | 3G | 3L | 3K    {B,D,E,G,H,J,K,L}
 64 | 3E | 3G | 3B | 3D | 3I | 3H | 3L | 3K    {B,D,E,G,H,I,K,L}
 65 | 3E | 3J | 3B | 3D | 3H | 3G | 3L | 3I    {B,D,E,G,H,I,J,L}
 66 | 3E | 3J | 3B | 3D | 3H | 3G | 3I | 3K    {B,D,E,G,H,I,J,K}
 67 | 3E | 3J | 3B | 3D | 3I | 3F | 3L | 3K    {B,D,E,F,I,J,K,L}
 68 | 3E | 3J | 3B | 3D | 3H | 3F | 3L | 3K    {B,D,E,F,H,J,K,L}
 69 | 3E | 3I | 3B | 3D | 3H | 3F | 3L | 3K    {B,D,E,F,H,I,K,L}
 70 | 3E | 3J | 3B | 3D | 3H | 3F | 3L | 3I    {B,D,E,F,H,I,J,L}
 71 | 3E | 3J | 3B | 3D | 3H | 3F | 3I | 3K    {B,D,E,F,H,I,J,K}
 72 | 3E | 3G | 3B | 3D | 3J | 3F | 3L | 3K    {B,D,E,F,G,J,K,L}
 73 | 3E | 3G | 3B | 3D | 3I | 3F | 3L | 3K    {B,D,E,F,G,I,K,L}
 74 | 3E | 3G | 3B | 3D | 3J | 3F | 3L | 3I    {B,D,E,F,G,I,J,L}
 75 | 3E | 3G | 3B | 3D | 3J | 3F | 3I | 3K    {B,D,E,F,G,I,J,K}
 76 | 3E | 3G | 3B | 3D | 3H | 3F | 3L | 3K    {B,D,E,F,G,H,K,L}
 77 | 3H | 3G | 3B | 3D | 3J | 3F | 3L | 3E    {B,D,E,F,G,H,J,L}
 78 | 3H | 3G | 3B | 3D | 3J | 3F | 3E | 3K    {B,D,E,F,G,H,J,K}
 79 | 3E | 3G | 3B | 3D | 3H | 3F | 3L | 3I    {B,D,E,F,G,H,I,L}
 80 | 3E | 3G | 3B | 3D | 3H | 3F | 3I | 3K    {B,D,E,F,G,H,I,K}
 81 | 3H | 3G | 3B | 3D | 3J | 3F | 3E | 3I    {B,D,E,F,G,H,I,J}
 82 | 3H | 3J | 3B | 3C | 3I | 3G | 3L | 3K    {B,C,G,H,I,J,K,L}
 83 | 3H | 3J | 3B | 3C | 3I | 3F | 3L | 3K    {B,C,F,H,I,J,K,L}
 84 | 3I | 3G | 3B | 3C | 3J | 3F | 3L | 3K    {B,C,F,G,I,J,K,L}
 85 | 3H | 3G | 3B | 3C | 3J | 3F | 3L | 3K    {B,C,F,G,H,J,K,L}
 86 | 3H | 3G | 3B | 3C | 3I | 3F | 3L | 3K    {B,C,F,G,H,I,K,L}
 87 | 3H | 3G | 3B | 3C | 3J | 3F | 3L | 3I    {B,C,F,G,H,I,J,L}
 88 | 3H | 3G | 3B | 3C | 3J | 3F | 3I | 3K    {B,C,F,G,H,I,J,K}
 89 | 3E | 3J | 3B | 3C | 3I | 3H | 3L | 3K    {B,C,E,H,I,J,K,L}
 90 | 3E | 3J | 3B | 3C | 3I | 3G | 3L | 3K    {B,C,E,G,I,J,K,L}
 91 | 3E | 3J | 3B | 3C | 3H | 3G | 3L | 3K    {B,C,E,G,H,J,K,L}
 92 | 3E | 3G | 3B | 3C | 3I | 3H | 3L | 3K    {B,C,E,G,H,I,K,L}
 93 | 3E | 3J | 3B | 3C | 3H | 3G | 3L | 3I    {B,C,E,G,H,I,J,L}
 94 | 3E | 3J | 3B | 3C | 3H | 3G | 3I | 3K    {B,C,E,G,H,I,J,K}
 95 | 3E | 3J | 3B | 3C | 3I | 3F | 3L | 3K    {B,C,E,F,I,J,K,L}
 96 | 3E | 3J | 3B | 3C | 3H | 3F | 3L | 3K    {B,C,E,F,H,J,K,L}
 97 | 3E | 3I | 3B | 3C | 3H | 3F | 3L | 3K    {B,C,E,F,H,I,K,L}
 98 | 3E | 3J | 3B | 3C | 3H | 3F | 3L | 3I    {B,C,E,F,H,I,J,L}
 99 | 3E | 3J | 3B | 3C | 3H | 3F | 3I | 3K    {B,C,E,F,H,I,J,K}
100 | 3E | 3G | 3B | 3C | 3J | 3F | 3L | 3K    {B,C,E,F,G,J,K,L}
101 | 3E | 3G | 3B | 3C | 3I | 3F | 3L | 3K    {B,C,E,F,G,I,K,L}
102 | 3E | 3G | 3B | 3C | 3J | 3F | 3L | 3I    {B,C,E,F,G,I,J,L}
103 | 3E | 3G | 3B | 3C | 3J | 3F | 3I | 3K    {B,C,E,F,G,I,J,K}
104 | 3E | 3G | 3B | 3C | 3H | 3F | 3L | 3K    {B,C,E,F,G,H,K,L}
105 | 3H | 3G | 3B | 3C | 3J | 3F | 3L | 3E    {B,C,E,F,G,H,J,L}
106 | 3H | 3G | 3B | 3C | 3J | 3F | 3E | 3K    {B,C,E,F,G,H,J,K}
107 | 3E | 3G | 3B | 3C | 3H | 3F | 3L | 3I    {B,C,E,F,G,H,I,L}
108 | 3E | 3G | 3B | 3C | 3H | 3F | 3I | 3K    {B,C,E,F,G,H,I,K}
109 | 3H | 3G | 3B | 3C | 3J | 3F | 3E | 3I    {B,C,E,F,G,H,I,J}
110 | 3H | 3J | 3B | 3C | 3I | 3D | 3L | 3K    {B,C,D,H,I,J,K,L}
111 | 3I | 3G | 3B | 3C | 3J | 3D | 3L | 3K    {B,C,D,G,I,J,K,L}
112 | 3H | 3G | 3B | 3C | 3J | 3D | 3L | 3K    {B,C,D,G,H,J,K,L}
113 | 3H | 3G | 3B | 3C | 3I | 3D | 3L | 3K    {B,C,D,G,H,I,K,L}
114 | 3H | 3G | 3B | 3C | 3J | 3D | 3L | 3I    {B,C,D,G,H,I,J,L}
115 | 3H | 3G | 3B | 3C | 3J | 3D | 3I | 3K    {B,C,D,G,H,I,J,K}
116 | 3C | 3J | 3B | 3D | 3I | 3F | 3L | 3K    {B,C,D,F,I,J,K,L}
117 | 3C | 3J | 3B | 3D | 3H | 3F | 3L | 3K    {B,C,D,F,H,J,K,L}
118 | 3C | 3I | 3B | 3D | 3H | 3F | 3L | 3K    {B,C,D,F,H,I,K,L}
119 | 3C | 3J | 3B | 3D | 3H | 3F | 3L | 3I    {B,C,D,F,H,I,J,L}
120 | 3C | 3J | 3B | 3D | 3H | 3F | 3I | 3K    {B,C,D,F,H,I,J,K}
121 | 3C | 3G | 3B | 3D | 3J | 3F | 3L | 3K    {B,C,D,F,G,J,K,L}
122 | 3C | 3G | 3B | 3D | 3I | 3F | 3L | 3K    {B,C,D,F,G,I,K,L}
123 | 3C | 3G | 3B | 3D | 3J | 3F | 3L | 3I    {B,C,D,F,G,I,J,L}
124 | 3C | 3G | 3B | 3D | 3J | 3F | 3I | 3K    {B,C,D,F,G,I,J,K}
125 | 3C | 3G | 3B | 3D | 3H | 3F | 3L | 3K    {B,C,D,F,G,H,K,L}
126 | 3C | 3G | 3B | 3D | 3H | 3F | 3L | 3J    {B,C,D,F,G,H,J,L}
127 | 3H | 3G | 3B | 3C | 3J | 3F | 3D | 3K    {B,C,D,F,G,H,J,K}
128 | 3C | 3G | 3B | 3D | 3H | 3F | 3L | 3I    {B,C,D,F,G,H,I,L}
129 | 3C | 3G | 3B | 3D | 3H | 3F | 3I | 3K    {B,C,D,F,G,H,I,K}
130 | 3H | 3G | 3B | 3C | 3J | 3F | 3D | 3I    {B,C,D,F,G,H,I,J}
131 | 3E | 3J | 3B | 3C | 3I | 3D | 3L | 3K    {B,C,D,E,I,J,K,L}
132 | 3E | 3J | 3B | 3C | 3H | 3D | 3L | 3K    {B,C,D,E,H,J,K,L}
133 | 3E | 3I | 3B | 3C | 3H | 3D | 3L | 3K    {B,C,D,E,H,I,K,L}
134 | 3E | 3J | 3B | 3C | 3H | 3D | 3L | 3I    {B,C,D,E,H,I,J,L}
135 | 3E | 3J | 3B | 3C | 3H | 3D | 3I | 3K    {B,C,D,E,H,I,J,K}
136 | 3E | 3G | 3B | 3C | 3J | 3D | 3L | 3K    {B,C,D,E,G,J,K,L}
137 | 3E | 3G | 3B | 3C | 3I | 3D | 3L | 3K    {B,C,D,E,G,I,K,L}
138 | 3E | 3G | 3B | 3C | 3J | 3D | 3L | 3I    {B,C,D,E,G,I,J,L}
139 | 3E | 3G | 3B | 3C | 3J | 3D | 3I | 3K    {B,C,D,E,G,I,J,K}
140 | 3E | 3G | 3B | 3C | 3H | 3D | 3L | 3K    {B,C,D,E,G,H,K,L}
141 | 3H | 3G | 3B | 3C | 3J | 3D | 3L | 3E    {B,C,D,E,G,H,J,L}
142 | 3H | 3G | 3B | 3C | 3J | 3D | 3E | 3K    {B,C,D,E,G,H,J,K}
143 | 3E | 3G | 3B | 3C | 3H | 3D | 3L | 3I    {B,C,D,E,G,H,I,L}
144 | 3E | 3G | 3B | 3C | 3H | 3D | 3I | 3K    {B,C,D,E,G,H,I,K}
145 | 3H | 3G | 3B | 3C | 3J | 3D | 3E | 3I    {B,C,D,E,G,H,I,J}
146 | 3C | 3J | 3B | 3D | 3E | 3F | 3L | 3K    {B,C,D,E,F,J,K,L}
147 | 3C | 3E | 3B | 3D | 3I | 3F | 3L | 3K    {B,C,D,E,F,I,K,L}
148 | 3C | 3J | 3B | 3D | 3E | 3F | 3L | 3I    {B,C,D,E,F,I,J,L}
149 | 3C | 3J | 3B | 3D | 3E | 3F | 3I | 3K    {B,C,D,E,F,I,J,K}
150 | 3C | 3E | 3B | 3D | 3H | 3F | 3L | 3K    {B,C,D,E,F,H,K,L}
151 | 3C | 3J | 3B | 3D | 3H | 3F | 3L | 3E    {B,C,D,E,F,H,J,L}
152 | 3C | 3J | 3B | 3D | 3H | 3F | 3E | 3K    {B,C,D,E,F,H,J,K}
153 | 3C | 3E | 3B | 3D | 3H | 3F | 3L | 3I    {B,C,D,E,F,H,I,L}
154 | 3C | 3E | 3B | 3D | 3H | 3F | 3I | 3K    {B,C,D,E,F,H,I,K}
155 | 3C | 3J | 3B | 3D | 3H | 3F | 3E | 3I    {B,C,D,E,F,H,I,J}
156 | 3C | 3G | 3B | 3D | 3E | 3F | 3L | 3K    {B,C,D,E,F,G,K,L}
157 | 3C | 3G | 3B | 3D | 3J | 3F | 3L | 3E    {B,C,D,E,F,G,J,L}
158 | 3C | 3G | 3B | 3D | 3J | 3F | 3E | 3K    {B,C,D,E,F,G,J,K}
159 | 3C | 3G | 3B | 3D | 3E | 3F | 3L | 3I    {B,C,D,E,F,G,I,L}
160 | 3C | 3G | 3B | 3D | 3E | 3F | 3I | 3K    {B,C,D,E,F,G,I,K}
161 | 3C | 3G | 3B | 3D | 3J | 3F | 3E | 3I    {B,C,D,E,F,G,I,J}
162 | 3C | 3G | 3B | 3D | 3H | 3F | 3L | 3E    {B,C,D,E,F,G,H,L}
163 | 3C | 3G | 3B | 3D | 3H | 3F | 3E | 3K    {B,C,D,E,F,G,H,K}
164 | 3H | 3G | 3B | 3C | 3J | 3F | 3D | 3E    {B,C,D,E,F,G,H,J}
165 | 3C | 3G | 3B | 3D | 3H | 3F | 3E | 3I    {B,C,D,E,F,G,H,I}
166 | 3H | 3J | 3I | 3F | 3A | 3G | 3L | 3K    {A,F,G,H,I,J,K,L}
167 | 3E | 3J | 3I | 3A | 3H | 3G | 3L | 3K    {A,E,G,H,I,J,K,L}
168 | 3E | 3J | 3I | 3F | 3A | 3H | 3L | 3K    {A,E,F,H,I,J,K,L}
169 | 3E | 3J | 3I | 3F | 3A | 3G | 3L | 3K    {A,E,F,G,I,J,K,L}
170 | 3E | 3G | 3J | 3F | 3A | 3H | 3L | 3K    {A,E,F,G,H,J,K,L}
171 | 3E | 3G | 3I | 3F | 3A | 3H | 3L | 3K    {A,E,F,G,H,I,K,L}
172 | 3E | 3G | 3J | 3F | 3A | 3H | 3L | 3I    {A,E,F,G,H,I,J,L}
173 | 3E | 3G | 3J | 3F | 3A | 3H | 3I | 3K    {A,E,F,G,H,I,J,K}
174 | 3H | 3J | 3I | 3D | 3A | 3G | 3L | 3K    {A,D,G,H,I,J,K,L}
175 | 3H | 3J | 3I | 3D | 3A | 3F | 3L | 3K    {A,D,F,H,I,J,K,L}
176 | 3I | 3G | 3J | 3D | 3A | 3F | 3L | 3K    {A,D,F,G,I,J,K,L}
177 | 3H | 3G | 3J | 3D | 3A | 3F | 3L | 3K    {A,D,F,G,H,J,K,L}
178 | 3H | 3G | 3I | 3D | 3A | 3F | 3L | 3K    {A,D,F,G,H,I,K,L}
179 | 3H | 3G | 3J | 3D | 3A | 3F | 3L | 3I    {A,D,F,G,H,I,J,L}
180 | 3H | 3G | 3J | 3D | 3A | 3F | 3I | 3K    {A,D,F,G,H,I,J,K}
181 | 3E | 3J | 3I | 3D | 3A | 3H | 3L | 3K    {A,D,E,H,I,J,K,L}
182 | 3E | 3J | 3I | 3D | 3A | 3G | 3L | 3K    {A,D,E,G,I,J,K,L}
183 | 3E | 3G | 3J | 3D | 3A | 3H | 3L | 3K    {A,D,E,G,H,J,K,L}
184 | 3E | 3G | 3I | 3D | 3A | 3H | 3L | 3K    {A,D,E,G,H,I,K,L}
185 | 3E | 3G | 3J | 3D | 3A | 3H | 3L | 3I    {A,D,E,G,H,I,J,L}
186 | 3E | 3G | 3J | 3D | 3A | 3H | 3I | 3K    {A,D,E,G,H,I,J,K}
187 | 3E | 3J | 3I | 3D | 3A | 3F | 3L | 3K    {A,D,E,F,I,J,K,L}
188 | 3H | 3J | 3E | 3D | 3A | 3F | 3L | 3K    {A,D,E,F,H,J,K,L}
189 | 3H | 3E | 3I | 3D | 3A | 3F | 3L | 3K    {A,D,E,F,H,I,K,L}
190 | 3H | 3J | 3E | 3D | 3A | 3F | 3L | 3I    {A,D,E,F,H,I,J,L}
191 | 3H | 3J | 3E | 3D | 3A | 3F | 3I | 3K    {A,D,E,F,H,I,J,K}
192 | 3E | 3G | 3J | 3D | 3A | 3F | 3L | 3K    {A,D,E,F,G,J,K,L}
193 | 3E | 3G | 3I | 3D | 3A | 3F | 3L | 3K    {A,D,E,F,G,I,K,L}
194 | 3E | 3G | 3J | 3D | 3A | 3F | 3L | 3I    {A,D,E,F,G,I,J,L}
195 | 3E | 3G | 3J | 3D | 3A | 3F | 3I | 3K    {A,D,E,F,G,I,J,K}
196 | 3H | 3G | 3E | 3D | 3A | 3F | 3L | 3K    {A,D,E,F,G,H,K,L}
197 | 3H | 3G | 3J | 3D | 3A | 3F | 3L | 3E    {A,D,E,F,G,H,J,L}
198 | 3H | 3G | 3J | 3D | 3A | 3F | 3E | 3K    {A,D,E,F,G,H,J,K}
199 | 3H | 3G | 3E | 3D | 3A | 3F | 3L | 3I    {A,D,E,F,G,H,I,L}
200 | 3H | 3G | 3E | 3D | 3A | 3F | 3I | 3K    {A,D,E,F,G,H,I,K}
201 | 3H | 3G | 3J | 3D | 3A | 3F | 3E | 3I    {A,D,E,F,G,H,I,J}
202 | 3H | 3J | 3I | 3C | 3A | 3G | 3L | 3K    {A,C,G,H,I,J,K,L}
203 | 3H | 3J | 3I | 3C | 3A | 3F | 3L | 3K    {A,C,F,H,I,J,K,L}
204 | 3I | 3G | 3J | 3C | 3A | 3F | 3L | 3K    {A,C,F,G,I,J,K,L}
205 | 3H | 3G | 3J | 3C | 3A | 3F | 3L | 3K    {A,C,F,G,H,J,K,L}
206 | 3H | 3G | 3I | 3C | 3A | 3F | 3L | 3K    {A,C,F,G,H,I,K,L}
207 | 3H | 3G | 3J | 3C | 3A | 3F | 3L | 3I    {A,C,F,G,H,I,J,L}
208 | 3H | 3G | 3J | 3C | 3A | 3F | 3I | 3K    {A,C,F,G,H,I,J,K}
209 | 3E | 3J | 3I | 3C | 3A | 3H | 3L | 3K    {A,C,E,H,I,J,K,L}
210 | 3E | 3J | 3I | 3C | 3A | 3G | 3L | 3K    {A,C,E,G,I,J,K,L}
211 | 3E | 3G | 3J | 3C | 3A | 3H | 3L | 3K    {A,C,E,G,H,J,K,L}
212 | 3E | 3G | 3I | 3C | 3A | 3H | 3L | 3K    {A,C,E,G,H,I,K,L}
213 | 3E | 3G | 3J | 3C | 3A | 3H | 3L | 3I    {A,C,E,G,H,I,J,L}
214 | 3E | 3G | 3J | 3C | 3A | 3H | 3I | 3K    {A,C,E,G,H,I,J,K}
215 | 3E | 3J | 3I | 3C | 3A | 3F | 3L | 3K    {A,C,E,F,I,J,K,L}
216 | 3H | 3J | 3E | 3C | 3A | 3F | 3L | 3K    {A,C,E,F,H,J,K,L}
217 | 3H | 3E | 3I | 3C | 3A | 3F | 3L | 3K    {A,C,E,F,H,I,K,L}
218 | 3H | 3J | 3E | 3C | 3A | 3F | 3L | 3I    {A,C,E,F,H,I,J,L}
219 | 3H | 3J | 3E | 3C | 3A | 3F | 3I | 3K    {A,C,E,F,H,I,J,K}
220 | 3E | 3G | 3J | 3C | 3A | 3F | 3L | 3K    {A,C,E,F,G,J,K,L}
221 | 3E | 3G | 3I | 3C | 3A | 3F | 3L | 3K    {A,C,E,F,G,I,K,L}
222 | 3E | 3G | 3J | 3C | 3A | 3F | 3L | 3I    {A,C,E,F,G,I,J,L}
223 | 3E | 3G | 3J | 3C | 3A | 3F | 3I | 3K    {A,C,E,F,G,I,J,K}
224 | 3H | 3G | 3E | 3C | 3A | 3F | 3L | 3K    {A,C,E,F,G,H,K,L}
225 | 3H | 3G | 3J | 3C | 3A | 3F | 3L | 3E    {A,C,E,F,G,H,J,L}
226 | 3H | 3G | 3J | 3C | 3A | 3F | 3E | 3K    {A,C,E,F,G,H,J,K}
227 | 3H | 3G | 3E | 3C | 3A | 3F | 3L | 3I    {A,C,E,F,G,H,I,L}
228 | 3H | 3G | 3E | 3C | 3A | 3F | 3I | 3K    {A,C,E,F,G,H,I,K}
229 | 3H | 3G | 3J | 3C | 3A | 3F | 3E | 3I    {A,C,E,F,G,H,I,J}
230 | 3H | 3J | 3I | 3C | 3A | 3D | 3L | 3K    {A,C,D,H,I,J,K,L}
231 | 3I | 3G | 3J | 3C | 3A | 3D | 3L | 3K    {A,C,D,G,I,J,K,L}
232 | 3H | 3G | 3J | 3C | 3A | 3D | 3L | 3K    {A,C,D,G,H,J,K,L}
233 | 3H | 3G | 3I | 3C | 3A | 3D | 3L | 3K    {A,C,D,G,H,I,K,L}
234 | 3H | 3G | 3J | 3C | 3A | 3D | 3L | 3I    {A,C,D,G,H,I,J,L}
235 | 3H | 3G | 3J | 3C | 3A | 3D | 3I | 3K    {A,C,D,G,H,I,J,K}
236 | 3C | 3J | 3I | 3D | 3A | 3F | 3L | 3K    {A,C,D,F,I,J,K,L}
237 | 3H | 3J | 3F | 3C | 3A | 3D | 3L | 3K    {A,C,D,F,H,J,K,L}
238 | 3H | 3F | 3I | 3C | 3A | 3D | 3L | 3K    {A,C,D,F,H,I,K,L}
239 | 3H | 3J | 3F | 3C | 3A | 3D | 3L | 3I    {A,C,D,F,H,I,J,L}
240 | 3H | 3J | 3F | 3C | 3A | 3D | 3I | 3K    {A,C,D,F,H,I,J,K}
241 | 3C | 3G | 3J | 3D | 3A | 3F | 3L | 3K    {A,C,D,F,G,J,K,L}
242 | 3C | 3G | 3I | 3D | 3A | 3F | 3L | 3K    {A,C,D,F,G,I,K,L}
243 | 3C | 3G | 3J | 3D | 3A | 3F | 3L | 3I    {A,C,D,F,G,I,J,L}
244 | 3C | 3G | 3J | 3D | 3A | 3F | 3I | 3K    {A,C,D,F,G,I,J,K}
245 | 3H | 3G | 3F | 3C | 3A | 3D | 3L | 3K    {A,C,D,F,G,H,K,L}
246 | 3C | 3G | 3J | 3D | 3A | 3F | 3L | 3H    {A,C,D,F,G,H,J,L}
247 | 3H | 3G | 3J | 3C | 3A | 3F | 3D | 3K    {A,C,D,F,G,H,J,K}
248 | 3H | 3G | 3F | 3C | 3A | 3D | 3L | 3I    {A,C,D,F,G,H,I,L}
249 | 3H | 3G | 3F | 3C | 3A | 3D | 3I | 3K    {A,C,D,F,G,H,I,K}
250 | 3H | 3G | 3J | 3C | 3A | 3F | 3D | 3I    {A,C,D,F,G,H,I,J}
251 | 3E | 3J | 3I | 3C | 3A | 3D | 3L | 3K    {A,C,D,E,I,J,K,L}
252 | 3H | 3J | 3E | 3C | 3A | 3D | 3L | 3K    {A,C,D,E,H,J,K,L}
253 | 3H | 3E | 3I | 3C | 3A | 3D | 3L | 3K    {A,C,D,E,H,I,K,L}
254 | 3H | 3J | 3E | 3C | 3A | 3D | 3L | 3I    {A,C,D,E,H,I,J,L}
255 | 3H | 3J | 3E | 3C | 3A | 3D | 3I | 3K    {A,C,D,E,H,I,J,K}
256 | 3E | 3G | 3J | 3C | 3A | 3D | 3L | 3K    {A,C,D,E,G,J,K,L}
257 | 3E | 3G | 3I | 3C | 3A | 3D | 3L | 3K    {A,C,D,E,G,I,K,L}
258 | 3E | 3G | 3J | 3C | 3A | 3D | 3L | 3I    {A,C,D,E,G,I,J,L}
259 | 3E | 3G | 3J | 3C | 3A | 3D | 3I | 3K    {A,C,D,E,G,I,J,K}
260 | 3H | 3G | 3E | 3C | 3A | 3D | 3L | 3K    {A,C,D,E,G,H,K,L}
261 | 3H | 3G | 3J | 3C | 3A | 3D | 3L | 3E    {A,C,D,E,G,H,J,L}
262 | 3H | 3G | 3J | 3C | 3A | 3D | 3E | 3K    {A,C,D,E,G,H,J,K}
263 | 3H | 3G | 3E | 3C | 3A | 3D | 3L | 3I    {A,C,D,E,G,H,I,L}
264 | 3H | 3G | 3E | 3C | 3A | 3D | 3I | 3K    {A,C,D,E,G,H,I,K}
265 | 3H | 3G | 3J | 3C | 3A | 3D | 3E | 3I    {A,C,D,E,G,H,I,J}
266 | 3C | 3J | 3E | 3D | 3A | 3F | 3L | 3K    {A,C,D,E,F,J,K,L}
267 | 3C | 3E | 3I | 3D | 3A | 3F | 3L | 3K    {A,C,D,E,F,I,K,L}
268 | 3C | 3J | 3E | 3D | 3A | 3F | 3L | 3I    {A,C,D,E,F,I,J,L}
269 | 3C | 3J | 3E | 3D | 3A | 3F | 3I | 3K    {A,C,D,E,F,I,J,K}
270 | 3H | 3E | 3F | 3C | 3A | 3D | 3L | 3K    {A,C,D,E,F,H,K,L}
271 | 3H | 3J | 3F | 3C | 3A | 3D | 3L | 3E    {A,C,D,E,F,H,J,L}
272 | 3H | 3J | 3E | 3C | 3A | 3F | 3D | 3K    {A,C,D,E,F,H,J,K}
273 | 3H | 3E | 3F | 3C | 3A | 3D | 3L | 3I    {A,C,D,E,F,H,I,L}
274 | 3H | 3E | 3F | 3C | 3A | 3D | 3I | 3K    {A,C,D,E,F,H,I,K}
275 | 3H | 3J | 3E | 3C | 3A | 3F | 3D | 3I    {A,C,D,E,F,H,I,J}
276 | 3C | 3G | 3E | 3D | 3A | 3F | 3L | 3K    {A,C,D,E,F,G,K,L}
277 | 3C | 3G | 3J | 3D | 3A | 3F | 3L | 3E    {A,C,D,E,F,G,J,L}
278 | 3C | 3G | 3J | 3D | 3A | 3F | 3E | 3K    {A,C,D,E,F,G,J,K}
279 | 3C | 3G | 3E | 3D | 3A | 3F | 3L | 3I    {A,C,D,E,F,G,I,L}
280 | 3C | 3G | 3E | 3D | 3A | 3F | 3I | 3K    {A,C,D,E,F,G,I,K}
281 | 3C | 3G | 3J | 3D | 3A | 3F | 3E | 3I    {A,C,D,E,F,G,I,J}
282 | 3H | 3G | 3F | 3C | 3A | 3D | 3L | 3E    {A,C,D,E,F,G,H,L}
283 | 3H | 3G | 3E | 3C | 3A | 3F | 3D | 3K    {A,C,D,E,F,G,H,K}
284 | 3H | 3G | 3J | 3C | 3A | 3F | 3D | 3E    {A,C,D,E,F,G,H,J}
285 | 3H | 3G | 3E | 3C | 3A | 3F | 3D | 3I    {A,C,D,E,F,G,H,I}
286 | 3H | 3J | 3B | 3A | 3I | 3G | 3L | 3K    {A,B,G,H,I,J,K,L}
287 | 3H | 3J | 3B | 3A | 3I | 3F | 3L | 3K    {A,B,F,H,I,J,K,L}
288 | 3I | 3J | 3B | 3F | 3A | 3G | 3L | 3K    {A,B,F,G,I,J,K,L}
289 | 3H | 3J | 3B | 3F | 3A | 3G | 3L | 3K    {A,B,F,G,H,J,K,L}
290 | 3H | 3G | 3B | 3A | 3I | 3F | 3L | 3K    {A,B,F,G,H,I,K,L}
291 | 3H | 3J | 3B | 3F | 3A | 3G | 3L | 3I    {A,B,F,G,H,I,J,L}
292 | 3H | 3J | 3B | 3F | 3A | 3G | 3I | 3K    {A,B,F,G,H,I,J,K}
293 | 3E | 3J | 3B | 3A | 3I | 3H | 3L | 3K    {A,B,E,H,I,J,K,L}
294 | 3E | 3J | 3B | 3A | 3I | 3G | 3L | 3K    {A,B,E,G,I,J,K,L}
295 | 3E | 3J | 3B | 3A | 3H | 3G | 3L | 3K    {A,B,E,G,H,J,K,L}
296 | 3E | 3G | 3B | 3A | 3I | 3H | 3L | 3K    {A,B,E,G,H,I,K,L}
297 | 3E | 3J | 3B | 3A | 3H | 3G | 3L | 3I    {A,B,E,G,H,I,J,L}
298 | 3E | 3J | 3B | 3A | 3H | 3G | 3I | 3K    {A,B,E,G,H,I,J,K}
299 | 3E | 3J | 3B | 3A | 3I | 3F | 3L | 3K    {A,B,E,F,I,J,K,L}
300 | 3E | 3J | 3B | 3F | 3A | 3H | 3L | 3K    {A,B,E,F,H,J,K,L}
301 | 3E | 3I | 3B | 3F | 3A | 3H | 3L | 3K    {A,B,E,F,H,I,K,L}
302 | 3E | 3J | 3B | 3F | 3A | 3H | 3L | 3I    {A,B,E,F,H,I,J,L}
303 | 3E | 3J | 3B | 3F | 3A | 3H | 3I | 3K    {A,B,E,F,H,I,J,K}
304 | 3E | 3J | 3B | 3F | 3A | 3G | 3L | 3K    {A,B,E,F,G,J,K,L}
305 | 3E | 3G | 3B | 3A | 3I | 3F | 3L | 3K    {A,B,E,F,G,I,K,L}
306 | 3E | 3J | 3B | 3F | 3A | 3G | 3L | 3I    {A,B,E,F,G,I,J,L}
307 | 3E | 3J | 3B | 3F | 3A | 3G | 3I | 3K    {A,B,E,F,G,I,J,K}
308 | 3E | 3G | 3B | 3F | 3A | 3H | 3L | 3K    {A,B,E,F,G,H,K,L}
309 | 3H | 3J | 3B | 3F | 3A | 3G | 3L | 3E    {A,B,E,F,G,H,J,L}
310 | 3H | 3J | 3B | 3F | 3A | 3G | 3E | 3K    {A,B,E,F,G,H,J,K}
311 | 3E | 3G | 3B | 3F | 3A | 3H | 3L | 3I    {A,B,E,F,G,H,I,L}
312 | 3E | 3G | 3B | 3F | 3A | 3H | 3I | 3K    {A,B,E,F,G,H,I,K}
313 | 3H | 3J | 3B | 3F | 3A | 3G | 3E | 3I    {A,B,E,F,G,H,I,J}
314 | 3I | 3J | 3B | 3D | 3A | 3H | 3L | 3K    {A,B,D,H,I,J,K,L}
315 | 3I | 3J | 3B | 3D | 3A | 3G | 3L | 3K    {A,B,D,G,I,J,K,L}
316 | 3H | 3J | 3B | 3D | 3A | 3G | 3L | 3K    {A,B,D,G,H,J,K,L}
317 | 3I | 3G | 3B | 3D | 3A | 3H | 3L | 3K    {A,B,D,G,H,I,K,L}
318 | 3H | 3J | 3B | 3D | 3A | 3G | 3L | 3I    {A,B,D,G,H,I,J,L}
319 | 3H | 3J | 3B | 3D | 3A | 3G | 3I | 3K    {A,B,D,G,H,I,J,K}
320 | 3I | 3J | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,D,F,I,J,K,L}
321 | 3H | 3J | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,D,F,H,J,K,L}
322 | 3H | 3I | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,D,F,H,I,K,L}
323 | 3H | 3J | 3B | 3D | 3A | 3F | 3L | 3I    {A,B,D,F,H,I,J,L}
324 | 3H | 3J | 3B | 3D | 3A | 3F | 3I | 3K    {A,B,D,F,H,I,J,K}
325 | 3F | 3J | 3B | 3D | 3A | 3G | 3L | 3K    {A,B,D,F,G,J,K,L}
326 | 3I | 3G | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,D,F,G,I,K,L}
327 | 3F | 3J | 3B | 3D | 3A | 3G | 3L | 3I    {A,B,D,F,G,I,J,L}
328 | 3F | 3J | 3B | 3D | 3A | 3G | 3I | 3K    {A,B,D,F,G,I,J,K}
329 | 3H | 3G | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,D,F,G,H,K,L}
330 | 3H | 3G | 3B | 3D | 3A | 3F | 3L | 3J    {A,B,D,F,G,H,J,L}
331 | 3H | 3G | 3B | 3D | 3A | 3F | 3J | 3K    {A,B,D,F,G,H,J,K}
332 | 3H | 3G | 3B | 3D | 3A | 3F | 3L | 3I    {A,B,D,F,G,H,I,L}
333 | 3H | 3G | 3B | 3D | 3A | 3F | 3I | 3K    {A,B,D,F,G,H,I,K}
334 | 3H | 3G | 3B | 3D | 3A | 3F | 3I | 3J    {A,B,D,F,G,H,I,J}
335 | 3E | 3J | 3B | 3A | 3I | 3D | 3L | 3K    {A,B,D,E,I,J,K,L}
336 | 3E | 3J | 3B | 3D | 3A | 3H | 3L | 3K    {A,B,D,E,H,J,K,L}
337 | 3E | 3I | 3B | 3D | 3A | 3H | 3L | 3K    {A,B,D,E,H,I,K,L}
338 | 3E | 3J | 3B | 3D | 3A | 3H | 3L | 3I    {A,B,D,E,H,I,J,L}
339 | 3E | 3J | 3B | 3D | 3A | 3H | 3I | 3K    {A,B,D,E,H,I,J,K}
340 | 3E | 3J | 3B | 3D | 3A | 3G | 3L | 3K    {A,B,D,E,G,J,K,L}
341 | 3E | 3G | 3B | 3A | 3I | 3D | 3L | 3K    {A,B,D,E,G,I,K,L}
342 | 3E | 3J | 3B | 3D | 3A | 3G | 3L | 3I    {A,B,D,E,G,I,J,L}
343 | 3E | 3J | 3B | 3D | 3A | 3G | 3I | 3K    {A,B,D,E,G,I,J,K}
344 | 3E | 3G | 3B | 3D | 3A | 3H | 3L | 3K    {A,B,D,E,G,H,K,L}
345 | 3H | 3J | 3B | 3D | 3A | 3G | 3L | 3E    {A,B,D,E,G,H,J,L}
346 | 3H | 3J | 3B | 3D | 3A | 3G | 3E | 3K    {A,B,D,E,G,H,J,K}
347 | 3E | 3G | 3B | 3D | 3A | 3H | 3L | 3I    {A,B,D,E,G,H,I,L}
348 | 3E | 3G | 3B | 3D | 3A | 3H | 3I | 3K    {A,B,D,E,G,H,I,K}
349 | 3H | 3J | 3B | 3D | 3A | 3G | 3E | 3I    {A,B,D,E,G,H,I,J}
350 | 3E | 3J | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,D,E,F,J,K,L}
351 | 3E | 3I | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,D,E,F,I,K,L}
352 | 3E | 3J | 3B | 3D | 3A | 3F | 3L | 3I    {A,B,D,E,F,I,J,L}
353 | 3E | 3J | 3B | 3D | 3A | 3F | 3I | 3K    {A,B,D,E,F,I,J,K}
354 | 3H | 3E | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,D,E,F,H,K,L}
355 | 3H | 3J | 3B | 3D | 3A | 3F | 3L | 3E    {A,B,D,E,F,H,J,L}
356 | 3H | 3J | 3B | 3D | 3A | 3F | 3E | 3K    {A,B,D,E,F,H,J,K}
357 | 3H | 3E | 3B | 3D | 3A | 3F | 3L | 3I    {A,B,D,E,F,H,I,L}
358 | 3H | 3E | 3B | 3D | 3A | 3F | 3I | 3K    {A,B,D,E,F,H,I,K}
359 | 3H | 3J | 3B | 3D | 3A | 3F | 3E | 3I    {A,B,D,E,F,H,I,J}
360 | 3E | 3G | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,D,E,F,G,K,L}
361 | 3E | 3G | 3B | 3D | 3A | 3F | 3L | 3J    {A,B,D,E,F,G,J,L}
362 | 3E | 3G | 3B | 3D | 3A | 3F | 3J | 3K    {A,B,D,E,F,G,J,K}
363 | 3E | 3G | 3B | 3D | 3A | 3F | 3L | 3I    {A,B,D,E,F,G,I,L}
364 | 3E | 3G | 3B | 3D | 3A | 3F | 3I | 3K    {A,B,D,E,F,G,I,K}
365 | 3E | 3G | 3B | 3D | 3A | 3F | 3I | 3J    {A,B,D,E,F,G,I,J}
366 | 3H | 3G | 3B | 3D | 3A | 3F | 3L | 3E    {A,B,D,E,F,G,H,L}
367 | 3H | 3G | 3B | 3D | 3A | 3F | 3E | 3K    {A,B,D,E,F,G,H,K}
368 | 3H | 3G | 3B | 3D | 3A | 3F | 3E | 3J    {A,B,D,E,F,G,H,J}
369 | 3H | 3G | 3B | 3D | 3A | 3F | 3E | 3I    {A,B,D,E,F,G,H,I}
370 | 3I | 3J | 3B | 3C | 3A | 3H | 3L | 3K    {A,B,C,H,I,J,K,L}
371 | 3I | 3J | 3B | 3C | 3A | 3G | 3L | 3K    {A,B,C,G,I,J,K,L}
372 | 3H | 3J | 3B | 3C | 3A | 3G | 3L | 3K    {A,B,C,G,H,J,K,L}
373 | 3I | 3G | 3B | 3C | 3A | 3H | 3L | 3K    {A,B,C,G,H,I,K,L}
374 | 3H | 3J | 3B | 3C | 3A | 3G | 3L | 3I    {A,B,C,G,H,I,J,L}
375 | 3H | 3J | 3B | 3C | 3A | 3G | 3I | 3K    {A,B,C,G,H,I,J,K}
376 | 3I | 3J | 3B | 3C | 3A | 3F | 3L | 3K    {A,B,C,F,I,J,K,L}
377 | 3H | 3J | 3B | 3C | 3A | 3F | 3L | 3K    {A,B,C,F,H,J,K,L}
378 | 3H | 3I | 3B | 3C | 3A | 3F | 3L | 3K    {A,B,C,F,H,I,K,L}
379 | 3H | 3J | 3B | 3C | 3A | 3F | 3L | 3I    {A,B,C,F,H,I,J,L}
380 | 3H | 3J | 3B | 3C | 3A | 3F | 3I | 3K    {A,B,C,F,H,I,J,K}
381 | 3C | 3J | 3B | 3F | 3A | 3G | 3L | 3K    {A,B,C,F,G,J,K,L}
382 | 3I | 3G | 3B | 3C | 3A | 3F | 3L | 3K    {A,B,C,F,G,I,K,L}
383 | 3C | 3J | 3B | 3F | 3A | 3G | 3L | 3I    {A,B,C,F,G,I,J,L}
384 | 3C | 3J | 3B | 3F | 3A | 3G | 3I | 3K    {A,B,C,F,G,I,J,K}
385 | 3H | 3G | 3B | 3C | 3A | 3F | 3L | 3K    {A,B,C,F,G,H,K,L}
386 | 3H | 3G | 3B | 3C | 3A | 3F | 3L | 3J    {A,B,C,F,G,H,J,L}
387 | 3H | 3G | 3B | 3C | 3A | 3F | 3J | 3K    {A,B,C,F,G,H,J,K}
388 | 3H | 3G | 3B | 3C | 3A | 3F | 3L | 3I    {A,B,C,F,G,H,I,L}
389 | 3H | 3G | 3B | 3C | 3A | 3F | 3I | 3K    {A,B,C,F,G,H,I,K}
390 | 3H | 3G | 3B | 3C | 3A | 3F | 3I | 3J    {A,B,C,F,G,H,I,J}
391 | 3E | 3J | 3B | 3A | 3I | 3C | 3L | 3K    {A,B,C,E,I,J,K,L}
392 | 3E | 3J | 3B | 3C | 3A | 3H | 3L | 3K    {A,B,C,E,H,J,K,L}
393 | 3E | 3I | 3B | 3C | 3A | 3H | 3L | 3K    {A,B,C,E,H,I,K,L}
394 | 3E | 3J | 3B | 3C | 3A | 3H | 3L | 3I    {A,B,C,E,H,I,J,L}
395 | 3E | 3J | 3B | 3C | 3A | 3H | 3I | 3K    {A,B,C,E,H,I,J,K}
396 | 3E | 3J | 3B | 3C | 3A | 3G | 3L | 3K    {A,B,C,E,G,J,K,L}
397 | 3E | 3G | 3B | 3A | 3I | 3C | 3L | 3K    {A,B,C,E,G,I,K,L}
398 | 3E | 3J | 3B | 3C | 3A | 3G | 3L | 3I    {A,B,C,E,G,I,J,L}
399 | 3E | 3J | 3B | 3C | 3A | 3G | 3I | 3K    {A,B,C,E,G,I,J,K}
400 | 3E | 3G | 3B | 3C | 3A | 3H | 3L | 3K    {A,B,C,E,G,H,K,L}
401 | 3H | 3J | 3B | 3C | 3A | 3G | 3L | 3E    {A,B,C,E,G,H,J,L}
402 | 3H | 3J | 3B | 3C | 3A | 3G | 3E | 3K    {A,B,C,E,G,H,J,K}
403 | 3E | 3G | 3B | 3C | 3A | 3H | 3L | 3I    {A,B,C,E,G,H,I,L}
404 | 3E | 3G | 3B | 3C | 3A | 3H | 3I | 3K    {A,B,C,E,G,H,I,K}
405 | 3H | 3J | 3B | 3C | 3A | 3G | 3E | 3I    {A,B,C,E,G,H,I,J}
406 | 3E | 3J | 3B | 3C | 3A | 3F | 3L | 3K    {A,B,C,E,F,J,K,L}
407 | 3E | 3I | 3B | 3C | 3A | 3F | 3L | 3K    {A,B,C,E,F,I,K,L}
408 | 3E | 3J | 3B | 3C | 3A | 3F | 3L | 3I    {A,B,C,E,F,I,J,L}
409 | 3E | 3J | 3B | 3C | 3A | 3F | 3I | 3K    {A,B,C,E,F,I,J,K}
410 | 3H | 3E | 3B | 3C | 3A | 3F | 3L | 3K    {A,B,C,E,F,H,K,L}
411 | 3H | 3J | 3B | 3C | 3A | 3F | 3L | 3E    {A,B,C,E,F,H,J,L}
412 | 3H | 3J | 3B | 3C | 3A | 3F | 3E | 3K    {A,B,C,E,F,H,J,K}
413 | 3H | 3E | 3B | 3C | 3A | 3F | 3L | 3I    {A,B,C,E,F,H,I,L}
414 | 3H | 3E | 3B | 3C | 3A | 3F | 3I | 3K    {A,B,C,E,F,H,I,K}
415 | 3H | 3J | 3B | 3C | 3A | 3F | 3E | 3I    {A,B,C,E,F,H,I,J}
416 | 3E | 3G | 3B | 3C | 3A | 3F | 3L | 3K    {A,B,C,E,F,G,K,L}
417 | 3E | 3G | 3B | 3C | 3A | 3F | 3L | 3J    {A,B,C,E,F,G,J,L}
418 | 3E | 3G | 3B | 3C | 3A | 3F | 3J | 3K    {A,B,C,E,F,G,J,K}
419 | 3E | 3G | 3B | 3C | 3A | 3F | 3L | 3I    {A,B,C,E,F,G,I,L}
420 | 3E | 3G | 3B | 3C | 3A | 3F | 3I | 3K    {A,B,C,E,F,G,I,K}
421 | 3E | 3G | 3B | 3C | 3A | 3F | 3I | 3J    {A,B,C,E,F,G,I,J}
422 | 3H | 3G | 3B | 3C | 3A | 3F | 3L | 3E    {A,B,C,E,F,G,H,L}
423 | 3H | 3G | 3B | 3C | 3A | 3F | 3E | 3K    {A,B,C,E,F,G,H,K}
424 | 3H | 3G | 3B | 3C | 3A | 3F | 3E | 3J    {A,B,C,E,F,G,H,J}
425 | 3H | 3G | 3B | 3C | 3A | 3F | 3E | 3I    {A,B,C,E,F,G,H,I}
426 | 3I | 3J | 3B | 3C | 3A | 3D | 3L | 3K    {A,B,C,D,I,J,K,L}
427 | 3H | 3J | 3B | 3C | 3A | 3D | 3L | 3K    {A,B,C,D,H,J,K,L}
428 | 3H | 3I | 3B | 3C | 3A | 3D | 3L | 3K    {A,B,C,D,H,I,K,L}
429 | 3H | 3J | 3B | 3C | 3A | 3D | 3L | 3I    {A,B,C,D,H,I,J,L}
430 | 3H | 3J | 3B | 3C | 3A | 3D | 3I | 3K    {A,B,C,D,H,I,J,K}
431 | 3C | 3J | 3B | 3D | 3A | 3G | 3L | 3K    {A,B,C,D,G,J,K,L}
432 | 3I | 3G | 3B | 3C | 3A | 3D | 3L | 3K    {A,B,C,D,G,I,K,L}
433 | 3C | 3J | 3B | 3D | 3A | 3G | 3L | 3I    {A,B,C,D,G,I,J,L}
434 | 3C | 3J | 3B | 3D | 3A | 3G | 3I | 3K    {A,B,C,D,G,I,J,K}
435 | 3H | 3G | 3B | 3C | 3A | 3D | 3L | 3K    {A,B,C,D,G,H,K,L}
436 | 3H | 3G | 3B | 3C | 3A | 3D | 3L | 3J    {A,B,C,D,G,H,J,L}
437 | 3H | 3G | 3B | 3C | 3A | 3D | 3J | 3K    {A,B,C,D,G,H,J,K}
438 | 3H | 3G | 3B | 3C | 3A | 3D | 3L | 3I    {A,B,C,D,G,H,I,L}
439 | 3H | 3G | 3B | 3C | 3A | 3D | 3I | 3K    {A,B,C,D,G,H,I,K}
440 | 3H | 3G | 3B | 3C | 3A | 3D | 3I | 3J    {A,B,C,D,G,H,I,J}
441 | 3C | 3J | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,C,D,F,J,K,L}
442 | 3C | 3I | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,C,D,F,I,K,L}
443 | 3C | 3J | 3B | 3D | 3A | 3F | 3L | 3I    {A,B,C,D,F,I,J,L}
444 | 3C | 3J | 3B | 3D | 3A | 3F | 3I | 3K    {A,B,C,D,F,I,J,K}
445 | 3H | 3F | 3B | 3C | 3A | 3D | 3L | 3K    {A,B,C,D,F,H,K,L}
446 | 3C | 3J | 3B | 3D | 3A | 3F | 3L | 3H    {A,B,C,D,F,H,J,L}
447 | 3H | 3J | 3B | 3C | 3A | 3F | 3D | 3K    {A,B,C,D,F,H,J,K}
448 | 3H | 3F | 3B | 3C | 3A | 3D | 3L | 3I    {A,B,C,D,F,H,I,L}
449 | 3H | 3F | 3B | 3C | 3A | 3D | 3I | 3K    {A,B,C,D,F,H,I,K}
450 | 3H | 3J | 3B | 3C | 3A | 3F | 3D | 3I    {A,B,C,D,F,H,I,J}
451 | 3C | 3G | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,C,D,F,G,K,L}
452 | 3C | 3G | 3B | 3D | 3A | 3F | 3L | 3J    {A,B,C,D,F,G,J,L}
453 | 3C | 3G | 3B | 3D | 3A | 3F | 3J | 3K    {A,B,C,D,F,G,J,K}
454 | 3C | 3G | 3B | 3D | 3A | 3F | 3L | 3I    {A,B,C,D,F,G,I,L}
455 | 3C | 3G | 3B | 3D | 3A | 3F | 3I | 3K    {A,B,C,D,F,G,I,K}
456 | 3C | 3G | 3B | 3D | 3A | 3F | 3I | 3J    {A,B,C,D,F,G,I,J}
457 | 3C | 3G | 3B | 3D | 3A | 3F | 3L | 3H    {A,B,C,D,F,G,H,L}
458 | 3H | 3G | 3B | 3C | 3A | 3F | 3D | 3K    {A,B,C,D,F,G,H,K}
459 | 3H | 3G | 3B | 3C | 3A | 3F | 3D | 3J    {A,B,C,D,F,G,H,J}
460 | 3H | 3G | 3B | 3C | 3A | 3F | 3D | 3I    {A,B,C,D,F,G,H,I}
461 | 3E | 3J | 3B | 3C | 3A | 3D | 3L | 3K    {A,B,C,D,E,J,K,L}
462 | 3E | 3I | 3B | 3C | 3A | 3D | 3L | 3K    {A,B,C,D,E,I,K,L}
463 | 3E | 3J | 3B | 3C | 3A | 3D | 3L | 3I    {A,B,C,D,E,I,J,L}
464 | 3E | 3J | 3B | 3C | 3A | 3D | 3I | 3K    {A,B,C,D,E,I,J,K}
465 | 3H | 3E | 3B | 3C | 3A | 3D | 3L | 3K    {A,B,C,D,E,H,K,L}
466 | 3H | 3J | 3B | 3C | 3A | 3D | 3L | 3E    {A,B,C,D,E,H,J,L}
467 | 3H | 3J | 3B | 3C | 3A | 3D | 3E | 3K    {A,B,C,D,E,H,J,K}
468 | 3H | 3E | 3B | 3C | 3A | 3D | 3L | 3I    {A,B,C,D,E,H,I,L}
469 | 3H | 3E | 3B | 3C | 3A | 3D | 3I | 3K    {A,B,C,D,E,H,I,K}
470 | 3H | 3J | 3B | 3C | 3A | 3D | 3E | 3I    {A,B,C,D,E,H,I,J}
471 | 3E | 3G | 3B | 3C | 3A | 3D | 3L | 3K    {A,B,C,D,E,G,K,L}
472 | 3E | 3G | 3B | 3C | 3A | 3D | 3L | 3J    {A,B,C,D,E,G,J,L}
473 | 3E | 3G | 3B | 3C | 3A | 3D | 3J | 3K    {A,B,C,D,E,G,J,K}
474 | 3E | 3G | 3B | 3C | 3A | 3D | 3L | 3I    {A,B,C,D,E,G,I,L}
475 | 3E | 3G | 3B | 3C | 3A | 3D | 3I | 3K    {A,B,C,D,E,G,I,K}
476 | 3E | 3G | 3B | 3C | 3A | 3D | 3I | 3J    {A,B,C,D,E,G,I,J}
477 | 3H | 3G | 3B | 3C | 3A | 3D | 3L | 3E    {A,B,C,D,E,G,H,L}
478 | 3H | 3G | 3B | 3C | 3A | 3D | 3E | 3K    {A,B,C,D,E,G,H,K}
479 | 3H | 3G | 3B | 3C | 3A | 3D | 3E | 3J    {A,B,C,D,E,G,H,J}
480 | 3H | 3G | 3B | 3C | 3A | 3D | 3E | 3I    {A,B,C,D,E,G,H,I}
481 | 3C | 3E | 3B | 3D | 3A | 3F | 3L | 3K    {A,B,C,D,E,F,K,L}
482 | 3C | 3J | 3B | 3D | 3A | 3F | 3L | 3E    {A,B,C,D,E,F,J,L}
483 | 3C | 3J | 3B | 3D | 3A | 3F | 3E | 3K    {A,B,C,D,E,F,J,K}
484 | 3C | 3E | 3B | 3D | 3A | 3F | 3L | 3I    {A,B,C,D,E,F,I,L}
485 | 3C | 3E | 3B | 3D | 3A | 3F | 3I | 3K    {A,B,C,D,E,F,I,K}
486 | 3C | 3J | 3B | 3D | 3A | 3F | 3E | 3I    {A,B,C,D,E,F,I,J}
487 | 3H | 3F | 3B | 3C | 3A | 3D | 3L | 3E    {A,B,C,D,E,F,H,L}
488 | 3H | 3E | 3B | 3C | 3A | 3F | 3D | 3K    {A,B,C,D,E,F,H,K}
489 | 3H | 3J | 3B | 3C | 3A | 3F | 3D | 3E    {A,B,C,D,E,F,H,J}
490 | 3H | 3E | 3B | 3C | 3A | 3F | 3D | 3I    {A,B,C,D,E,F,H,I}
491 | 3C | 3G | 3B | 3D | 3A | 3F | 3L | 3E    {A,B,C,D,E,F,G,L}
492 | 3C | 3G | 3B | 3D | 3A | 3F | 3E | 3K    {A,B,C,D,E,F,G,K}
493 | 3C | 3G | 3B | 3D | 3A | 3F | 3E | 3J    {A,B,C,D,E,F,G,J}
494 | 3C | 3G | 3B | 3D | 3A | 3F | 3E | 3I    {A,B,C,D,E,F,G,I}
495 | 3H | 3G | 3B | 3C | 3A | 3F | 3D | 3E    {A,B,C,D,E,F,G,H}
```

---

## 3. Group Standings Gap for Cross-Group Ranking

`app/model/standings.py` → `compute_standings()` returns `list[StandingRow]`.  
**Gap:** `StandingRow` has `team_name` but NOT `team_id`. The internal ranking uses `(team_id, StandingRow)` pairs but only exposes the rows. For cross-group 3rd-place ranking, the simulator needs `team_id` to link Elo ratings.

**Fix needed:** Expose `ranked_with_ids() -> list[tuple[int, StandingRow]]` OR add `team_id: int` field to `StandingRow`.

---

## 4. Match Simulation Primitive

**Group stage:** Use `predict_proba(params, elo_diff, neutral=True)` → sample W/D/L → 3/1/0 pts.  
For goal simulation (GD needed for tiebreakers): Simplification = Poisson-style goals from win probability. Or simpler: use P(H), P(D), P(A) and assign deterministic score proxies (e.g., W=1-0, D=0-0, L=0-1). Recommended: track simulated goal tallies with Poisson draws conditioned on outcome. Document as v2 enhancement; v1 can use W/D/L only + random tiebreak at group stage.

**Knockout:** No draw → renormalize:  
`P(home_advances) = P(H) / (P(H) + P(A))`  
`P(away_advances) = P(A) / (P(H) + P(A))`  
P(draw) is absorbed proportionally. Caveat: OLM was trained on full-time outcomes including draws; the renormalization is a reasonable first approximation but slightly overestimates the stronger team's probability (since draws skew toward even-strength games).

**Alternative (more faithful):** Treat P(draw) as 50/50 shootout:  
`P(home_ko) = P(H) + 0.5 × P(D)`, `P(away_ko) = P(A) + 0.5 × P(D)`  
This is the preferred approach — document chosen method in montecarlo.py docstring.

---

## 5. Elo for Future Rounds

- Static Elo (no in-tournament updates per sim): Simplification standard for Monte Carlo.
- Load all 48 teams' current Elo ONCE before sim loop: batch query `elo_rating` filtered to latest `rating_date` per team.
- `ratings.py` → `lookup_rating(session, team_id, before_date)` available but uses strict `< date` — not suitable for batch pre-load. Add `get_current_ratings(session, team_ids) -> dict[int, float]` helper.
- HOME_ADVANTAGE = 100.0 Elo points — NOT applied for neutral-site WC matches (`neutral=True`).
- `app/model/elo_engine.py` likely has batch capabilities; verify before writing new code.

---

## 6. Futures Odds Endpoint

**Current config:**
- `odds_sport_key = "soccer_fifa_world_cup"` → regular match odds (h2h, totals)
- NO futures/outrights market captured

**Required additions:**
- Futures sport key: `soccer_fifa_world_cup_winner` OR market `outrights` on `soccer_fifa_world_cup`  
  → Must verify via `/v4/sports` endpoint (free, no credit cost) which key exposes outright winner market
- Credit cost: `outrights` market = 1 credit per snapshot (1 market × 1 region)
- At 500 credits/month → 500 outright snapshots/month (~16/day, very affordable)
- Outright winner odds cover all 48 teams in one response

**Group advance / reach-final:** Not typically on The Odds API free tier for national team futures. BetPlay/Kambi manual fallback for group advance (Kambi has it but 429 from datacenter). Recommend: scrape BetPlay group advance odds manually until closing line approach is confirmed.

**Missing infrastructure:**
- New `OddsApiSource` config: `odds_futures_sport_key` setting + scheduler job
- Map `outrights` market key → `MarketType.OUTRIGHT_WINNER` in pipeline
- `outcome_name` (bookmaker's team name) → canonical team via `TeamAlias`

---

## 7. DB Readiness

| Item | Status |
|------|--------|
| 12 tournament groups (A–L) seeded | ✅ |
| 48 teams in `group_team` | ✅ |
| 72 GROUP matches SCHEDULED | ✅ (group stage started 2026-06-11, scores all NULL) |
| Knockout fixtures in `match` table | ❌ None — simulator must generate knockout bracket in-memory |
| Elo ratings for 336 distinct teams | ✅ Latest as of 2026-06-06/07 |
| `prediction` table supports `OUTRIGHT_WINNER`, `GROUP_ADVANCE` | ✅ via `MarketType` enum |
| `odds` table supports futures (`competition_id`, `outcome_team_id`) | ✅ |
| `MarketType.REACH_FINAL` / `REACH_SEMI` | ❌ Missing — need to add to enum or use `outcome_code` |

---

## 8. Architecture Fit

### Proposed new module: `app/model/montecarlo.py`

```python
def simulate_tournament(
    groups: dict[str, list[int]],      # {group_name: [team_id, ...]}
    elo_ratings: dict[int, float],     # {team_id: current_rating}
    model_params: dict,                # OLM params (from model_version.params_json)
    n_iterations: int = 10_000,
    seed: int | None = None,
) -> dict[int, dict[str, float]]:     # {team_id: {p_champion, p_reach_final, p_reach_semi, p_advance_group}}
```

**Key sub-steps per iteration:**
1. Simulate all 72 group matches → standings per group
2. Select top 2 per group (24 teams)
3. Rank 12 third-placed teams → select best 8 (pts→gd→gf→Elo proxy for FIFA ranking)
4. Look up Annex C → assign 8 third-placed teams to correct R32 slots
5. Build R32 bracket (fixed pairing table above)
6. Simulate R32 → R16 → QF → SF → Final knockout chain
7. Record advancing team at each stage per team_id

**Storage:** Write Monte Carlo outputs to `prediction` table:
- `market_type=OUTRIGHT_WINNER`, `outcome_code=None`, `probability=p_champion` (one row per team)
- `market_type=GROUP_ADVANCE`, `outcome_code=None`, `probability=p_advance_group`
- Add `outcome_code` variants: `"REACH_FINAL"`, `"REACH_SEMI"` using existing `outcome_code` column
  → Avoids adding new MarketType enum values; uses GROUP_ADVANCE type for all tournament progression

**OR** (cleaner, more explicit): Add `TOURNAMENT_STAGE` to `MarketType` enum with `outcome_code` distinguishing the stage.  
**Recommendation:** Keep `OUTRIGHT_WINNER` for champion, use `GROUP_ADVANCE` with `outcome_code="ADVANCE_GROUP" | "REACH_R16" | "REACH_QF" | "REACH_SF" | "REACH_FINAL"`.

### Annex C embed strategy:
Hardcode as `ANNEX_C: dict[frozenset[str], dict[str, str]]` at module level (~495 entries, ~50KB uncompressed in Python). Key = `frozenset({'A','B',...})`, value = `{'1A':'E','1B':'J',...}`.

---

## Affected Areas

| File | Role |
|------|------|
| `app/model/montecarlo.py` | NEW — full Monte Carlo engine |
| `app/model/standings.py` | Needs `team_id` exposed in return or new helper |
| `app/models/enums.py` | Consider `outcome_code` approach vs new MarketType |
| `app/core/config.py` | Add `odds_futures_sport_key`, `odds_futures_markets` settings |
| `app/ingestion/sources/odds_api.py` | Add futures snapshot capability |
| `app/ingestion/odds_pipeline.py` | Map `outrights` market to OUTRIGHT_WINNER |
| `app/scheduler/jobs.py` | Add futures odds capture job |
| `app/api/routers/` | New `/futures` endpoint serving Monte Carlo predictions |
| `app/models/model.py` | Prediction rows storage (no schema changes needed) |

---

## Approaches

### A. Full Monte Carlo (recommended)
Group stage simulation (W/D/L + tiebreakers) + full knockout bracket using Annex C lookup.
- Pros: Correct per-FIFA bracket; produces calibrated p_champion/p_reach_stage probabilities; comparable to market odds
- Cons: 495-row static table must be embedded; cross-group 3rd-place ranking is complex
- Effort: High

### B. Simplified (group-only) Monte Carlo
Simulate groups only, probabilistically advance top-2 + 8 thirds, skip bracket fidelity.
- Pros: Simpler implementation
- Cons: No champion probability; can't compare to OUTRIGHT_WINNER odds; defeats the purpose
- Effort: Medium

### C. Bracket-from-live-data (skip simulation, use API results)
Once group stage is live, pull real results → simulate only remaining matches.
- Pros: Uses real data; lower variance
- Cons: Requires live ingestion working; misses pre-tournament opportunity
- Effort: Medium (but requires live ingestion already working)

---

## Recommendation

**Approach A** — full Monte Carlo. The 2026 WC is live (started today). The bracket rules are now completely documented with official source. The existing code has all primitives: Elo ratings, OLM `predict_proba`, `standings.py`. The main new work is: `montecarlo.py` core engine, the `standings.py` team_id exposure fix, Annex C lookup table, and the futures odds capture config.

---

## Risks

1. **Annex C lookup correctness:** The 495 rows were extracted from the official FIFA PDF via OCR/text extraction. Each row's qualifying groups can be computed from cell values, but off-by-one errors in the table are possible. MUST add a validation step: for each of the 495 rows, verify `len(set(cells)) == 8` and `all cells ∈ {3A..3L}`. Run this as a unit test.

2. **`standings.py` team_id gap:** The function must be updated to expose team_ids before Monte Carlo can link standings to Elo. Small change but blocks the cross-group 3rd-place ranking.

3. **OLM for knockout over-estimates favorites:** The draw renormalization approach slightly biases toward stronger teams. Acceptable for v1; document clearly.

4. **Futures odds credit budget:** 500 credits/month total. If already consuming 2 credits/snapshot for h2h+totals at 8h interval → 90 snapshots/month = 180 credits used. Futures adds 1 credit/snapshot → budget is fine, but must track with `sync_log`.

5. **Group advance odds not capturable via The Odds API free tier:** `GROUP_ADVANCE` market may not exist in the free key. BetPlay manual capture needed. This limits edge measurement for `p_advance_group`.

6. **Static Elo simplification:** In-tournament Elo updates could improve accuracy by round 2+ of group stage. Out of scope for v1 but document as known limitation.

7. **Fair-play tiebreaker missing:** When 3rd-place teams are tied after Pts/GD/GF, FIFA uses fair-play (cards), then FIFA ranking. We approximate with Elo for FIFA ranking but omit cards entirely. Edge case; document.

---

## Ready for Proposal

Yes — all critical unknowns resolved:
- Full R32 bracket structure confirmed (official source)
- Complete 495-row Annex C table extracted from official FIFA PDF
- DB has all data needed (groups, teams, Elo)
- Architecture fit is clear; `montecarlo.py` can be designed cleanly
- Futures odds endpoint is partially capturable (champion), with known limitations (group advance)

Next: propose module design + API endpoint for `/futures/probabilities`.

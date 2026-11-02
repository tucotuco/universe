# U-REL-001V7 — Historical reproduction profile decision brief

**Status:** exploratory evidence only. No historical probability or biological/calendar rule is adopted. `legacy/` was read as text/data only; no archived executable was run, modified, or staged. The explorer is independent of authoritative Universe generation.

## Evidence and source-path matrix

The 16 original offspring tables are UTF-8 CSV with exact `weight,value` headings. The table below reports the bytes' SHA-256, row/value coverage, total relative weight, and zero-weight rows. The value `0` is present in every table; a zero-weight row is not a sampleable value under ordinary weighted selection.

| Source path | Rows | Value range | Weight sum | Zero-weight rows | SHA-256 |
|---|---:|---:|---:|---:|---|
| `legacy/src/data/offspring_darkelf_wlist.csv` | 15 | 0–14 | 216 | 8 | `e0fabb178a4faa032f05f0243f82c057e92a428cffae63d59d7459ee38314b45` |
| `legacy/src/data/offspring_gnome_wlist.csv` | 15 | 0–14 | 186 | 6 | `2ad18fda37f6b9aa77259ef3d8ae9ffb2f6836b3883af14499ee9539df99da9e` |
| `legacy/src/data/offspring_greydwarf_wlist.csv` | 16 | 0–31 | 300 | 12 | `7013abb4b9946082ac64f374d88070d71903320dd5fa0d65d9f3442e13b42077` |
| `legacy/src/data/offspring_greyelf_wlist.csv` | 15 | 0–14 | 211 | 9 | `ed7198e38bb326500b8e04b1afbbd6ea94642eda55a7c4453121489dc4de9965` |
| `legacy/src/data/offspring_halfelf_wlist.csv` | 15 | 0–14 | 186 | 2 | `57c323966bf4a185f08fd4d6983d8c4fd9015fe061e8989d997679bff4aed838` |
| `legacy/src/data/offspring_halfling_wlist.csv` | 15 | 0–14 | 181 | 7 | `43c89c61a2b1cfef53053ae37519fffdcb17970a21051111a9cf2e2a23342ff8` |
| `legacy/src/data/offspring_halforc_wlist.csv` | 15 | 0–14 | 251 | 8 | `c4160f9c15fa7b3070befefbb833f182c4613b6b85d319d2ac80155f915b8e7c` |
| `legacy/src/data/offspring_highelf_wlist.csv` | 15 | 0–14 | 201 | 8 | `50bcff8bf934a0011e8b7f1f622b513138cc4ad1204d013177ccf448db057e08` |
| `legacy/src/data/offspring_hilldwarf_wlist.csv` | 15 | 0–14 | 181 | 5 | `c98d0a3e71b0eca788afde88296a97ff4b3ae1bda65867a4487e9afcd0370351` |
| `legacy/src/data/offspring_human_wlist.csv` | 15 | 0–14 | 848 | 0 | `9763d3587340c2b4acc475af7c23a960d49930e1c8e18878658f617876b221a7` |
| `legacy/src/data/offspring_merseian_wlist.csv` | 15 | 0–14 | 201 | 11 | `7c5d9ea8733cbc0673b006917293c7aeb5c96cd33aa1e167fe86b6e6435741b1` |
| `legacy/src/data/offspring_mountaindwarf_wlist.csv` | 15 | 0–14 | 189 | 5 | `eedbaa5c0889b90c97e2b6647e0946dac1a88d892e83cc4d2000049ae716e355` |
| `legacy/src/data/offspring_pteron_wlist.csv` | 15 | 0–14 | 211 | 11 | `188bfde26795930f90140a3b4153415601f5d3060b8336de22cb7cb65cfb64d9` |
| `legacy/src/data/offspring_svirfneblin_wlist.csv` | 15 | 0–14 | 230 | 11 | `addc42387b4d8625fb83098f943c7721a127bae8b9b5d174e659fdfbd399120a` |
| `legacy/src/data/offspring_wingedfolk_wlist.csv` | 15 | 0–14 | 186 | 5 | `73bd00f3816c6ecea5941ab9cc37318f71620623dc67e44e30e3067f33726809` |
| `legacy/src/data/offspring_woodelf_wlist.csv` | 15 | 0–14 | 211 | 8 | `17c26ff6151aaa7a5b1b022422ebd583b9b6a559d9219b40ad42ba4200a2497a` |


| Additional exact local path | Presence / SHA-256 | Source-grounded observation |
|---|---|---|
| `legacy/FAMTREE/FAMTREE.C` | `53b0d9a779a7ef5cd2efc27385024c59aebe48bdb6d2c70ed49a999f2b61596d` | C family-tree program; inline `kidchances` and `age_class` arrays, lazy family expansion on navigation; no reference to the offspring CSV files found. |
| `legacy/FAMTREE/LIFESPAN.C` | `a68bb92ea4eb9475777ffd8b19ad16f2f5654486842ece7d80b841810df680f5` | C lifespan sampling against age-stage values and a hardcoded survival-chance array; expects caller-provided ages. |
| `legacy/src/HISTORY.C` | `9309818cbacd6a07edcd09b1439bf6d953aa99680f4ae8e450b768e0c4e9d5c9` | Inline `kidchances[16][12]`; computes `resultcalc(roll(1,171), row) + 1`, followed by sibling/birth-date/survival construction. CSV table use is not present in this file. |
| `legacy/NPC/CHOOZ/HISTORY.C` | `9309818cbacd6a07edcd09b1439bf6d953aa99680f4ae8e450b768e0c4e9d5c9` | Byte-identical to `legacy/src/HISTORY.C`; same embedded count table. |
| `legacy/src/history.py` | `ABSENT` | ABSENT in this checkout. No checksum. |
| `legacy/src/utils_wlist.py` | `cc911c6614e167dbd55141decd8a2b745f850ce7971d9024078640775d5904b8` | Generic weighted CSV implementation. `get_random_item()` uses global `random.randint(1, weightsum)` and cumulative weights; no direct offspring-table reference found. |
| `legacy/src/utils_csv.py` | `dac9c0479d2d0f121c6d63ef91ba4738fe9999dcd7bd7f44b83ac85f93e27ee5` | CSV dialect/encoding/header/row helper used by the generic weighted-list loader. |
| `legacy/src/tester.py` | `d9273095d0aa57f4041c32b62f1abd6aebe7d03c509ae9759c83605cd0b42413` | A generic WeightedList test/reference; it does not establish the meaning of the offspring tables. |
| `legacy/src/longevity.py` | `16368c769bc63be30fc548db61fed082b822a29d005305d369a3b5fa2ffc1c9e` | Contains a `Life(WeightedList)` sketch and an unfinished `age()` implementation; file includes embedded C-like text and is not valid runnable Python. |
| `legacy/src/data/longevity_human_list.csv` | `aa6083c87deeb1a3e414938ac7971f669136bfdf19ca54f3af598be7e9dd89dd` | Human-labeled `weight,value` stages (young adult through ancient); distinct from offspring counts. |

The 16 `legacy/src/data/age_*_list.csv` files are also present. Each is 135 bytes, has SHA-256 `08ad64c758f0f2fdbc4ef2667a0fb1a3f3a8728a771d6359698e6798c0cf6ac3`, and uses `lifestage,value`; all 16 are byte-identical. Exact paths:
- `legacy/src/data/age_darkelf_list.csv`
- `legacy/src/data/age_gnome_list.csv`
- `legacy/src/data/age_greydwarf_list.csv`
- `legacy/src/data/age_greyelf_list.csv`
- `legacy/src/data/age_halfelf_list.csv`
- `legacy/src/data/age_halfling_list.csv`
- `legacy/src/data/age_halforc_list.csv`
- `legacy/src/data/age_highelf_list.csv`
- `legacy/src/data/age_hilldwarf_list.csv`
- `legacy/src/data/age_human_list.csv`
- `legacy/src/data/age_merseian_list.csv`
- `legacy/src/data/age_mountaindwarf_list.csv`
- `legacy/src/data/age_pteron_list.csv`
- `legacy/src/data/age_svirfneblin_list.csv`
- `legacy/src/data/age_wingedfolk_list.csv`
- `legacy/src/data/age_woodelf_list.csv`

## Statistical and units assessment

**Positively supported:** the offspring CSVs encode nonnegative integer `value` rows paired with nonnegative integer `weight` entries. The generic weighted-list helper treats weights as relative integer frequencies, samples a value by cumulative weight, and calls the resulting value an item. The selected tables differ: 15 have 15 rows over 0–14; `offspring_greydwarf_wlist.csv` has 16 rows over 0–31. Total weights range from 181 to 848. Every table includes a zero candidate value, and many include additional rows with zero weight.

**Not established:** the unit/population attached to each value, the sampling denominator or reference population, whether a count is lifetime children, children in one reproductive event, offspring of a parent set, births, surviving children, or family size; any calendar horizon; and whether all records represent the same setting or source population. The tables are not documented here as per-period fertility rates.

`legacy/FAMTREE/FAMTREE.C` independently embeds a 16-row count array and calls `resultcalc(roll(1,171), kidchances[race_index])`. `legacy/src/HISTORY.C` and its byte-identical CHOOZ copy contain a different 16-by-12 array and add one to the result. A local definition of `resultcalc` was not found in the inspected family sources, and no direct reference from these generators to `offspring_*_wlist.csv` was found. The table files therefore cannot be treated as the proven inputs to either generator. The historical arrays also disagree with the CSV distributions, which argues against silently substituting one for another.

Age and longevity resources cannot responsibly be combined with offspring weights now. FAMTREE embeds age classes and lifespan survival logic; the separate 16 CSV age files are byte-identical placeholders by content; the human longevity table is a separate stage-weight table; and `longevity.py` is unfinished/mixed-language. No validated common species mapping, time unit, population, or conditional sampling contract is established.

## Decisions requiring approval

1. **What population and provenance may an adopted source represent, and is its reuse authorized?** `U-ARC-001` remains open: source provenance/rights were not established by this exploration. **Default:** keep the tables local/read-only and experimental until provenance and permitted use are reviewed.
2. **What does each candidate count measure?** The files only prove weighted integer values. The C generators show family-sized counts but do not prove CSV linkage or CSV semantics. **Default:** retain “weighted candidate offspring-count value”; do not interpret as lifetime children, births, surviving offspring, or per-parent-set facts.
3. **What entity/scope is sampled and how many times?** A Being, exact reproductive parent set, family record, or a different unit is unresolved. **Default:** do not attach a draw to a Person/parent set or repeat it over simulation periods.
4. **What horizon and time basis apply?** No source-backed mapping to Universe periods or calendar ticks was found. **Default:** no date, age, fertility window, or per-period rate; preserve existing abstract test-only ticks only where that established test machinery is explicitly used.
5. **Should age/mortality tables condition offspring outcomes or materialized Being state?** Their formats and embedded source algorithms are distinct and not reconciled. **Default:** do not combine them; use no inferred survival, age, gender, or species properties.

## Recommended next executable target

After the decisions above, build one **explicit opt-in, source-identified statistical reproduction demonstration** using one approved table and the existing world publisher. Bind the selected source path, SHA-256, parser/sampler version, seed, requested scope, and interpretation to the request/result; preserve zero outcomes, exact-parent-set uniqueness, stable IDs, chronological constraints only if separately approved, deterministic retry, atomic publication, and Reality/Observation/Belief separation. Until semantic and provenance approval exists, the only safe path is continued read-only exploration or current test-only profiles.

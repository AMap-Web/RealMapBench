# Data Scope

This inventory describes the contents and scoring scope of
`realmapbench-v1-public-72-r2`.

## Inventory

The package contains 72 questions, 72 frozen reference answers, and 329
machine-readable criteria (263 required, 66 quality). The expected-answer
objects contain 294 numeric leaf values, including array elements. These are
field instances, including repeated counts, distances, areas, radii, ratios,
and candidate values; they are not 294 distinct observations or person records.
Numbers repeated in prose, criteria, and tolerances are not included in 294.

The following groups partition the 72 cases without overlap:

| Data group | Cases | Numeric expected fields | Membership | Notes |
| --- | ---: | ---: | --- | --- |
| Place addresses and administrative areas | 6 | 0 | PL-001 through PL-006 | Retains the place facts needed by each task. |
| Route and distance comparisons | 8 | 25 | All RD except RD-006 | Retains frozen distances and route scope. |
| Reachability geometry summaries | 2 | 8 | SA-001, SA-006 | Retain counts, directional distances, and areas; no coordinate arrays. |
| Chain-brand store and grid statistics | 10 | 31 | Listed below | Retains necessary per-brand values; speculative business commentary is removed. |
| Other POI, facility, business-category, and grid statistics | 46 | 230 | Other NS/BA/SA cases plus RD-006 | Retains necessary counts and definitions. |

Task taxonomy is unchanged: PL 6, NS 16, RD 9, BA 22, SA 19. RD-006 is counted
with facility statistics above because its route selection uses transit counts.
The chain-brand group means counts grouped by a named chain; other groups may
also mention individual businesses or landmarks.

The ten chain-brand cases are RMB-NS-001, RMB-NS-002, RMB-NS-004, RMB-NS-011,
RMB-NS-016, RMB-SA-009, RMB-SA-010, RMB-SA-014, RMB-SA-015, and RMB-SA-018.
They cover six coffee/tea chains. Counts and grid coverage are not revenue,
customer counts, customer demographics, or individual movement records.

All 26 MF questions, answers, and contracts remain withheld. No MF case IDs
or coordinate values are included in the dataset, truth sidecar, or manifest.
Public-place names and addresses still identify real entities; coordinate
redaction is not entity anonymization.

## Editorial Changes

The following 18 reference answers were minimized:

- NS-001, NS-002, NS-005, NS-006, NS-007, NS-009, NS-012.
- BA-001, BA-004, BA-006, BA-010, BA-011, BA-016, BA-017.
- SA-009, SA-015, SA-016, SA-018.

The cleanup removes operational narration, quota failures, internal tool and
rule identifiers, download offers, unnecessary record identifiers and detail,
unsupported commercial claims, and invitations to obtain audience profiles.
Necessary reference facts, deduplication definitions, circular-scope caveats,
and existing observation limitations are retained. It does not newly validate
POI identities, counts, or conditional reference values.

BA-010 no longer describes a count inside a 1 km radius as a per-square-km
density. BA-017 no longer infers increasing density or human movement from
counts in unequal-area regions. SA-009 no longer infers brand strategy from
store locations.

Five stale count titles are aligned with the already-existing numeric truth:
NS-012 restaurant 484 and tea house 50; BA-001 commercial areas 10; BA-004
commercial areas 7; BA-006 commercial areas 3. NS-012 category and deduplication
titles and BA-006 extraction wording are also aligned with their existing
scope. BA-017 drops unused `category`, `category_code`, and `poi_id` expected
metadata: the old narrow restaurant category conflicted with the broad-scope
question and answer, and no criterion referenced those three fields.

All question text, numeric expected values, criterion IDs, roles, operators,
weights, and tolerances remain unchanged. All other expected fields remain
unchanged. Reference-answer edits still change LLM judge inputs: re-evaluate
with this revision and do not claim equivalence to previous scores or to the
paper's 98-case results.

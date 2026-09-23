# Reproducibility Protocol

RealMapBench separates the public evaluation object from private agent
executions. The public release contains the questions, frozen truth snapshots,
rubrics, rubric contracts, scorer, and integrity manifest. It does not contain
the paper's agent outputs or execution traces.

## Public Subset and Paper Results

The paper uses the full 98-case research benchmark. The current public revision,
`realmapbench-v1-public-72-r2`, contains 72 cases; the remaining 26 Mobility and
Footfall cases are not included in this revision. The public subset keeps its
original case IDs and prompts but omits coordinate values from reference
answers and contracts. Five coordinate-dependent criteria are excluded from
`RMB-SA-011` and `RMB-SA-014`; their public contracts score counts only, not grid
locations or location-based tie completeness. This is a distinct evaluation
revision, not a reproduction of the paper's full experiment.

Compute new criterion verdicts against the published public contracts and use
72 as the full public-subset denominator. Do not change the denominator of a
paper result or reuse scores from a different contract revision. Even for the
retained cases, coordinate redaction changes the judge input, and the two
reduced contracts change what is scored. A later MF release must identify its
own case set, scoring scope, and revision.

The `realmapbench-v1-public-72-r2` editorial revision preserves all 72 questions,
numeric expected values, criterion IDs, roles, operators, weights, and
tolerances from `realmapbench-v1-public-72`. It minimizes 18 reference answers,
corrects conflicting rubric descriptions, and removes three unused expected
metadata fields from BA-017. These edits change the judge input; they do not
establish score equivalence or revalidate the underlying map observations.
Run the judge again and report the new revision rather than relabeling old
scores. The scope and changes are listed in [Data Scope](data-scope.md).

## Version Lock

A reported evaluation must identify the dataset revision, truth snapshot ID,
rubric-contract version, direct-scorer version, judge model, judge generation
settings, and final-attempt policy. The release manifest binds the public data
and scorer versions by hash.

## Scoring One Answer

Use `scripts/score.py prepare` with a case ID and final-answer file. The command
produces a vendor-neutral request containing the fixed judge system prompt,
question, frozen truth, rubric contract, and final answer. An optional
`--evidence-file` may provide a publication-safe JSON summary. Do not pass a
raw execution trace through this option.

Send the request's `system` and `prompt` fields to the recorded judge model,
then use `scripts/score.py aggregate` to validate and aggregate its criterion
verdicts. A case passes only if every required criterion passes. Mean Rubric
Score is the weighted mean across required and quality criteria.

## Aggregating A Run

Select one final attempt per case using a policy fixed before inspecting
scores. Preserve missing answers and technical judge failures as explicit
statuses rather than converting them silently into semantic failures. Compute
Strict Task Pass Rate over the declared benchmark denominator and separately
report scoring coverage.

LLM judge calls are not bitwise deterministic across providers or model
revisions. Exact result reproduction therefore requires preserving the judge
identity, request hash, and criterion-level verdict response. The public scorer
deterministically validates and reaggregates a preserved verdict response.

## Experiment Integrity

The agent execution environment must not be able to read benchmark truth,
rubrics, judge responses, prior result ledgers, or evaluator services. Skill and
no-skill conditions should use separate clean workspaces and an environment
variable allowlist. Access to evaluation-only assets is an integrity violation,
not evidence of task-solving ability: retain the original score for audit,
set the affected result's reported task pass to false, label the violation, and
perform a clean-room rerun. A case-level penalty is only a diagnostic
sensitivity policy; it does not make the contaminated run a valid comparison.

Raw traces can contain credentials, internal service locations, local paths,
and proprietary payloads. They require a separate sanitization process and are
not part of this release.

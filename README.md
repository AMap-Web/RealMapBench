# RealMapBench

RealMapBench evaluates tool-augmented agents on real-world map service tasks.
The paper reports experiments on the full 98-case research benchmark. This
repository currently provides an initial **72-case public subset**, revision
`realmapbench-v1-public-72-r2`, with reference answers, rubrics, and a scorer.

## Release Scope

**The 26 Mobility and Footfall (MF) cases are not included in the current
public release.** Their questions, reference answers, and rubric contracts are
withheld. They may be included in a future revision; no release date is
committed.

The paper's results refer to the full 98-case research benchmark. They are not
scores on this 72-case public subset, and the current public package does not
reproduce the paper's complete evaluation. Original case IDs and prompts are
retained for the 72 published cases.

Longitude and latitude values have been removed from the published reference
answers and rubric contracts. Five coordinate-dependent criteria have also
been removed: two quality criteria in `RMB-SA-011` and three required criteria
in `RMB-SA-014`. These two public contracts score the remaining numeric counts
only; grid identities, boundaries, locations, and location-based tie completeness
are not evaluated. The corresponding human-readable rubrics describe this
reduced scoring scope. This revision contains 329 criteria (263 required and
66 quality).

Report evaluations with this public revision and a 72-case denominator.
Scores must be computed with the published contracts; neither the paper's
aggregate scores nor its per-case scores can simply be relabeled as public
subset results. Any future additions or restored scoring criteria will be
published under a new revision.

中文说明：论文实验使用完整的98道题；本仓库当前公开其中72道题。
26道MF（人流与客流）题目及其答案、评分规则未纳入当前公开版本。
当前公开版本已移除参考答案和评分规则中的经纬度数值，并撤下SA-011、SA-014中依赖坐标的评分项。
因此，本公开子集及其评分范围与论文完整实验不同，不能直接用于复现论文的98题结果。

Revision `realmapbench-v1-public-72-r2` minimizes 18 reference answers and
corrects stale scoring descriptions without changing questions, numeric
expected values, criterion membership, weights, or tolerances. Reference text
is part of the judge input, so evaluations must identify this revision and
must not reuse verdicts from the earlier revision. See [Data Scope](docs/data-scope.md)
for the inventory and cleanup details.

## Release Contents

- `data/realmapbench-v1.json`: 72 questions with task annotations, rubrics, and
  rubric contracts.
- `data/realmapbench-v1.truth.json`: one reviewed frozen truth snapshot per
  question.
- `data/realmapbench-v1.manifest.json`: file, case, rubric, and truth hashes,
  plus scorer versions.
- `src/realmapbench/scoring/direct.py`: the direct scoring contract and score
  aggregation logic.
- `scripts/score.py`: a model-neutral interface for preparing judge requests
  and aggregating criterion verdicts.
- `scripts/validate.py`: release consistency validation.
- `docs/reproducibility.md`: the public scoring and experiment-integrity
  protocol.
- `docs/data-scope.md`: data inventory and publication scope.

No execution traces or experiment results are included in this repository.
They are outside the scope of the current public release.

## Tasks

The current public subset covers five task types and three difficulty levels.

| Task type | Code | Cases |
| --- | --- | ---: |
| Place lookup | PL | 6 |
| Nearby search | NS | 16 |
| Route and distance | RD | 9 |
| Business analysis | BA | 22 |
| Spatial analysis | SA | 19 |

Difficulty distribution: 24 simple, 43 medium, and 5 hard cases.

Public case IDs use the form `RMB-{task-type code}-{sequence}`, such as
`RMB-PL-001`.

## Data Contract

Each case contains a natural-language question, task annotations, a
human-readable rubric, a machine-readable rubric contract, and a reference to
its frozen public truth snapshot. The coordinate-redacted reference answers
are kept in the sidecar so they can be versioned independently. A rubric
contract may repeat only the expected fields needed to score its published
criteria. Coordinate redactions in narrative answers are explicitly marked.

```json
{
  "id": "RMB-PL-001",
  "prompt": "...",
  "metadata": {
    "task_type": "place_lookup",
    "difficulty": "simple"
  },
  "rubric": {
    "goal": "...",
    "criteria": []
  },
  "rubric_contract": {
    "version": "rubric_contract.v1",
    "pass_policy": "all_required",
    "score_policy": "weighted_mean",
    "criteria": [],
    "expected": {}
  },
  "truth": {
    "mode": "snapshot",
    "snapshot_id": "truth-realmapbench-v1-public-72-r2/RMB-PL-001"
  }
}
```

## Direct Scoring

The primary metric is `direct_task_pass`, implemented by
`rubric_contract_direct_v8`.

The scorer presents the question, frozen truth, complete rubric contract, the
agent's final answer, and optional publication-safe evidence to a
rubric-contract judge. Raw execution traces are neither required nor included
in this release. The judge must assign one `pass` or `fail` verdict to every
criterion. A case passes only when all required criteria pass. Quality criteria
contribute to the weighted score but cannot override a failed required
criterion.

Missing, incomplete, ambiguous, or unsupported claims fail the affected
criterion. Invalid contracts, unavailable truth, malformed judge responses,
and judge transport failures must be reported as scoring errors rather than
ordinary task failures.

The repository does not bind scoring to one model vendor. Prepare the complete
judge request, submit its `system` and `prompt` fields to the judge model, and
then aggregate the returned criterion verdicts:

```bash
uv sync

uv run python scripts/score.py prepare \
  --case-id RMB-PL-001 \
  --answer-file answer.txt \
  --output judge-request.json

uv run python scripts/score.py aggregate \
  --case-id RMB-PL-001 \
  --judge-response judge-response.json \
  --output score.json
```

The expected judge response is:

```json
{
  "criteria": [
    {
      "id": "required.example",
      "verdict": "pass",
      "reason": "brief reason",
      "evidence": ["short evidence from the final answer"]
    }
  ]
}
```

## Validation

Validate the published dataset, truth sidecar, rubrics, hashes, and scorer
versions:

```bash
uv run python scripts/validate.py
uv run pytest -q
```

After a data or truth update, rebuild the integrity manifest and validate
again:

```bash
uv run python scripts/build_manifest.py
uv run python scripts/validate.py
```

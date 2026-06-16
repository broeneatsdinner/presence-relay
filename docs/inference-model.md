# Inference Model

This document defines future contracts for baselines, correlation, confidence,
and compound-context inference. These contracts are roadmap-only and are not
implemented yet.

## Baselines

A route baseline summarizes completed comparable route sessions.

Comparable dimensions may include:

- `from_place`
- `to_place`
- route classification
- day of week
- time-of-day bucket
- daylight state
- season
- weather category
- optional event-context category

Prefer robust statistics over averages alone.

Potential baseline metrics:

| Field | Meaning |
| --- | --- |
| `sample_count` | Number of comparable completed sessions |
| `median_duration_seconds` | Robust central tendency |
| `mean_duration_seconds` | Average, useful but outlier-sensitive |
| `p25_duration_seconds` | Lower quartile |
| `p75_duration_seconds` | Upper quartile |
| `p90_duration_seconds` | High-end duration |
| `minimum_duration_seconds` | Fastest observed comparable session |
| `maximum_duration_seconds` | Slowest observed comparable session |
| `last_updated_at` | Last baseline update time |

Sparse-data rules:

- Require minimum sample thresholds before making strong claims.
- Treat tiny groups as exploratory only.
- Track outliers rather than deleting them silently.
- Age baselines as route behavior changes.
- Split baselines when route classification changes materially.
- Avoid overfitting by combining too many dimensions too early.

## Correlation Discipline

The system should distinguish:

- raw observation
- normalized context
- association/correlation
- hypothesis
- confidence
- recommendation
- causal conclusion

Future correlation results should structurally avoid causal claims.

Potential contract:

| Field | Meaning |
| --- | --- |
| `factor_type` | Context category, such as air-quality or venue-event |
| `factor_value` | Normalized factor value |
| `comparison_group` | Baseline group being compared |
| `baseline_sample_count` | Comparable sessions without factor |
| `affected_sample_count` | Comparable sessions with factor |
| `observed_difference_seconds` | Difference in duration metric |
| `effect_direction` | slower, faster, mixed, or none |
| `confidence` | low, moderate, high |
| `confidence_reason` | Public-safe explanation |
| `hypothesis` | Non-causal interpretation |
| `causality_claimed` | Always false for this contract |

Example discipline:

```text
Similar sessions during poor air quality were slightly slower.

Observed difference:
  +28 seconds median

Sample count:
  17 comparable sessions

Interpretation:
  correlation only

Confidence:
  low
```

Do not claim that a context factor caused behavior unless a separate, explicit
causal-analysis process exists. It does not exist in this roadmap.

## Compound-Context Inference

Multiple weak signals may combine into a meaningful operational deviation:

```text
light snow
+ evening darkness
+ nearby venue event
+ poor air quality
+ holiday schedule
= conditions different from the normal route baseline
```

Do not invent a machine-learning model in the contract. Start with explainable
rules and visible evidence.

Inference outputs should include:

- route key
- planned or evaluated departure time
- risk level, where risk means route/operational deviation, not danger by
  default
- confidence
- expected duration
- baseline duration
- visible reasons
- advisory recommendations
- an insufficient-evidence path

Recommendations should remain advisory.

Every reason should be visible so a human can inspect why the system reached a
conclusion. Contradictory factors should be shown rather than hidden.

## Red-Team-Relevant Framing

This project demonstrates authorized, privacy-aware operational reasoning:

- identifying weak signals
- recognizing changing baselines
- observing timing windows
- distinguishing evidence from assumption
- understanding friction, distraction, cover, and opportunity
- thinking across physical, human, network, and operational layers
- preserving authorization and minimizing impact
- explaining why a conclusion was reached

The same scheduled or environmental condition can create friction, distraction,
changed access patterns, or a temporary shift in normal behavior. In an
authorized security assessment, recognizing those changes can help an operator
choose appropriate test timing and interpret anomalous observations without
assuming causality.

The system analyzes the operator's own movement data and public contextual
information. It must not imply unauthorized surveillance, targeting uninvolved
people, exploiting health conditions, or causing public disruption.

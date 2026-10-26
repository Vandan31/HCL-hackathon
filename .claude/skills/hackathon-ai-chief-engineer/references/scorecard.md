# Opportunity and delivery scorecards

## Market opportunity score (0–5 for each; weight × score / 5)

| Dimension | Weight | High score means |
|---|---:|---|
| Magnitude + frequency of user pain | 20 | Repeated, concrete time/money/risk loss |
| Feasibility under the actual time/data budget | 20 | Core vertical slice can run today |
| Cost and operational efficiency | 15 | Small unit cost, straightforward deployment |
| Differentiation vs non-AI and existing tools | 10 | Useful advantage, not a generic chatbot |
| Measurable impact and evaluability | 10 | Testable outcome and baseline |
| Demo clarity / wow without fragile staging | 10 | Normal case and fallback can be shown live |
| Access and inclusivity | 10 | Language, low-bandwidth, accessibility addressed |
| Quality of supporting evidence | 5 | Primary/credible recent evidence available |
| **Total** | **100** | |

Give score, short reason, confidence (high/medium/low), and assumption that would overturn the recommendation. This is a prioritization heuristic, **not** a validated market forecast. Don't fake precision or use as proof of demand.

## AI technical acceptance table

For every AI feature, require: baseline, dataset/source, ground truth or human review, metric, target, test set, failure fallback, inference volume, rough unit cost, and owner. Example fields:
`feature | baseline | eval set | metric | target | failure policy | $/1k | owner`

## Claims protocol

- **Measured**: output of tests/profiling actually executed; state sample size/environment.
- **Sourced**: publicly or internally sourced claim; include source URL/title/date when available.
- **Estimated**: formula and explicit assumptions, sensitivity range.
- **Hypothesized**: plausible but unvalidated demand, pain point or impact.
Never call "estimated" figures "proven", and never compute precise ROI without baseline + input volume.

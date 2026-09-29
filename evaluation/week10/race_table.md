# Week 10 - Race Table

| Metric | single_agent | orchestrator |
|---|---:|---:|
| pass_rate | 80% | 80% |
| p50_latency_ms | 53.9 | 50.2 |
| p99_latency_ms | 84.5 | 80.5 |
| total_tokens | 2140 | 4340 |
| cost_per_question_usd | $0.000000 | $0.000000 |

Context re-send multiplier: **2.0x**

Largest hand-off: **substitution_worker -> orchestrator** = 1948 tokens (45% of all hand-off tokens)

All hand-off totals: {
  "orchestrator -> substitution_worker": 221,
  "substitution_worker -> orchestrator": 1948,
  "orchestrator -> allergen_worker": 65,
  "allergen_worker -> orchestrator": 175,
  "substitution_worker+allergen_worker -> synthesis": 1931
}

Same 10 Week-6 cases used (evals/week10_cases.py): ['S01', 'S03', 'S07', 'S08', 'S09', 'S13', 'S15', 'S21', 'S25', 'S26']

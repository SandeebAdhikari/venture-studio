# AI Venture Studio — Agents

## Overview

The intelligence layer combines **10 LangGraph LLM agents** with **2 deterministic engines** (scoring and executive ranking). All LLM agents share common patterns: service → graph → LLM client → validator → evidence persistence → budget guard.

```
Complaint evidence
       │
       ▼
┌──────────────────┐     ┌─────────────────────┐
│ Classification   │     │ Opportunity Gen     │
│ (LangGraph)      │────►│ (LangGraph + patterns)│
└──────────────────┘     └──────────┬──────────┘
                                    │
                                    ▼
                          ┌─────────────────────┐
                          │ Scoring Engine      │
                          │ (deterministic)     │
                          └──────────┬──────────┘
                                     │
       ┌─────────────────────────────┼─────────────────────────────┐
       ▼                             ▼                             ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  … (8 agents)
│ Market      │  │ Competitor  │  │ Customer    │
│ Research    │  │ Intelligence│  │ Research    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       └────────────────┼─────────────────┘
                        ▼
              ┌─────────────────────┐
              │ Executive Ranking   │
              │ (deterministic)     │
              └──────────┬──────────┘
                         ▼
              ┌─────────────────────┐
              │ Venture Report      │
              │ (template + LLM)    │
              └─────────────────────┘
```

---

## V1 Agents

### Classification Agent

| Attribute | Value |
|-----------|-------|
| Package | `app/agents/classification/` |
| Graph name | `classify_complaint` |
| Service | `ComplaintClassificationService` |
| Model | `CLASSIFICATION_MODEL` (default `gpt-4o-mini`) |
| Input | Pending `signals` |
| Output | `complaints` row or signal skip/fail |
| Pipeline stage | `CLASSIFY` |
| Worker job | `classify` |

**Graph flow:** extract → validate → persist

Extracts: category, domain, persona, severity, summary, verbatim quote, product mentions. Validates verbatim quote is substring of source text.

### Opportunity Generator Agent

| Attribute | Value |
|-----------|-------|
| Package | `app/agents/opportunity/` |
| Graph name | `generate_opportunity` |
| Service | `OpportunityGeneratorService` |
| Pattern detector | `TopicPatternDetector` (in-memory, not DB clusters) |
| Model | `GENERATION_MODEL` (default `gpt-4o-mini`) |
| Input | Unlinked complaints in rolling window |
| Output | `opportunities` + `opportunity_complaints` |
| Pipeline stage | `GENERATE_OPPORTUNITIES` |
| Worker job | `generate_opportunities` |

**Graph flow:** gather evidence → synthesize → validate → persist

---

## Deterministic Engines (No LLM)

### Opportunity Scoring Engine

| Attribute | Value |
|-----------|-------|
| Package | `app/scoring/` |
| Engine | `OpportunityScoringEngine` |
| Model ID | `scoring_engine_v1` |
| Service | `OpportunityScoringService` |
| Output | `opportunity_scores` (0–100 with dimension breakdown) |
| Pipeline stage | `SCORE_OPPORTUNITIES` |
| Worker job | `score` |

**Dimensions:** volume, severity, market_indicators, implementation_ease, founder_fit

Weighted combination produces integer score 0–100. Each rescore appends history; one `is_current=true` row per opportunity.

### Executive Ranking Engine

| Attribute | Value |
|-----------|-------|
| Package | `app/ranking/` |
| Engine | `ExecutiveRankingEngine` |
| Model ID | `executive_ranking_v1` |
| Service | `ExecutiveRankingService` |
| Input | Agent evaluation outputs per opportunity |
| Output | `executive_ranking_runs` + `executive_ranking_entries` |
| Pipeline stage | `EXECUTIVE_RANKING` |
| Worker job | `executive_ranking` |

**Components:** pain_score, market_score, revenue_score, competition_score, growth_score, founder_fit_score

Requires at least one agent evaluation (`agent_coverage_count > 0`). Creates approval request when founder approval enabled.

---

## V2 Research Agents

All research agents follow this structure:

```
app/agents/{name}/
├── graph.py          # LangGraph workflow
├── service.py        # Batch + single-opportunity orchestration
├── llm_client.py     # OpenAI structured output
├── mock_client.py    # Test doubles
├── validator.py      # Pydantic + business rules
├── schemas.py        # Agent-specific types
└── metrics.py        # Score computation helpers
```

Common API pattern per agent:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/{prefix}` | List evaluations/briefs |
| GET | `/{prefix}/{id}` | Get by ID |
| GET | `/{prefix}/opportunity/{opportunity_id}` | Get for opportunity |
| POST | `/{prefix}/generate` | Batch generate |
| POST | `/{prefix}/opportunity/{opportunity_id}/generate` | Single opportunity |

### Agent Reference

| Agent | Package | API prefix | Output table | Graph |
|-------|---------|------------|--------------|-------|
| Market Research | `market_research/` | `/market-research` | `market_briefs` | ✅ |
| Competitor Intelligence | `competitor_intelligence/` | `/competitor-intelligence` | `competitor_analyses` | ✅ |
| Customer Research | `customer_research/` | `/customer-research` | `customer_research` | ✅ |
| Revenue Validation | `revenue_validation/` | `/revenue-validation` | `revenue_validations` | ✅ |
| Product Strategy | `product_strategy/` | `/product-strategy` | `product_strategies` | ✅ |
| Go-To-Market | `go_to_market/` | `/go-to-market` | `gtm_plans` | ✅ |
| Growth Strategy | `growth_strategy/` | `/growth-strategy` | `growth_evaluations` | ✅ |
| Human Proxy | `human_proxy/` | `/human-proxy` | `human_proxy_evaluations` | ✅ |

Human Proxy additionally manages `founder_profiles` for founder-fit scoring context.

---

## Budget Guard

All LangGraph agents call `LLMBudgetService.try_prepare_call(graph_name, model)` before LLM invocation:

```python
# app/agents/classification/graph.py (pattern repeated in all graphs)
estimated_cost, block_reason = await self._budget.try_prepare_call(GRAPH_NAME, model)
if block_reason:
    raise BudgetExceededError(block_reason)
```

Shared utilities: `app/agents/budget_guard.py`, `app/agents/llm_cost.py`, `app/agents/eval_logging.py`

Budget API: `GET /api/v1/budget`, `GET /api/v1/budget/history`

---

## LLM Audit

Every LLM call logs to `llm_calls`:

- `graph_name`, `model`, token counts
- `estimated_cost_usd` (migration 019)
- `entity_type`, `entity_id` polymorphic reference
- `latency_ms`

---

## Testing

Each agent has dedicated tests under `api/tests/`:

| Agent | Test directory |
|-------|----------------|
| Classification | `tests/classification/` |
| Opportunity | `tests/opportunity/` |
| Scoring | `tests/scoring/` |
| Market research | `tests/market_research/` |
| Competitor intelligence | `tests/competitor_intelligence/` |
| Customer research | `tests/customer_research/` |
| Revenue validation | `tests/revenue_validation/` |
| Product strategy | `tests/product_strategy/` |
| Go-to-market | `tests/go_to_market/` |
| Growth strategy | `tests/growth_strategy/` |
| Human proxy | `tests/human_proxy/` |
| Executive ranking | `tests/ranking/` |
| Budget integration | `tests/budget/test_budget_agent_integration.py` |

Tests use mock LLM clients by default. Set `OPENAI_API_KEY` for live integration.

---

## Adding a New Agent

1. Create package under `app/agents/{name}/` following existing structure
2. Add ORM models + Alembic migration
3. Add repository and service to `ServiceContainer`
4. Add router in `app/api/v1/`
5. Register in `router.py`
6. Add `PipelineStage` enum value
7. Add stage execution in `PipelineStageExecutor`
8. Add job in `workers/jobs.py` STAGE_JOB_MAP
9. Wire budget guard in graph
10. Add tests

---

## Related Documentation

- [pipeline.md](./pipeline.md) — stage order and configuration
- [database.md](./database.md) — agent output tables
- [api-overview.md](./api-overview.md) — REST endpoints

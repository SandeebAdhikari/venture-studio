# AI Venture Studio — Vision

## Purpose

AI Venture Studio is a **continuous opportunity discovery system** for a solo founder. It ingests public signals from the internet, surfaces recurring complaints, clusters them into validated pain points, and generates ranked software business opportunities with enough context to decide what to build next.

Version 1 does not build products. It builds **decision-quality intelligence**: a steady stream of classified complaints and draft opportunity briefs that a human can review in under 30 minutes per day.

---

## Problem Statement

Solo founders waste time on:

- Manually scrolling Reddit, Hacker News, Twitter/X, Product Hunt, and review sites for ideas
- Chasing one-off anecdotes instead of recurring patterns
- Starting research from scratch for every promising thread
- Losing context when signals are scattered across bookmarks and notes

AI Venture Studio replaces ad-hoc browsing with a **repeatable pipeline** that collects, normalizes, classifies, and synthesizes signals into actionable opportunity records.

---

## Target User (V1)

| Attribute | Definition |
|-----------|------------|
| Primary user | Solo technical founder (you) |
| Time budget | 30–60 min/day for review; pipeline runs unattended |
| Decision output | "Which 1–3 opportunities deserve deeper manual research this week?" |
| Non-goals (V1) | Multi-user SaaS, automated MVP building, autonomous agent swarms |

---

## North Star (Full System — Aspirational)

The long-term system will:

1. Collect signals from the internet
2. Identify recurring pain points
3. Detect business opportunities
4. Research markets
5. Analyze competitors
6. Validate revenue potential
7. Create MVP plans
8. Create go-to-market plans
9. Rank opportunities
10. Present recommendations to a human

**Version 1 implements steps 1–3 only**, with lightweight ranking embedded in opportunity generation. Steps 4–10 are documented here for alignment but are explicitly out of scope until V2+.

---

## Version 1 Outcomes

By the end of V1, the system should reliably:

| Outcome | Success Criteria |
|---------|------------------|
| **Collect complaints** | Ingest 200+ raw signals/week from 3+ configured sources without manual copy-paste |
| **Classify complaints** | ≥85% of ingested items receive category, severity, persona, and domain tags with audit trail |
| **Generate opportunities** | Produce 5–15 opportunity briefs/week from clustered complaints, each linking back to source evidence |
| **Human review loop** | Founder can approve, reject, or defer opportunities from a single dashboard in <30 min |

---

## Core Concepts

### Signal
A single piece of raw content: a Reddit post, HN comment, G2 review snippet, etc. Immutable after ingestion except for enrichment metadata.

### Complaint
A structured extraction from a signal where a user expresses frustration, unmet need, or workaround behavior. One signal may yield zero or one complaint (V1 keeps this 1:1 for simplicity).

### Pain Point Cluster
A group of semantically similar complaints sharing domain, persona, and problem theme. Clusters are the input to opportunity generation.

### Opportunity
A synthesized business hypothesis: who hurts, what they need, why incumbents fail, and a draft wedge. Generated from a cluster, not from a single anecdote.

### Pipeline Run
A bounded execution of collect → classify → cluster → generate, tracked with status, timestamps, and error logs.

---

## Design Principles

1. **Evidence over eloquence** — Every opportunity must cite linked complaints and source URLs. No orphan claims.
2. **Batch over realtime** — Scheduled jobs (cron) beat streaming complexity for a solo founder.
3. **Human-in-the-loop by default** — AI proposes; the founder disposes. No auto-publishing or auto-building.
4. **Idempotent ingestion** — Re-running collection must not duplicate signals (`source + external_id` uniqueness).
5. **Observable failures** — Every stage logs to PostgreSQL; Redis is for queues and locks, not source of truth.
6. **Cheap to operate** — Target <$100/month infra + LLM at V1 scale (see MVP doc for limits).

---

## What V1 Is Not

- Not a market research platform (no TAM/SAM, no competitor deep-dives)
- Not an MVP builder or code generator
- Not a multi-tenant product
- Not a general-purpose web scraper (only whitelisted, ToS-respecting sources)
- Not an autonomous agent that takes external actions (post, email, deploy)

Future agents (market research, competitor analysis, revenue validation, MVP/GTM planning) will plug into the same `Opportunity` entity and pipeline orchestration layer designed in V1.

---

## Success Metrics (90-Day Horizon)

| Metric | Target |
|--------|--------|
| Pipeline uptime | ≥95% of scheduled runs complete without manual intervention |
| Signal freshness | Median age of unprocessed signals < 24 hours |
| Cluster quality | Founder rates ≥60% of generated opportunities as "worth considering" |
| Time saved | Founder stops manual signal hunting entirely |
| Cost per opportunity | < $2 LLM cost per generated opportunity brief |

---

## Technology Alignment

| Layer | Choice | Rationale |
|-------|--------|-----------|
| UI | Next.js (App Router) | Fast dashboard for solo founder; SSR for auth-ready pages later |
| API | FastAPI | Async Python ecosystem for LangGraph and data jobs |
| Database | PostgreSQL | Relational model for signals, lineage, and audit |
| Queue / cache | Redis | Job queues, rate-limit counters, distributed locks |
| Orchestration | LangGraph | Stateful multi-step LLM workflows with checkpoints |

---

## Document Map

| Document | Contents |
|----------|----------|
| [mvp.md](./mvp.md) | V1 scope, milestones, source list, LLM budget |
| [architecture.md](./architecture.md) | Services, deployment, API surface, LangGraph graphs |
| [database.md](./database.md) | Schema, indexes, migrations |
| [pipeline.md](./pipeline.md) | Stage definitions, schedules, error handling |

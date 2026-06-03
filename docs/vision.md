# AI Venture Studio — Vision

## Purpose

AI Venture Studio is a **continuous opportunity discovery and validation system** for a solo founder. It ingests public signals from the internet, surfaces recurring complaints, generates ranked software business opportunities, runs multi-agent research, and produces executive reports — with human approval gates before publication.

The system builds **decision-quality intelligence**: classified complaints, evidence-backed opportunity briefs, agent research artifacts, executive rankings, and venture recommendation reports that a founder can review in under 30 minutes per day.

---

## Problem Statement

Solo founders waste time on:

- Manually scrolling Reddit, RSS feeds, and forums for ideas
- Chasing one-off anecdotes instead of recurring patterns
- Starting research from scratch for every promising thread
- Losing context when signals are scattered across bookmarks and notes

AI Venture Studio replaces ad-hoc browsing with a **repeatable pipeline** that collects, normalizes, classifies, synthesizes, researches, ranks, and reports — orchestrated by FastAPI, ARQ workers, and a daily scheduler.

---

## Target User

| Attribute | Definition |
|-----------|------------|
| Primary user | Solo technical founder |
| Time budget | 30–60 min/day for review; pipeline runs on schedule |
| Decision output | "Which 1–3 opportunities deserve deeper manual action this week?" |
| Non-goals | Multi-user SaaS, automated MVP building, autonomous external actions |

---

## North Star Pipeline

The implemented system executes these stages (see [pipeline.md](./pipeline.md)):

1. **Collect** — ingest signals from Reddit and RSS sources
2. **Classify** — LLM extraction of structured complaints
3. **Generate opportunities** — pattern detection + LLM synthesis from complaint clusters
4. **Score** — deterministic 0–100 scoring from complaint evidence
5. **Research agents** — market, competitor, customer, revenue, product, GTM, growth, human proxy
6. **Executive ranking** — deterministic composite ranking from agent outputs
7. **Venture report** — executive recommendation markdown with founder approval workflow

Steps 1–7 are **implemented**. The founder dashboard (`web/`) surfaces opportunities, pipeline status, reports, approvals, budget, and agent activity.

---

## Core Concepts

### Signal
A single piece of raw content: a Reddit post/comment or RSS entry. Deduplicated by `(source_id, external_id)`, URL, and content hash.

### Complaint
A structured extraction from a signal where a user expresses frustration or unmet need. At most one complaint per signal (1:1).

### Opportunity
A synthesized business hypothesis generated from a recurring complaint pattern (topic cluster), linked to evidence complaints via `opportunity_complaints`.

### Agent Evaluation
Structured output from a V2 LangGraph agent (market brief, competitor analysis, etc.) stored per opportunity with evidence tables.

### Pipeline Run
A bounded execution of all 14 pipeline stages tracked in `pipeline_runs` and `pipeline_stage_runs`.

### Approval Request
Founder gate for executive rankings and venture reports when `REQUIRE_FOUNDER_APPROVAL=true` (default).

---

## Design Principles

1. **Evidence over eloquence** — Every opportunity and agent output must cite linked complaints and source URLs.
2. **Batch over realtime** — Scheduled jobs and ARQ workers beat streaming complexity for a solo founder.
3. **Human-in-the-loop by default** — AI proposes; the founder approves rankings and venture reports.
4. **Idempotent ingestion** — Re-running collection must not duplicate signals.
5. **Observable failures** — Pipeline, scheduler, and LLM audit trails in PostgreSQL; Redis for queues and locks.
6. **Budget-aware LLM usage** — Daily spend cap enforced before every agent LLM call.

---

## What the System Is Not

- Not an MVP builder or code generator
- Not a multi-tenant product (single shared API key auth)
- Not a general-purpose web scraper (only registered collectors: Reddit, RSS)
- Not fully autonomous in production (founder approval gates reports by default)

---

## Technology Alignment

| Layer | Choice | Rationale |
|-------|--------|-----------|
| UI | Next.js 15 (App Router) | Founder dashboard with BFF proxy |
| API | FastAPI | Async Python for LangGraph and data jobs |
| Database | PostgreSQL 16 + pgvector | Relational model, embeddings on complaints |
| Queue / cache | Redis | ARQ job queue, rate limits, distributed locks |
| Orchestration | LangGraph | Stateful multi-step LLM workflows |
| Scheduling | APScheduler | Daily cron slots enqueue ARQ jobs |
| Workers | ARQ | Background pipeline stage execution |

---

## Document Map

| Document | Contents |
|----------|----------|
| [mvp.md](./mvp.md) | Implemented scope, milestones, source list |
| [architecture.md](./architecture.md) | Services, deployment, API surface |
| [database.md](./database.md) | Schema, indexes, migrations |
| [pipeline.md](./pipeline.md) | Stage definitions and configuration |
| [pipeline-orchestration.md](./pipeline-orchestration.md) | Orchestrator, workers, scheduler integration |
| [agents.md](./agents.md) | LangGraph agents and ranking engine |
| [workers.md](./workers.md) | ARQ job system |
| [scheduler.md](./scheduler.md) | APScheduler daily jobs |
| [dashboard.md](./dashboard.md) | Founder dashboard |
| [operations.md](./operations.md) | Running, monitoring, recovery |
| [deployment.md](./deployment.md) | Docker and production deployment |
| [api-overview.md](./api-overview.md) | REST API reference |
| [ci.md](./ci.md) | GitHub Actions workflows |

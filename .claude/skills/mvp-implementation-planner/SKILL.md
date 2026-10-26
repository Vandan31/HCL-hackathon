---
name: mvp-implementation-planner
description: Scope and implement a testable AI hackathon MVP with a vertical-slice roadmap, data/API contracts, modular repo layout, mock data, test cases, and fallback demo.
---
# MVP Implementation Planner

Act as a senior full-stack AI engineer who delivers an end-to-end working slice, not a slideware architecture.

- Inventory available time, team, budget, skills, data and existing repository. If repository access exists, inspect files first and respect present language/toolchain. Don't overwrite existing code blindly.
- Choose **one high-value story** with UI interaction → API → source of truth → inference (only if justified) → visible result. Design the smallest working version; identify fake external services as *mocks* and make the demo honest.
- Default to simple modular-monolith stack: FastAPI or Flask backend, SQLite initially/Postgres if necessary, HTML/React/Streamlit front end to team skill, validated Pydantic-style schemas where appropriate, Python pytest; prefer an existing stack over these defaults.
- Supply file tree and each module's responsibility: config and secrets, ingestion, domain logic, retrieval/model, validation, API, DB/storage, UI, evaluation and tests.
- Provide API contract with method, path, request JSON example, success response, 4xx/5xx failure example; include authentication/authorization and idempotent repeated actions if relevant.
- Establish fixture/sample data with source + license/privacy clarity. Never use private real-world data in demos without permission.
- Give test-first acceptance criteria and actual runnable commands: happy path, malformed input, permissions, empty corpus/no match, model timeout, low-confidence outcome, and model/API off. Add basic metrics for p95 latency and request cost when measurable.
- Allocate tasks to teammates: backbone/API, model/data, UX/demo, integration/test (combine assignments if team smaller). Estimate time boxes in portions of total available time, not invented promises.
- **Cut list:** no login unless needed, no mobile native app, no fine-tuning, no complex RAG or Kubernetes without evidence. Every nonessential feature requires a demonstrated benefit.
- For build execution: make code changes using available tools, execute tests, fix errors, and summarize changed files, test command/output, deployment and known gaps. If unable to execute, state that clearly.

## Output contract

`MVP goal → user story & acceptance tests → 2-tier features (must/cut) → repo tree → architecture and API → fixture/sample data → 6–10 engineering steps and owners → test matrix → deployment + offline-failure demo → next commands`.

## Scoping guardrail

If the project is demo-only, make one complete flow reliable. Prefer an accessible, simple UX and trustworthy outputs over artificially increasing the number of AI agents. Every user-facing asynchronous state needs a loading/error/uncertain result.

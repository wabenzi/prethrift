# ADR 0001: Platform Architecture Overview

Date: 2025-08-10
Status: Accepted

## Context
Prethrift ("Vintage Vault") is a fashion-focused discovery platform. The system ingests second-hand or long-tail apparel inventory, enriches it with structured ontology attributes and semantic embeddings, and serves personalized, explainable search results. We require: (1) resilience when external AI services are unavailable, (2) clear contracts for multiple frontends (web, iOS), (3) guardrails for ambiguous or off-topic user input, and (4) a path to evolve ranking without breaking existing clients.

## Decision
Adopt a modular FastAPI backend with hybrid search pipeline (ontology + embeddings + preference weighting) plus lightweight LLM assistance for clarification & description enrichment. Implement deterministic fallbacks (hash-based image features, heuristic off-topic / ambiguity detection) to keep baseline functionality operational offline or under API quota constraints. Expose OpenAPI spec to generate typed clients for TypeScript and Swift. Store domain logic (ontology classification, ranking) in dedicated services to enable future replacement or augmentation (e.g., vector DB, learned re-ranker) without public API churn.

## Architecture Summary
- API Layer: FastAPI routers (search, inventory, ingest, user_profile, feedback) compose a single app.
- Domain Services: Ontology extraction, ranking pipeline, preference blending, image feature generation.
- Data Layer: SQLAlchemy ORM for garments, images, attributes, user preferences, interaction events.
- AI/ML Layer: Text embeddings (OpenAI) + deterministic image feature hash (pluggable), optional LLM calls for description & clarification.
- Guardrails: Heuristics for ambiguity and off-topic (with user force override except for disallowed content categories to be added later).
- Tooling: Pre-commit (Ruff, mypy), OpenAPI generation & drift check, pytest suites for edge cases.

## Rationale
- Explainability: Ontology & attribute overlap produce interpretable signals to supplement black-box embeddings.
- Robustness: Deterministic fallbacks avoid hard downtime when AI providers fail.
- Evolvability: Service boundaries allow incremental swap-in (e.g., CLIP vision encoder, FAISS vector index) behind stable interfaces.
- Safety & UX: Early input quality checks (ambiguity, off-topic) reduce irrelevant results and user frustration.

## Consequences
Positive:
- Clear layering shortens onboarding & testing cycles.
- Frontend type generation reduces integration bugs.
- Baseline search works in degraded AI mode.

Negative / Trade-offs:
- Additional complexity maintaining heuristics alongside ML components.
- Potential duplication (ontology extraction + embeddings) until a learned unifying model is introduced.
- Hash-based image features are low-fidelity; visual similarity limited until upgraded encoder integrated.

## Alternatives Considered
1. Pure embedding search (no ontology): Rejected due to poorer explainability & control.
2. Immediate vector DB adoption: Deferred; current scale manageable with in-memory / SQL plus future pluggable path.
3. Heavy moderation API dependency: Rejected for MVP; starting with lightweight heuristics keeps latency & cost low.

## Future Enhancements
- Pluggable vision encoder (CLIP / fashion-specific) & vector index.
- Learned re-ranker using gradient boosted trees with rich features.
- Multi-stage retrieval (sparse BM25 + dense fusion).
- Advanced moderation (tiered classifier, escalation workflow).
- Style profiling & clustering for personalization.
- Real-time metrics & observability (OpenTelemetry, Prometheus).

## Status Tracking
This ADR establishes the baseline architecture. Subsequent ADRs will cover: ranking evolution, moderation escalation, vector store adoption, and frontend contract versioning.

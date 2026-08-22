# ReconGuard Architecture Decisions

These decisions are locked for the MVP unless a genuine technical blocker appears.

| Layer | Decision |
|---|---|
| Backend | Python + FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy |
| Validation | Pydantic |
| Data Processing | Pandas |
| AI | Gemini API |
| Frontend | Streamlit |
| Testing | pytest |
| Containerization | Docker |

## Why These Choices?

### SQLite

SQLite keeps the MVP simple and requires zero database infrastructure. The workload is batch-oriented, and the database can be migrated to PostgreSQL later if required.

### Streamlit

Streamlit lets us prioritize the actual reconciliation workflow, exception investigation, policy decisions, and evaluation metrics instead of spending buildathon time building frontend infrastructure.

### Gemini

Gemini is the current AI provider for the MVP.

The AI layer will remain isolated behind an investigator interface so that the underlying model provider can be replaced without changing the reconciliation engine or policy engine.

## Core Architecture Decision

The AI does not directly authorize financial actions.

The AI:

1. Investigates the case.
2. Retrieves evidence through read-only tools.
3. Produces a structured recommendation.

The policy engine independently determines whether the recommendation is safe to execute or must be escalated.

This separation is a core safety requirement of ReconGuard.
# ReconGuard Architecture

## System Flow

```mermaid
flowchart TD
    A[Synthetic data generator] --> B[Deterministic matching engine]

    B -->|matched| G[Audit trail]

    B -->|ambiguous / unmatched / duplicate| C[Exception queue]

    C --> D[AI Investigator]

    D --> E[Policy engine - confidence + reversibility]

    E -->|safe| F[Auto-resolve]

    E -->|not safe| H[Escalate to human]

    F --> G
    H --> G

    G --> I[Evaluation engine]
    G --> J[Streamlit dashboard]
    
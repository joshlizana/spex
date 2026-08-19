# Use Focused Pipeline Components

Status: accepted

## Context and problem statement

Spex handles continuous ingestion, historical backfills, validation, transformation, analytical storage, operational control, and analytical presentation. These responsibilities have distinct lifecycles, scaling characteristics, and failure modes. The architecture needs clear ownership without fixing every responsibility to an independent deployment.

## Decision drivers

- Clear responsibility boundaries
- Independent live-ingestion and backfill lifecycles
- Measurable performance
- Operational simplicity
- Efficient resource use
- Focused testing and observability

## Considered options

- Focused logical components with flexible deployment boundaries
- Independently deployed microservices for every responsibility
- One application process with implicit internal boundaries

## Decision outcome

Chosen option: **Focused logical components within one application**.

Live ingestion, historical backfill, validation, and transformation remain distinct logical components. DuckLake provides the analytical data mart. Textual is the application control plane, and Streamlit provides the analytical interface. Every component is packaged as one application. Backfill, live ingestion, validation and transformation, Streamlit, and the Textual control plane run as five processes.

### Consequences

- Each component has a narrow purpose and explicit contract.
- Logical boundaries remain clear when responsibilities share a process.
- Live ingestion and backfill operate independently.
- One package contains every component.
- Multiple processes provide parallel execution.
- Validation and transformation share one process.
- Service contracts, supervision, observability, and failure handling require deliberate design.
- End-to-end testing covers both separated and combined deployments where applicable.

### Confirmation

Design reviews confirm that every component has one stated responsibility and explicit inputs and outputs. Performance and operational evidence supports each deployment boundary.

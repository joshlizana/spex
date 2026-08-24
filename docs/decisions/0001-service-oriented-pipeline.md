# Use Focused Pipeline Components

Status: superseded by [Consolidate Jetstream ingestion](0005-consolidated-jetstream-ingestion.md)

## Context and problem statement

Spex handles continuous ingestion, historical backfills, validation, transformation, analytical storage, operational control, and analytical presentation. These responsibilities have distinct lifecycles, scaling characteristics, and failure modes. The architecture needs clear ownership without fixing every responsibility to an independent deployment.

## Decision drivers

- Clear responsibility boundaries
- A lifecycle boundary aligned with the external protocol
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

Ingestion, validation, and transformation remain distinct logical components. DuckLake provides the analytical data mart. The Hub is the application orchestrator and control plane, Textual provides the operational interface, and Streamlit provides the analytical interface. Every component is packaged as one application. The Hub, Textual, ingestion, validation and transformation, and Streamlit run as five processes when every component is active.

### Consequences

- Each component has a narrow purpose and explicit contract.
- Logical boundaries remain clear when responsibilities share a process.
- Ingestion exposes replay and live as phases of one service.
- One package contains every component.
- Multiple processes provide parallel execution.
- Validation and transformation share one process.
- Service contracts, supervision, observability, and failure handling require deliberate design.
- End-to-end testing covers both separated and combined deployments where applicable.

### Confirmation

Design reviews confirm that every component has one stated responsibility and explicit inputs and outputs. Performance and operational evidence supports each deployment boundary.

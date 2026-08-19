# Project Collaboration Guide

This repository is a personal learning project owned and implemented by Joshua.

## Codex responsibilities

Codex serves as the project's documentation owner, research partner, and peer code reviewer.

- Proactively create and maintain documentation and other text files as the project changes.
- Research relevant topics, ideas, alternatives, and facts; distinguish verified facts from assumptions.
- Review code in depth for correctness, behavior, edge cases, structure, maintainability, conventions, style, and typographical errors.
- Report and discuss code-review findings without implementing fixes unless Joshua explicitly changes that boundary.
- Write and run tests only when explicitly asked.
- Do not write or modify application code. Joshua owns all application implementation.
- Preserve the project's learning value by explaining tradeoffs and helping Joshua reason through decisions.
- Maintain the repository lifecycle, including repository hygiene, intentional commits, branches, and GitHub pushes.
- Commit coherent project changes with concise messages.
- Push committed work to the configured GitHub remote.
- Keep application implementation ownership with Joshua while managing commits that include his code.

## Documentation conventions

- Keep prose succinct.
- Write in the present tense.
- Use affirmative phrasing.
- Make each document self-contained; omit comparisons to past states and context available only in conversations.
- Populate templates only with confirmed project information.
- Leave unknown sections explicit and bring them to Joshua for discussion.
- Do not invent requirements, decisions, rationale, constraints, interfaces, or verification plans to complete a template.
- Ask comprehensive related project questions in numbered groups so Joshua can reference each answer.
- Treat confirmed overarching processes as defaults for every component they govern; avoid relitigating resolved decisions through narrower follow-up questions.
- Ask for decisions that block architecture or near-term implementation; defer lower-level details to implementation, testing, or `docs/TODO.md`.
- Plan through progressive decomposition: settle system structure first, then component boundaries, interfaces, behaviors, and implementation details when implementation reaches them.
- Apply the standard retry policy to every retryable operation unless a documented decision defines an exception.
- Keep `README.md` aligned with the current user-facing state of the project.
- Track open documentation and project questions in `docs/TODO.md`.
- Record durable architectural or product decisions in `docs/decisions/`.
- Store research notes and source summaries in `docs/research/`.
- Store design specifications and explorations in `docs/design/`.
- Store substantial code-review reports in `docs/reviews/`.
- Use `docs/templates/adr.md` for architectural decision records.
- Use `docs/templates/tdd.md` for technical design documents.
- Use `docs/templates/research.md` for technical research.
- Use `docs/templates/review.md` for substantial code reviews.
- Maintain `CHANGELOG.md` in the Keep a Changelog 2.0 format.
- Update existing documents when facts change rather than leaving contradictory guidance.
- Clearly label proposals, unresolved questions, and unverified assumptions.

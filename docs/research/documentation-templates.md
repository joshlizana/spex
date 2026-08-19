# Documentation Template Selection

Research date: 2026-08-18

## Goal

Select concise, durable templates for Spex architectural decisions, technical designs, technical research, code reviews, and notable changes.

## Method

Review established public templates and engineering guidance. Prefer primary sources maintained by the template authors or engineering organizations. Select formats that preserve rationale, evidence, and actionable outcomes with limited process overhead.

## Evidence

### MADR structures architectural decisions around rationale

MADR 4.0 provides minimal and full Markdown templates. Its structure captures the problem, drivers, considered options, outcome, consequences, and confirmation.

Source: [Markdown Architectural Decision Records](https://adr.github.io/madr/)

### The Polotek template keeps technical designs compact

The template covers stakeholders, problem statement, goals, non-goals, design, API, dependencies, and functional, performance, and scale testing.

Source: [Design Doc Template](https://gist.github.com/polotek/a51449c4cc5d7d5ebfba033abc1c2cab)

### Keep a Changelog separates notable changes by reader impact

Keep a Changelog 2.0 uses an `Unreleased` section and six change types: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, and `Security`. Its guidance favors curated project changes over commit history.

Source: [Keep a Changelog 2.0](https://keepachangelog.com/en/2.0.0/)

### Microsoft Technical Spike organizes focused engineering research

The Microsoft Engineering Fundamentals Playbook template uses goal, method, evidence, conclusions, and next steps. This structure connects a research question to sourced evidence and a project action.

Source: [Template: Technical Spike](https://microsoft.github.io/code-with-engineering-playbook/design/design-reviews/recipes/templates/template-technical-spike/)

### Google and GitLab provide complementary code-review guidance

Google's review guide covers design, functionality, complexity, tests, naming, comments, style, documentation, and line-level review. GitLab's application-security review format adds concise findings, explicit severity, detailed evidence, and a conclusion.

Sources: [Google: What to look for in a code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html), [GitLab: AppSec review template process](https://handbook.gitlab.com/handbook/security/product-security/security-platforms-architecture/application-security/runbooks/review-process/)

## Conclusions

- Spex uses an adapted MADR 4.0 minimal template for ADRs.
- Spex uses an adapted Polotek design-doc template for TDDs.
- Spex uses Keep a Changelog 2.0 with Semantic Versioning.
- Spex uses an adapted Microsoft Technical Spike template for research.
- Spex uses an adapted Google and GitLab format for code-review reports.

The selected formats provide consistent questions, traceable evidence, and concise outcomes for a personal learning project.

## Next steps

- Apply each template to new documents of its type.
- Refine a template when repeated use exposes missing or unnecessary sections.

## Sources

- [Markdown Architectural Decision Records](https://adr.github.io/madr/)
- [Design Doc Template](https://gist.github.com/polotek/a51449c4cc5d7d5ebfba033abc1c2cab)
- [Keep a Changelog 2.0](https://keepachangelog.com/en/2.0.0/)
- [Microsoft Template: Technical Spike](https://microsoft.github.io/code-with-engineering-playbook/design/design-reviews/recipes/templates/template-technical-spike/)
- [Google: What to look for in a code review](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
- [GitLab: AppSec review template process](https://handbook.gitlab.com/handbook/security/product-security/security-platforms-architecture/application-security/runbooks/review-process/)

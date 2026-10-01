---
name: spec-auditor
description: Adversarial fresh-context SPEC audit. Supply the SPEC path and factual context card, not author conversation history.
model: opus
effort: xhigh
tools: Read, Grep, Glob, Bash
---

Hand-written Claude Code projection; policy generation is not built.
Read `docs/REVIEW_PRACTICE.md`, then `docs/agents/spec-auditor.md` and follow that
canonical charter. Resolve paths from the supplied project root.

The model/effort fields preserve the source Claude definition's explicit
selection instead of inheriting the spawning seat's tier. Use only where that
selection is available and authorized by the project; see `docs/REVIEW_AGENTS.md`.

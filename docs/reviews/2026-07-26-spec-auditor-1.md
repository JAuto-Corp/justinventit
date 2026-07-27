# Spec-auditor pass 1 (fresh-context, opus) — verdict

VERDICT: DISPATCH WITH FIXES. 1 blocker, 5 majors, 4 minors + a CHECKED-CLEAN list
(independently confirms: all cited Codex 0.145 surfaces real; profile-file layering
semantics; role-launch two-tier hardcode; .id supersession; Quick-RED exemption coherence;
no phase: remnants post-R2).

1 BLOCKER: HUB §6 "additive compound-keying" infeasible — orchestration_roles.letter char(1)
PK w/ 4 inbound FKs, threads.id slug PK w/ 4 more, views + RLS (migrations 20260517221227,
20260701221022); hub_id dedup needs NOT-NULL tighten over legacy NULLs. [CONVERGES with
auditor-2 M4 — dual independent confirmation.]
2 MAJOR: SEAT:150/TDD:129 cite "tracked in ROADMAP M3" — ROADMAP predates program, contains
neither; ARCH §9 is the real owner.
3 MAJOR: matrix self-contradiction — diagnostic thinking(xhigh) vs "high→xhigh" prose; high
absent from tiers; frontend raise_to:maint lowers the model while calling it a raise.
4 MAJOR: budget arithmetic fails on reference env — 28KB+4KB=32768 exactly; real global
4,771B ⇒ conforming repo refuses to launch. Budget 26-27KB / measured reserve.
5 MAJOR: JAuto ALREADY has AGENTS.md files as SKILL PAYLOADS (.agents/skills/
vercel-react-best-practices/AGENTS.md = 81,716B — 2.5× ceiling); native nested discovery
makes them entry context; per-directory budget check reds day one. Exclusion rule required.
6 MAJOR: three decision tables lack no-match branches — classifier (red-but-still-failing),
exit-code space (2/127 unspecified in the fail-loud contract itself), composer
(region-absent-locally / new-upstream / removed-upstream).
7 MINOR: registry relocation moves a path read by SEVEN live sites with no migration section.
8 MINOR: letter-case invariant unowned (lowercase files vs uppercase DB CHECK).
9 MINOR: TDD §4 autopsy mischaracterizes #3225 — AM-on-impl was the deliberate remedy;
residual defect is A-only TEST detection. Reword, don't revert a ruling.
10 MINOR: fixtures assert per-runtime visibility, not cross-runtime EQUIVALENCE — the
contract's actual premise untested.

DISPOSITION: all 10 addressed in R3 (same-day) together with auditor-2's 4 blockers +
8 majors. See the R3 section of 2026-07-26-specset-dispositions.md.

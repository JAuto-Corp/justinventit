# justinventit — Development Guide

## Codebase Map

```
template/                  Copier template (what gets scaffolded into projects)
  .claude/
    commands/              Slash-command wrappers (bare front doors + namespaced sub-verbs)
    skills/orchestrators/  Framework skills (work, verify, capture, scope, check, team-lead, etc.)
    hooks/                 Hook scripts (session-start, stop pipeline, guards)
    settings.json.jinja    Generated .claude/settings.json (hook wiring, matchers)
  context/                 State file templates
  docs/                    Doc templates (PLAYBOOK, CURRENT_WORK, etc.)
  scripts/                 Utility script templates
  CLAUDE.md.jinja          Main CLAUDE.md template

docs/                      Framework documentation
copier.yml                 Copier questionnaire + config
```

**This repo IS the framework.** The `template/` directory is what Copier copies into target projects. Everything outside `template/` is framework documentation and Copier config.

**Reference implementation**: [JAuto-Corp/customer-portal](https://github.com/JAuto-Corp/customer-portal) — the source codebase this framework was extracted from.

## Before Working

1. Read `docs/ROADMAP.md` — find the next unchecked item in the current milestone
2. Read `context/WORKING.md` — check the last observation block for session context
3. Read `docs/DOGFOODING.md` — understand the bootstrap development workflow

## Development Protocol

1. Changes to `template/` affect all projects on next `copier update`
2. Test changes by running `copier copy . /tmp/test-project` and verifying the output
3. Keep CLAUDE.md.jinja under 200 lines (hard limit for agent adherence)
4. Skills are lazy-loaded — only `name` + `description` in frontmatter matter at startup
5. Hook checks must be individually testable (exit 0 = pass, exit 1 = block)

## Conventions

- Jinja2 templates use `.jinja` extension
- Framework content uses `<!-- forge:start -->` / `<!-- forge:end -->` markers in generated files
- Hook scripts follow the check pipeline pattern (see `template/.claude/hooks/stop/`)
- State files use append-only observation block format

## Key Commands

```bash
# Test template generation
copier copy . /tmp/test-project --defaults

# Test with specific answers
copier copy . /tmp/test-project -d stack=nextjs -d database=supabase

# Generate + coherence gate across the answer matrix (also runs the generated
# project's hook harness and the real Stop runner — this is the hook validation)
scripts/ci/generate-matrix-check.sh [path/to/copier]
```

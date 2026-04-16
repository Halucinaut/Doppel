# Contributing to Doppel

Thanks for your interest in contributing to Doppel.

## Scope

Doppel is currently in an early MVP stage. The repository is open, but the interfaces, configuration schema, runtime behavior, and reporting format are still evolving. Small, well-scoped contributions are the easiest to review and merge.

Good contribution areas include:

- bug fixes
- test coverage improvements
- configuration validation improvements
- reporting and artifact quality improvements
- documentation fixes
- new example fixtures and scenario templates

## Before You Start

Please open an issue or start a discussion before sending a large change. This is especially important for new runtime behavior, judge logic, configuration schema changes, or anything that changes the project direction.

For small fixes, direct pull requests are fine.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

If you are working on the real browser path, you may also need Playwright and local browser binaries available under `.playwright-browsers`.

## Project Shape

The current repository is organized around a simple pipeline:

1. `config`: load and normalize `product.yaml`, `skill.yaml`, and `personas.yaml`
2. `sandbox`: prepare a repeatable runtime context
3. `runtime`: execute the synthetic user loop
4. `session`: persist artifacts and evidence
5. `judge`: extract facts and evaluate criteria
6. `reporting`: build Markdown and JSON outputs

Contributions should preserve this separation unless there is a strong reason to change it.

## Contribution Guidelines

- Keep changes focused. Avoid mixing refactors, new features, and unrelated cleanup in one pull request.
- Preserve the current product direction: experiential testing, synthetic users, evidence-first reporting, sandbox-aware execution.
- Add or update tests when behavior changes.
- Keep documentation aligned with actual repository behavior. Do not describe features that do not exist yet.
- Avoid introducing unnecessary dependencies.
- Prefer explicit, readable code over clever abstractions.

## Pull Request Checklist

Before opening a pull request, make sure that:

- the change has a clear purpose
- tests pass locally, or any skipped coverage is explained
- documentation is updated when user-facing behavior changes
- example configs are updated when schema changes
- unrelated generated files and local artifacts are not included

## Reporting Issues

When reporting a bug, include:

- the command you ran
- the config files involved
- the expected behavior
- the actual behavior
- logs or artifact snippets if relevant

For browser-related issues, also include whether you used `capture-only`, `browser-use`, or Playwright-backed execution.

## License

By contributing to this repository, you agree that your contributions will be licensed under the MIT License in this repository.

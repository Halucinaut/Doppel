# Roadmap Issues

下面是 v0.1.0 收尾后建议补到 GitHub 的 roadmap issues。本机当前没有可用的 GitHub CLI 或 GitHub 写入凭证，因此先以可复制文本固化在仓库内。

## 1. Runtime guardrail for browser-use actions

Strengthen runtime-level guardrails beyond prompt instructions. Scope: force entry URL when page is blank, block unsupported actions, detect repeated waits, detect impossible element indexes, and add deterministic stop suggestions when mission evidence is sufficient.

## 2. Batch run group and retry visibility

Make batch runs a first-class run group. Scope: stable group ID, per-persona attempt history, final-attempt selection, retry reason summary, and clean output directory naming without leaking failed intermediate attempts into curated reports.

## 3. Evidence quality for click targets and page text

Improve evidence extraction for click targets, visible text, accessible names, placeholders, button labels and page snapshots. Scope: reduce `click: {"index": n}` fallbacks and link every primary-action judgement to a human-readable target.

## 4. First-screen snapshot and content readiness

Add a deterministic first-screen evidence layer. Scope: capture the first non-empty screenshot, visible text summary, viewport metadata and page readiness timing before agent decisions start influencing the path.

## 5. CI integration

Add GitHub Actions examples for running `doppel validate`, smoke tests and selected browser-use evaluations before release. Scope: safe secret handling, artifact upload and failure summary comments.

## 6. Judge skill package format

Move beyond single YAML skill files. Scope: directory-based judge skill packages, shared criteria templates, persona-specific overrides and reusable domain packs.

## 7. Sample matrix

Expand official samples beyond `ai-bot.cn`. Scope: SaaS landing page, documentation site, logged-in workflow, local preview app and failure-case page. Each sample should include product config, personas, skills, commands and curated artifacts.

## 8. Report comparison

Support comparing reports across versions or personas. Scope: highlight changed criteria, new friction points, step-count deltas, screenshot diffs and trust-signal changes.

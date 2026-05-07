# Doppel 项目进展说明

更新时间：2026-05-06

## 1. 当前项目定位

Doppel 是一个面向体验测试的 synthetic user runtime。它要解决的问题不是“功能是否存在”，而是“陌生用户第一次进入产品时，能否理解、找到路径并完成目标任务”。

当前代码库已经完成 MVP 主链路：从产品配置、persona、judge skill 到 sandbox 运行、session artifacts、facts、evaluation 和报告输出。现阶段更准确的状态是“体验评测流水线已闭合”，不是“完整产品已成熟”。

## 2. 核心痛点

AI 编程工具和低代码平台降低了产品构建成本，但没有同步降低体验验证成本。团队可以快速知道代码是否报错、接口是否返回、按钮是否响应，却很难高频判断真实用户第一次进入产品时会不会看懂页面、找到主入口、完成任务。

传统 E2E 测试验证的是预设脚本。脚本天然知道下一步要点哪里，真实用户并不知道。人工 UX 走查和用户访谈更接近真实体验，但成本高、周期长，不适合每次提交、每个预览环境、每次小版本发布都运行。

Doppel 的切入点是把体验预检工程化：让 synthetic users 在 sandbox 中执行 mission，记录行为证据，再由 judge agents 基于 criteria 评估体验质量。

## 3. 已落地能力

当前仓库已经支持这些能力：

1. CLI 入口：`doppel validate` 用于校验配置，`doppel run` 用于执行一次评测主链路。
2. 配置加载：支持 `product.yaml`、当前 YAML 形态的 judge skill、`personas.yaml`，并支持环境变量插值。
3. Sandbox 抽象：已经有 `RemoteUrlSandbox` 和 `LocalPreviewSandbox`，支持 reset hook 元数据。
4. Runtime 主链路：支持 `capture-only` scaffold 模式，支持 Playwright adapter，也接入了 `browser-use` 作为真实浏览器 agent 执行路径。
5. Session artifacts：能够输出 `session.json`、`run_meta.json`、`prompt_context.json`、截图路径和错误信息。
6. Judge 基础结构：已经拆出 `FactExtractor` 和 `CriteriaEvaluator`，能从 step 记录中提取基础 facts，并按 criteria 输出评估结果。
7. Report 输出：能够生成 `report.md` 和 `report.json`，包含 summary、outcome、friction points、criteria、facts 和 screenshots。
8. 样例配置：当前保留 `examples/basic` 和 `examples/example-domain` 两组 sample。

## 4. 多 Agent 核心逻辑流

Doppel 可以描述为一个面向体验评测的多 Agent 流水线。当前代码里部分角色已经以模块形式落地，后续会进一步显式 Agent 化。

1. `Planner Agent`：读取产品配置、persona、mission 和 judge skill，生成本次评测上下文。
2. `Synthetic User Agent`：进入 sandbox，以目标 persona 的视角浏览 Web 页面，执行观察、决策、点击、输入、滚动和停止判断。
3. `Observer Agent`：持续记录页面状态、截图、动作、路径、错误、停顿和停止原因，形成 session artifacts。
4. `Fact Extraction Agent`：从 artifacts 中抽取事实，例如 step count、screenshot count、last action、stop reason，以及后续会扩展的误点、回退、重复路径和卡顿证据。
5. `Judge Agent`：根据 judge skill 中的 criteria 评估任务完成度、路径效率、信息清晰度和体验摩擦。
6. `Report Agent`：将 facts 和 evaluations 组织成 Markdown 与 JSON，用于人工 review、版本对比或接入 CI/CD。

长链推理主要发生在两个位置：Synthetic User Agent 需要基于当前视觉状态和历史动作持续判断下一步；Judge Agent 需要把分散行为证据串成体验结论。当前实现已经有浏览器执行、facts、criteria、report 的模块边界，下一阶段重点是把这些边界升级成更强的多 Agent 协作机制。

## 5. Sample 验证结果

本次参考了当前仓库内的两个 sample：

1. `examples/basic`：虚构产品 `PodFlow`，mission 是首次进入后理解产品并识别主入口，criteria 包含 `path_efficiency` 和 `clarity`。
2. `examples/example-domain`：目标页面是 `https://example.com/`，mission 是理解页面用途和主链接作用，criteria 包含 `clarity` 和 `entry_point`。

本地执行结果如下：

```bash
python3 -m doppel.cli.main validate \
  --product examples/basic/product.yaml \
  --skill examples/basic/skill.yaml \
  --personas examples/basic/personas.yaml
```

结果：配置校验通过，product 为 `PodFlow`，persona 为 `newcomer`，judge skill 为 `首次发现`。

```bash
python3 -m doppel.cli.main validate \
  --product examples/example-domain/product.yaml \
  --skill examples/example-domain/skill.yaml \
  --personas examples/example-domain/personas.yaml
```

结果：配置校验通过，product 为 `Example Domain`，persona 为 `newcomer`，judge skill 为 `落地页理解`。

```bash
python3 -m doppel.cli.main run \
  --product examples/example-domain/product.yaml \
  --skill examples/example-domain/skill.yaml \
  --personas examples/example-domain/personas.yaml
```

结果：生成一次 run，`run_id` 为 `a2fe35c4f975`，mode 为 `remote`，step count 为 `1`，stop reason 为 `capture_only`，报告路径为 `examples/example-domain/output/a2fe35c4f975/report.md`。

这次 sample run 证明了主链路已经能从配置进入运行、记录 session、提取 facts、生成 evaluation 和 report。它没有证明完整浏览智能已经成熟，因为默认执行路径是 `capture-only`，只完成初始视口捕获和 scaffold 报告生成。

## 6. 当前版本边界

当前版本的主要边界如下：

1. 默认模式是 `capture-only`，更适合验证主链路和 artifacts，不等同于完整 synthetic user 浏览任务。
2. `browser-use` 路径已经接入，但依赖可用的模型 API key、浏览器资源和运行环境。
3. Judge 仍是规则驱动基础版本，当前 facts 主要覆盖 step count、stop reason、screenshot count 和 last action。
4. Report 已经结构化，但分析深度依赖 judge 能力，当前更偏 MVP 证据汇总。
5. 当前 judge skill 仍以单个 YAML 文件承载，后续应扩展为可组合的目录或 skill 包。

## 7. 下一阶段方向

建议下一阶段按能力推进：

1. 强化 Synthetic User Agent：让默认路径从 `capture-only` 走向可持续浏览、决策和任务推进。
2. 强化 Judge Agent：从规则判断升级为证据驱动评估，支持误点、反复跳转、任务放弃、路径效率和信息清晰度分析。
3. 升级 judge skill：支持多文件目录、可复用 criteria、领域模板和组合式评测包。
4. 扩展 sandbox：支持账号隔离、seed data、reset hooks、版本对比和更稳定的复现机制。
5. 接入 CI/CD：支持在 pull request、preview deployment 和 release 前自动运行体验评测。
6. 扩展目标环境：从 Web 页面扩展到 macOS、Windows 桌面应用，以及虚拟机中的应用体验测试。

## 8. 结论

Doppel 当前已经完成从配置到报告的 MVP 骨架，能够用 sample 证明体验评测流水线闭合。下一阶段的关键不是继续堆文档，而是把 synthetic user 执行能力和 judge agent 评估能力做实，让报告从“主链路证据汇总”升级为“可用于发布判断的体验风险结论”。

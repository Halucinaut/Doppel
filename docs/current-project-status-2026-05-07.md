# Doppel 当前项目状态

状态日期：2026-05-07

当前状态：v0.1.0 MVP closed。

Doppel 已完成一个可演示、可验证、可上传的阶段性闭环。当前版本可以读取产品配置、persona 配置和 judge skill，启动 browser-use runtime 访问真实 Web 页面，记录 session artifacts，提取 facts，按 criteria 输出 evaluation，并生成 Markdown/JSON 报告。`ai-bot.cn` 已固定为 v0.1.0 的官方展示样例。

## 已完成闭环

v0.1.0 已支持 Web 页面体验测试、browser-use runtime、远程站点与本地预览、persona 配置、judge skill、facts 提取、criteria 评估、Markdown/JSON 报告、多 persona batch、runtime fallback 和点击目标标注。

当前 CLI 主入口包括三条命令：`doppel validate` 校验配置，`doppel run` 跑单 persona，`doppel batch` 跑多 persona 并生成横向汇总。

## 主示例

官方展示样例位于 `examples/ai-bot-cn`。该示例包含：

- `product.yaml`
- `personas.yaml`
- `skill.yaml`
- `skill-newcomer.yaml`
- `skill-designer.yaml`
- `skill-product-manager.yaml`
- `skill-privacy.yaml`
- `artifacts/v0.1.0`

`artifacts/v0.1.0/single-newcomer` 保存了单 persona 运行核心 artifacts，包括 `session.json`、`facts.json`、`evaluation.json`、`report.md`、`report.json` 和关键截图。`artifacts/v0.1.0/batch` 保存了 batch 汇总和四个 persona 的独立报告。

## 当前示例结论

`ai-bot.cn` batch 示例中，四个 persona 都以 `mission_completed` 结束。新手和产品经理识别并点击了搜索框，设计师点击了 AI 设计工具，谨慎用户通过关于我们路径寻找信任信息。

报告暴露出的主要体验问题是：首屏产品定位仍不够直接，部分角色没有触发滚动发现，信任信号在不同路径下暴露不稳定，模型偶发 JSON 格式错误和超时。Doppel 能把这些问题落到步骤、facts、截图和评估结论中，而不是只给出“任务完成”。

## 已知限制

当前限制主要在运行稳定性和证据质量。多模态模型仍可能输出无效 JSON、超时或重复行动；browser-use 的元素编号会受页面动态变化影响；facts 提取仍以启发式规则为主；桌面应用、虚拟机运行、CI/CD、历史版本对比和 judge skill package 尚未实现。

这些限制不阻碍 v0.1.0 MVP 结项。它们属于后续从“可演示闭环”走向“稳定可用工具”的路线。

## 结项判断

v0.1.0 可以阶段性结项，并可以宣布 MVP 阶段成功。项目已经证明 synthetic user 体验评测流水线可行，能在真实 Web 页面上产出多 persona、证据驱动的评测报告。

下一阶段目标不应继续扩大 MVP 范围，而应围绕 runtime guardrail、batch run group、evidence quality、first-screen snapshot、CI integration、judge skill package、sample matrix 和 report comparison 做稳定化。

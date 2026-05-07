<p align="center">
  <img src="./assets/doppel-pixel-logo.svg" alt="Doppel pixel logo" width="320" />
</p>

# Doppel

Synthetic user runtime for experiential testing.

## 简介

Doppel 用 synthetic user 运行一次真实的产品体验路径，回答传统测试很难覆盖的问题：第一次进入产品的用户能否理解它、找到主要入口，并在关键路径上继续行动。

当前版本支持 Web 页面体验测试、远程站点或本地预览环境、persona 与 judge skill 配置、浏览器运行证据采集、facts 提取、criteria 评估、单次报告和多 persona 批量报告。它更适合体验预检和体验回归，不能替代单元测试、接口测试、安全审计或真实用户研究。

## 灵感来源

AI 降低了做产品原型的成本，但没有降低陌生用户理解产品的成本。很多项目上线前知道按钮能点、接口能通、路径能跑完，却不知道用户第一次看到页面时会不会理解主价值、会不会点击正确入口、会不会因为信息结构混乱而放弃。

Doppel 来自这个断层：功能测试验证预设路径，人工走查验证真实体验，中间缺少一层高频、低成本、可重复的体验验证。它先把一个可控的 synthetic user 放进产品，观察它如何理解、误点、滚动、等待、放弃或完成任务。

## 项目愿景

Doppel 的目标是把体验预检变成和单元测试、CI/CD 一样自然的工程动作。团队可以在发布前运行一组 persona，检查首屏理解、主要入口、滚动信息递进、路径效率和信任信号，并把报告作为版本迭代的体验证据。

长期方向是形成独立的体验验证基础设施：运行时 agent 负责观察和行动，judge 模块负责从 session artifacts 中提取事实并评估，sandbox 负责隔离与重置，报告层负责可归档、可比较、可接入流程的输出。

## 适合谁用

Doppel 适合独立开发者、早期团队、产品经理、设计师、增长团队，以及缺少专职质量保障和用户研究资源但需要频繁做体验预检的人。典型用法是给一个产品配置、一个 persona、一个 mission 和一组 judge criteria，让系统自动跑出证据链和评审报告。

Doppel 不适合用来确认选择器是否存在、接口是否返回 200、表单是否按固定步骤提交成功；这些属于 Playwright、Cypress、接口测试和单元测试的职责。它关注用户是否自然理解和行动。

## 工作原理

Doppel 的执行路径是：读取 `product.yaml`、`personas.yaml` 和 judge skill，生成规范化运行上下文；准备 sandbox，确定入口 URL、种子状态和重置策略；启动浏览器运行时，让 agent 按 persona 和 mission 执行观察、决策、行动；记录截图、页面状态、动作、推理摘要、错误和停止原因；从 `session.json` 提取 facts；按 judge criteria 生成 `evaluation.json`；最后输出 `report.md`、`report.json` 和批量运行汇总。

当前浏览器运行链路基于 browser-use。Doppel 在其上补了运行时模型配置、OpenAI 兼容供应商、失败重试、供应商轮转、结构化动作约束、中文中间过程、截图证据和点击目标标注。模型输出不稳定、目标网页加载超时、页面动态变化导致元素编号失效时，Doppel 会记录错误、冗余步骤和停止原因，报告会暴露这些摩擦。

## 与 Related Work 的差异

与 Playwright、Cypress 相比，Doppel 不要求用户提前写死操作序列；它让 synthetic user 根据页面可见信息自主选择路径，再评估这条路径是否清晰、高效、可信。

与通用 browser agent 和一次性网页探索工具相比，Doppel 的核心对象是可复用的产品配置、persona、judge skill、sandbox 和 artifacts。它输出结构化事实和评估结果，适合归档、复查、多角色对比和后续接入 CI/CD。

与人工可用性测试相比，Doppel 的价值是便宜、快、可高频运行；边界是无法替代真实用户访谈、长期行为观察、合规判断和高风险业务决策。

## Roadmap

| Version | Status | Supported or Completed | Planned Updates |
| --- | --- | --- | --- |
| 0.1.0 | Completed | Web 页面体验测试、browser-use 运行时、远程站点和本地预览、persona 配置、judge skill YAML、facts 提取、criteria 评估、Markdown 和 JSON 报告、多 persona 批量运行、运行时模型重试与轮转、点击目标标注 | 稳定 API、完善公开示例、整理包发布元数据 |
| 0.2.0 | Planned | 当前 Web 运行链路继续稳定 | 支持 judge skill 目录、可组合评测模板、更多内置 criteria、报告可视化增强 |
| 0.3.0 | Planned | 当前 sandbox 继续保留 | 强化隔离账号、种子数据、状态重置、版本对比和体验回归基线 |
| 0.4.0 | Planned | 当前 CLI 继续保留 | 接入 GitHub Actions 等 CI/CD 流程，在提交、部署或发布前自动运行体验评测 |
| Later | Planned | Web 产品体验测试 | 支持 macOS 和 Windows 应用，支持在虚拟机中运行目标应用，提供 API 和 Web UI |

## 配置与使用

当前项目使用 Python 3.11+。

```bash
git clone https://github.com/Halucinaut/Doppel
cd Doppel
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

如果要运行真实浏览器链路，需要安装 Playwright 浏览器资源。仓库默认支持从工作区 `.playwright-browsers` 读取浏览器。

最小配置包含三个文件：`product.yaml` 描述目标产品和 sandbox，`personas.yaml` 描述用户画像，judge skill 描述 mission、停止条件和评判标准。当前 judge skill 可以是一个 YAML 文件，后续会支持目录化 skill 包。

```yaml
name: "PodFlow"
entry_url: "https://example.com"
description: "A podcast listening and discovery platform"

sandbox:
  mode: "remote"
  seed_state: "new_user"
```

```yaml
name: "首次发现"
version: "1.0"
persona: "newcomer"

mission: |
  你第一次进入这个产品。
  请尝试理解它是做什么的，并识别主要入口。

stop_conditions:
  - "你已经理解主要行动入口"
  - "你会选择离开这个产品"

judge_criteria:
  - id: "path_efficiency"
    question: "用户找到主要行动入口的路径是否直接？"
    good: "用户很快找到了入口"
    bad: "用户用了太多步骤，或路径不清晰"
```

校验配置：

```bash
doppel validate \
  --product examples/basic/product.yaml \
  --skill examples/basic/skill.yaml \
  --personas examples/basic/personas.yaml
```

运行单个 judge skill：

```bash
doppel run \
  --product examples/basic/product.yaml \
  --skill examples/basic/skill.yaml \
  --personas examples/basic/personas.yaml
```

使用 OpenAI 兼容模型时，创建本地 `runtime.local.yaml`，不要提交真实密钥：

```yaml
provider: "openai-compatible"
api_key: "${DOPPEL_RUNTIME_API_KEY}"
base_url: "https://open.bigmodel.cn/api/paas/v4"
runtime_model: "glm-4.6v-flash"
fallback_providers:
  - provider: "openai-compatible"
    api_key: "${DOPPEL_RUNTIME_FALLBACK_API_KEY}"
    base_url: "https://integrate.api.nvidia.com/v1"
    runtime_model: "moonshotai/kimi-k2.6"
```

运行多 persona 批量评测：

```bash
doppel batch \
  --product examples/ai-bot-cn/product.yaml \
  --skill-dir examples/ai-bot-cn \
  --personas examples/ai-bot-cn/personas.yaml \
  --runtime-config runtime.local.yaml \
  --decision-provider browser-use \
  --retries 1
```

运行完成后，输出目录包含 `session.json`、`run_meta.json`、`prompt_context.json`、`facts.json`、`evaluation.json`、`report.md`、`report.json`、`screenshots/`。批量运行会额外生成 `batch_report.md` 和 `batch_summary.json`。

## License

当前仓库采用 MIT License，具体条款见根目录下的 `LICENSE` 文件。

Doppel 用于辅助体验预检，不构成质量、合规、安全、可访问性或业务结果保证。对受登录保护、含隐私数据或受合规约束的系统运行 Doppel 前，应先确认授权、隔离和数据处理边界。

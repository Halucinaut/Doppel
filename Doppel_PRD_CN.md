# Doppel

## Synthetic User Runtime 与 Sandbox 驱动的体验测试系统

### 产品需求文档 · v0.2 · MVP Reframed

**Your users, before your users.**


## 1. 产品定义

### 1.1 Doppel 是什么

Doppel 是一个开源、可扩展的 **Synthetic User Runtime**。它让 AI 代理以“第一次接触产品的真实用户”身份，进入一个目标产品，在尽量少的背景信息下完成指定任务，并输出基于行为证据的体验反馈。

Doppel 的目标不是回答“这个功能是否正常工作”，而是回答：

- 一个陌生人第一次来到这里，能不能理解这个产品？
- 他会不会在关键路径上迷路、犹豫、点错、放弃？
- 哪些页面、文案、交互会制造认知摩擦？

### 1.2 Doppel 不是什么

Doppel 不是下列工具的替代品：

- 不是单元测试或集成测试框架
- 不是安全扫描器
- 不是性能压测工具
- 不是 WCAG 合规审计器
- 不是自动修复代码的 coding agent
- 不是纯粹的“浏览器工作流录制器”

它工作的层次更高：**体验验证层**。

### 1.3 产品本体与产品入口

为了避免概念混淆，这里做严格区分：

- **产品本体**：Synthetic User Runtime + Sandbox + Judge System
- **产品入口**：CLI、未来的 Web UI、GitHub Action、API

MVP 阶段只交付 CLI，不代表 Doppel 是 CLI 产品；它只是最便宜、最快验证需求的入口。

---

## 2. 核心问题

### 2.1 我们要解决什么问题

AI 把“做出一个产品”的成本降得很低，却没有同步降低“判断这个产品是不是能被陌生人真正用起来”的成本。

今天的测试工具分别解决了不同层的问题：

- 单元测试验证代码逻辑
- 集成测试验证系统协作
- E2E 测试验证预定义路径是否可走通
- Lighthouse/可访问性工具验证静态规则

但仍然缺失一个问题的标准答案：

> 第一次来的用户，会不会看不懂、找不到、点不下去、或者直接流失？上新的一个功能，是不是真的满足了客户群的需求，有没有按照我们预期的去工作。以及最经典的case：“用户去酒吧点了一份蛋炒饭"

### 2.2 为什么现有工具不够

| 方案                  | 能做什么               | 做不到什么                         |
| --------------------- | ---------------------- | ---------------------------------- |
| Playwright / Cypress  | 验证功能路径是否可执行 | 不能判断体验是否自然、是否让人困惑 |
| QA 脚本               | 验证预期行为           | 无法模拟陌生用户的探索与误解       |
| UX 专家走查           | 能发现体验问题         | 慢、贵、主观、不易高频运行         |
| 用户访谈 / 可用性测试 | 最接近真实反馈         | 组织成本高，不适合每次迭代都做     |
| 静态分析工具          | 识别规则违反           | 不能模拟“用户正在迷失”的过程     |

### 2.3 Doppel 的切口

Doppel 试图填补的是中间这层空白：

**在真实用户到来之前，用合成用户高频、低成本、可追溯地暴露体验风险。**

---

## 3. 产品判断与原则

### 3.1 核心判断

我们对这个产品有四个核心判断：

1. 未来的大量产品会由少量人、借助 AI 快速生成。
2. 这类团队最缺的不是“构建能力”，而是“体验验证能力”。
3. 他们需要的不是昂贵的研究体系，而是一个足够诚实、足够快、可以反复跑的 synthetic user 系统。
4. Doppel 的价值不在于替代真实用户，而在于提前暴露明显问题，减少把有缺陷的体验直接交给真实用户的次数。

### 3.2 产品原则

#### 原则一：冷启动优先

Agent 只拿到最少产品语义信息，例如入口 URL 和一句描述。越少预先解释，越能验证产品本身是否自解释。

#### 原则二：视觉优先于 DOM

Doppel 对页面的理解应以视觉结果为主，而不是以 DOM 结构为主。

这意味着：

- agent 首先看到的是截图中的页面，而不是 HTML/CSS
- agent 判断“哪里能点、哪里像入口”时，应基于视觉线索
- 浏览器自动化层可以使用 DOM 或坐标完成执行，但不应让 DOM 决定 agent 的认知

这样做的原因是，Doppel 要测的是“用户会如何理解页面”，而不是“页面结构允许什么”。

例如：

- 一个元素在 DOM 中可点击，但视觉上不像按钮，用户不会点
- 一个元素视觉上像主按钮，但实际点击无效，用户会误判

#### 原则三：Sandbox 优先于 Workflow

Doppel 不应只是“调用浏览器点一遍”。它必须在可控环境中运行，使测试可以隔离、重置、重复和比较。CLI 只是触发器，sandbox 才是测试基础设施。

#### 原则四：证据优先于观点

报告中的结论必须绑定具体行为证据，例如：

- 第 4 步停留 12 秒
- 在同一页面来回跳转 3 次
- 点击错误按钮 2 次后才找到主路径

没有证据的主观描述不构成 Doppel 的核心价值。

#### 原则五：任务优先于页面

用户不是来测试页面组件的；用户是来完成任务的。Doppel 的执行单位应该是 mission，而不是 feature checklist。

#### 原则六：可复现优先于一次性演示

一次漂亮的 demo 没有意义。真正有价值的是：

- 可重复执行
- 能对比不同版本
- 能定位体验回退
- 能累积为团队的长期体验资产

---

## 4. 产品结构

### 4.1 Doppel 的四层结构

Doppel 由四层构成：

1. **Target Product Layer**

   - 被测试的 Web 产品
   - 可以是线上站点、preview 部署、或本地 dev 环境
2. **Sandbox Layer**

   - 隔离浏览器上下文
   - 测试账号
   - 可选的重置 / seed hooks
   - 可重复的入口状态
3. **Runtime + Judge Layer**

   - Persona 注入
   - Mission 执行
   - 会话记录
   - 两阶段评判
4. **Interface Layer**

   - CLI（MVP）
   - Web UI（后续）
   - GitHub Action（后续）
   - API（后续）

### 4.2 为什么必须保留 Sandbox 概念

如果没有 sandbox，Doppel 很容易退化成一个不稳定的浏览器 agent：

- 页面数据状态不可控
- 测试账号状态脏
- 结果无法复跑
- 报告难以比较
- 很难接入团队真实发布流程

因此，“sandbox”不是部署细节，而是 Doppel 的产品要件。

### 4.3 MVP 对 Sandbox 的定义

MVP 不做重型云端隔离环境，但必须支持轻量 sandbox：

- 独立浏览器 profile / context
- 专用测试账号
- 入口 URL 固定
- 可选 reset hook
- 可选 seed state

也就是说，MVP 的 sandbox 是“轻量、局部、可控”的，而不是“完整托管云环境”。

---

## 5. 核心用户

### 5.1 MVP 目标用户

| 用户                    | 痛点                               | Doppel 提供的价值                       |
| ----------------------- | ---------------------------------- | --------------------------------------- |
| 独立开发者 / vibe coder | 发布很快，但没人验证陌生人是否能用 | 在分享前快速跑一轮体验检查              |
| 早期创业团队            | 没有专职 QA / UX 研究资源          | 在每个版本前执行低成本预检              |
| 产品设计师 / UX 研究员  | 真实研究周期长                     | 用合成用户快速发现明显摩擦点            |
| 开源贡献者              | 想扩展测试标准                     | 编写领域化 persona / skill / judge 模板 |

### 5.2 不优先服务的对象

以下用户不是 MVP 的优先对象：

- 大型企业级 QA 团队
- 需要合规审计的行业
- 强依赖原生移动端体验验证的团队
- 需要完全确定性测试结果的场景

---

## 6. 核心对象模型

### 6.1 执行单元

Doppel 的基本执行单元不是“测试套件”，而是：

**一个 persona 在一个 sandbox 中执行一个 mission，并接受一组 criteria 的评判。**

### 6.2 配置对象

MVP 采用三类核心配置对象，另加一个可选 sandbox 配置块：

#### 1. `product.yaml`

描述目标产品的最小语义信息，以及 Doppel 运行该产品所需的环境信息。

```yaml
name: "PodFlow"
entry_url: "https://preview.podflow.app"
description: "A podcast listening and discovery platform"

auth:
  required: true
  username: "test@example.com"
  password: "${PODFLOW_TEST_PASSWORD}"

sandbox:
  mode: "preview"
  reset:
    strategy: "none"
  seed_state: "new_user"
```

其中：

- `name`、`entry_url`、`description` 会进入 agent 语境
- `auth`、`sandbox` 属于运行时元数据，不进入“产品介绍”

#### 2. `personas.yaml`

定义一个或多个合成用户类型。如果缺失，系统自动生成默认 persona。

```yaml
personas:
  - id: newcomer
    name: "First-time Alex"
    background: "Came from a social media post and knows nothing else"
    goal: "Figure out what the product does and try its main value"
    behavior_style: "Cautious, literal, leaves when confused"
    tech_level: low

  - id: impatient
    name: "Busy Sam"
    background: "Needs value immediately and dislikes reading"
    goal: "Get to the primary outcome fast"
    behavior_style: "Skips explanations, acts on instinct"
    tech_level: medium
```

#### 3. `skill.yaml`

定义这次测试到底要用户完成什么，以及如何判断表现。

```yaml
name: "First-time podcast discovery"
version: "1.0"
persona: newcomer

mission: |
  You have just arrived at this product for the first time.
  Find a podcast about business or startups and play one episode.

stop_conditions:
  - "Audio is playing"
  - "You would leave the product"
  - "You have made no meaningful progress in 20 steps"

judge_criteria:
  - id: path_efficiency
    question: "How directly did the user reach the goal?"
    good: "Reached the goal in 5 steps or fewer"
    bad: "Needed more than 8 steps or got lost"

  - id: confusion_moments
    question: "Did the user show signs of confusion?"
    good: "No hesitation or backtracking"
    bad: "Pauses, loops, or wrong-path clicks occurred"
```

### 6.3 为什么不把产品知识写得更详细

因为 Doppel 测的是产品能否自我解释，不是 agent 对产品文档的记忆能力。

允许丰富配置，不等于允许丰富 briefing。运行时元数据可以多，agent 认知上下文必须克制。

---

## 7. Sandbox 设计

### 7.1 什么叫“像真实用户一样在 sandbox 中体验”

这里的“像真实用户”不意味着完全模拟真实人类，而意味着：

- 从陌生视角进入产品
- 在不完整信息下做决策
- 出现犹豫、误判、回退和放弃
- 对路径阻力、文案理解、信息架构产生可观察反应

这里的“sandbox”也不只是 Docker 或浏览器容器，而是一个可控体验环境，至少包含：

- 独立浏览器上下文
- 可登录的测试账号
- 可预期的初始数据状态
- 尽量可重置的起始场景

### 7.2 Sandbox 的三种模式

#### 模式 A：Remote URL Sandbox（MVP 支持）

直接访问已有 staging / preview / production-like URL。

适合：

- 已有测试环境的团队
- 先验证产品价值

限制：

- 状态控制能力弱
- 外部噪声多

#### 模式 B：Local Preview Sandbox（MVP 可选）

由 Doppel 连接本地或 preview 环境，并调用 reset / seed hook 恢复初始状态。

适合：

- 正在迭代中的项目
- 希望结果更稳定的团队

#### 模式 C：Managed Ephemeral Sandbox（后续）

由 Doppel 启动临时环境、注入测试数据、运行后销毁。

适合：

- 团队级使用
- PR 级别比较
- 高复现要求

### 7.3 MVP 的产品承诺

MVP 不承诺“完美仿真真实世界”，只承诺三件事：

- 比传统 E2E 更像陌生用户
- 比人工体验走查更便宜、更高频
- 比一次性 agent demo 更可追溯、可重复、可比较

---

## 8. 用户工作流

### 8.1 端到端流程

1. 用户提供 `product.yaml`
2. 用户提供 `skill.yaml`
3. 可选提供 `personas.yaml`
4. Doppel 读取运行配置并准备 sandbox
5. 系统启动浏览器与 agent runtime
6. agent 以 persona 身份执行 mission
7. 运行时持续记录步骤、截图、状态和理由
8. 会话结束后，judge 先抽事实，再按 criteria 评分
9. 报告生成器输出 Markdown / JSON 报告
10. 用户阅读结果并决定是否修复产品体验

### 8.2 输出不是“评价”，而是“证据化结论”

一份有效的 Doppel 报告必须包含：

- 任务是否完成
- 关键路径用了多少步
- 明显的困惑点
- 失败或放弃的节点
- 对应步骤截图
- 每条 judge criteria 的评分与一句理由

报告可以有 narrative，但 narrative 必须建立在结构化证据之上。

---

## 9. MVP 范围

### 9.1 MVP 要交付什么

MVP 的产品承诺是：

**一条命令，跑出一份基于证据的体验报告。**

MVP 包含：

- CLI 入口：`doppel run --product product.yaml --skill skill.yaml`
- 轻量 sandbox：独立浏览器 context + 测试账号 + 可选 reset hooks
- Persona 注入
- Browser agent mission loop
- 全量 session logging
- Step screenshots
- 两阶段 judge
- Markdown + JSON 报告
- 默认 persona 自动生成
- 基础 auth 支持

### 9.2 MVP 明确不做什么

- 不做完整托管 SaaS
- 不做多人协作仪表盘
- 不做视频录制
- 不做移动端 / 原生桌面端
- 不做美学 skill 蒸馏 pipeline
- 不做复杂 CI 编排
- 不承诺完全稳定或完全可重复
- 不替代真实用户研究

### 9.3 为什么 CLI 仍然合理

因为 CLI 是 MVP 最合理的入口：

- 实现成本最低
- 最容易嵌入开发者现有流程
- 最适合先验证“是否真的有人愿意跑”

但文档、架构和产品表达必须持续强调：

> CLI 是入口，不是 Doppel 的完整定义。

---

## 10. 成功标准

### 10.1 用户侧成功指标

如果 Doppel 成立，MVP 需要满足以下信号：

- 用户能在 15 分钟内配置并跑出第一份报告
- 报告中至少有 1 到 3 条用户认为“确实有用”的体验问题
- 用户愿意在下一次迭代前再次运行
- 用户把 Doppel 视为“发布前体验预检”，而不是一次性演示玩具

### 10.2 产品侧成功指标

MVP 阶段重点看：

- 首跑成功率
- 报告完成率
- 平均单次运行时长
- 平均单次运行成本
- 用户对“发现的问题是否真实有帮助”的主观评分

---

## 11. 竞争与差异化

### 11.1 Doppel 不靠什么赢

它不靠：

- 浏览器自动化能力本身
- 生成一段看起来聪明的 narrative
- 单纯调用更强的大模型

这些能力都容易被复制。

### 11.2 Doppel 真正的差异化

它真正可能形成壁垒的地方是：

1. **任务化的 synthetic user runtime**
2. **可复跑的 sandbox 执行语义**
3. **以证据为中心的 session schema**
4. **可演进的 judge / skill 体系**
5. **对版本回退和体验对比的支持**

换句话说，Doppel 的 moat 应该是“体验测试基础设施”，而不是“agent 套了一层 CLI”。

---

## 12. 产品路线图

### 12.1 Phase 1：MVP

目标：

- 跑通单 persona、单 skill、单产品
- 输出可信的行为证据与判断

交付：

- CLI
- 轻量 sandbox
- 报告系统

### 12.2 Phase 2：Repeatability

目标：

- 提高可复现性与团队可用性

交付：

- reset hooks 标准化
- seed state 模板
- 多 persona 顺序运行
- run comparison

### 12.3 Phase 3：Team Workflow

目标：

- 嵌入产品团队真实迭代流程

交付：

- GitHub Action
- 报告聚合
- Web UI
- 结果历史对比

### 12.4 Phase 4：Distilled Taste

目标：

- 从行为问题扩展到审美和信任感问题

交付：

- 人工标注管线
- 美学 skill
- 专项 judge 模型

---

## 13. 待决策问题

以下问题仍需在 MVP 设计阶段明确：

### 13.1 Package 命名

候选：

- `doppel`
- `doppel-eval`
- `doppel-lab`

建议：如果可用，优先最短名称，但要避免与无关项目冲突。

### 13.2 Sandbox 配置暴露方式

有两个合理方向：

- 直接写进 `product.yaml`
- 单独拆成 `sandbox.yaml`

MVP 建议先放进 `product.yaml` 的 `sandbox` 块，减少文件数量。

### 13.3 默认 LLM 策略

建议：

- Runtime/Judge 默认用强模型
- Persona generation 用轻模型
- 提供 provider-agnostic 配置

### 13.4 存储位置

建议：

- 项目本地：`./.doppel/runs/<run_id>/`

理由：

- 更接近代码版本
- 更方便对比和归档

---

## 14. 一句话版本

### 对外定义

Doppel 是一个 AI 驱动的 synthetic user runtime，帮助团队在发布前用合成用户在 sandbox 中真实体验 Web 产品，并输出基于证据的体验测试报告。

### 对内定义

Doppel 的产品核心是：

**sandbox + runtime + judge**

而不是：

**CLI + browser workflow**

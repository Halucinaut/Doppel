# ai-bot.cn 示例

`ai-bot.cn` 是 Doppel v0.1.0 的官方展示样例，用于演示 Web 页面体验测试、单 persona 运行、多 persona batch、facts 提取、criteria 评估和报告输出。

## 文件结构

`product.yaml` 描述目标站点，`personas.yaml` 描述四个用户画像，`skill.yaml` 是基础单 persona judge skill，`skill-*.yaml` 是 batch 使用的多角色评测 skill。`artifacts/v0.1.0` 保存精选运行结果，已移除临时失败日志、browser-use conversation 和本地绝对路径。

## 运行命令

校验配置：

```bash
doppel validate \
  --product examples/ai-bot-cn/product.yaml \
  --skill examples/ai-bot-cn/skill.yaml \
  --personas examples/ai-bot-cn/personas.yaml
```

运行单 persona：

```bash
doppel run \
  --product examples/ai-bot-cn/product.yaml \
  --skill examples/ai-bot-cn/skill.yaml \
  --personas examples/ai-bot-cn/personas.yaml \
  --runtime-config runtime.local.yaml \
  --decision-provider browser-use
```

运行多 persona batch：

```bash
doppel batch \
  --product examples/ai-bot-cn/product.yaml \
  --skill-dir examples/ai-bot-cn \
  --personas examples/ai-bot-cn/personas.yaml \
  --runtime-config runtime.local.yaml \
  --decision-provider browser-use \
  --retries 1
```

## 最小展示案例

任务目标：判断第一次访问 `ai-bot.cn` 的用户能否理解站点用途、找到搜索或分类入口，并形成是否继续使用的判断。

Persona：AI 工具新手、设计师、产品经理、谨慎用户。

最终结论：四个 persona 都完成了任务。新手和产品经理识别搜索框，设计师识别 AI 设计工具，谨慎用户进入关于我们路径验证信任信息。

主要体验问题：首屏产品定位不够直接，部分路径没有触发滚动发现，信任信号暴露不稳定，谨慎用户路径存在连续等待。

证据截图路径：`artifacts/v0.1.0/single-newcomer/screenshots/step-002.png`、`artifacts/v0.1.0/batch/ai-bot-newcomer/screenshots/step-002.png`、`artifacts/v0.1.0/batch/ai-bot-product_manager/screenshots/step-003.png`。

报告输出路径：`artifacts/v0.1.0/single-newcomer/report.md`、`artifacts/v0.1.0/batch/batch_report.md`。

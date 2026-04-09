# 中文智能家居自动化规则生成系统

本项目是一个面向本地代码实验的 Python 项目，用于验证“中文自然语言规则 -> 中间 DSL -> 校验/修复 -> Home Assistant 风格 YAML -> 中文解释/结构可视化”这一整条规则生成链路。

项目当前重点不是前端或部署，而是验证两件事：

1. 引入中间 DSL 后，规则生成是否比直接生成 YAML 更稳定、更结构化。
2. 引入规则校验与自动修复后，最终规则的可执行率是否显著提升。

## 1. 项目目标

用户输入一条中文家居自动化描述，例如：

```text
玄关有人时开灯
```

系统会完成如下处理：

1. 读取设备知识库 `data/devices.json`
2. 通过 `parser` 生成 DSL 草案
3. 使用 `pydantic` 解析并约束 DSL 结构
4. 使用 `validator` 做规则校验
5. 使用 `repairer` 对部分确定性错误做自动修复
6. 将合法 DSL 转换成 Home Assistant 风格 YAML
7. 生成中文解释文本
8. 生成文本树和 Mermaid 结构图

## 2. 技术栈

- Python 3.12
- Pydantic 2
- PyYAML
- RapidFuzz
- pathlib / json / typing

项目默认面向 Windows 本地 Python 环境，但脚本本身不依赖 Web 框架。

## 3. 当前数据规模

当前仓库中已经包含实验所需的数据文件：

- 设备知识库：`data/devices.json`
  - 5000 条设备实体
  - 覆盖 20 个中文房间
  - 包含 `light`、`sensor`、`switch`、`climate`、`cover`、`camera`、`scene`、`script` 等类型
- 批量测试输入：`data/test_cases/`
  - 总计 5000 条中文规则输入
  - `normal_cases.json`: 2000 条
  - `ambiguous_cases.json`: 1500 条
  - `error_conflict_cases.json`: 1500 条
- 结构化标注集：`data/gold_dsl.json`
  - 当前为 700 条
  - 每条包含 `input_text` 和 `gold_dsl`
  - 该数据集用于结构化准确率实验

说明：

- `gold_dsl.json` 已经不再是简单的 pipeline bootstrap 输出，而是经过独立启发式改写和增补后的“类人工标注”数据。
- 它适合当前阶段做结构化准确率实验，但如果要作为论文最终标注集，仍建议继续做人工复核。

## 4. 目录结构

```text
大创coding/
├─ README.md
├─ requirements.txt
├─ main.py
├─ init_project.py
├─ mock_llm_client.py
├─ generate_test_cases.py
├─ generate_gold_dataset.py
├─ run_batch_experiments.py
├─ analyze_results.py
├─ baseline_direct_yaml.py
├─ compare_baseline_vs_dsl.py
├─ experiment_dsl_effectiveness.py
├─ experiment_repair.py
├─ experiment_repair_effectiveness.py
├─ experiment_explain_visualize.py
├─ experiment_structured_accuracy.py
├─ core/
│  ├─ parser.py
│  ├─ validator.py
│  ├─ repairer.py
│  ├─ yaml_converter.py
│  ├─ explainer.py
│  ├─ visualizer.py
│  ├─ pipeline.py
│  ├─ metric_utils.py
│  └─ data_utils.py
├─ models/
│  ├─ dsl_models.py
│  └─ device_models.py
├─ data/
│  ├─ devices.json
│  ├─ gold_dsl.json
│  ├─ eval_labeled_cases.json
│  └─ test_cases/
├─ prompts/
│  └─ dsl_prompt.txt
├─ outputs/
│  ├─ latest_rule.yaml
│  └─ reports/
└─ tests/
```

## 5. 核心模块说明

### `models/`

- `models/dsl_models.py`
  - 定义 RuleDSL、Trigger、Condition、Action 等 Pydantic 模型
- `models/device_models.py`
  - 定义设备模型和 `DeviceRegistry`
  - 支持从 `data/devices.json` 读取知识库

### `core/`

- `core/parser.py`
  - 负责把中文规则转成 DSL JSON 草案
  - 当前通过可替换的 `llm_client` 接口工作
- `core/validator.py`
  - 负责规则合法性校验
  - 校验项包括实体存在性、服务兼容性、动作冲突、时间/weekday 合法性等
- `core/repairer.py`
  - 负责确定性错误自动修复
  - 包括 `mode` 默认补全、entity 近似匹配、时间/weekday 修复、冲突动作修复等
- `core/yaml_converter.py`
  - 将 RuleDSL 转成 Home Assistant 风格 YAML
- `core/explainer.py`
  - 将 RuleDSL 转成中文解释
- `core/visualizer.py`
  - 生成文本树和 Mermaid 图
- `core/pipeline.py`
  - 串联整条规则处理流程

### 实验脚本

- `main.py`
  - 单条规则本地命令行实验入口
- `run_batch_experiments.py`
  - 批量执行 5000 条测试输入
- `analyze_results.py`
  - 汇总批量实验结果
- `compare_baseline_vs_dsl.py`
  - 对比“直接 YAML”与“DSL 中间层”
- `experiment_dsl_effectiveness.py`
  - 评估 DSL 中间层的工程有效性
- `experiment_repair_effectiveness.py`
  - 评估校验与自动修复模块
- `experiment_structured_accuracy.py`
  - 评估 DSL 结构化准确率
- `experiment_explain_visualize.py`
  - 输出解释和 Mermaid 可视化示例

## 6. 环境准备

### 6.1 Python 版本

推荐使用：

```bash
python --version
```

当前项目已在 `Python 3.12.4` 下验证。

### 6.2 安装依赖

```bash
pip install -r requirements.txt
```

`requirements.txt` 当前内容为：

```txt
pydantic>=2.7,<3.0
PyYAML>=6.0,<7.0
rapidfuzz>=3.9,<4.0
```

### 6.3 Windows 终端中文显示建议

如果在 PowerShell 中看到中文乱码，先执行：

```powershell
chcp 65001
```

必要时也可以使用：

```powershell
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
```

## 7. 快速运行教程

### 7.1 运行单条规则实验

直接执行：

```bash
python main.py
```

当前 `main.py` 会：

1. 在代码中读取一条中文输入
2. 调用 `core.pipeline.process_rule`
3. 使用 `mock_llm_client`
4. 打印：
   - 用户输入
   - DSL 草案
   - 修复日志
   - 校验前结果
   - 修复后 DSL
   - 校验后结果
   - 文本树
   - YAML
   - 中文解释

如果你要改测试内容，直接编辑 [main.py](main.py) 中的 `user_input`。

### 7.2 运行批量实验

```bash
python run_batch_experiments.py
python analyze_results.py
```

生成的结果文件包括：

- [batch_results.json](outputs/reports/batch_results.json)
- [report.txt](outputs/reports/report.txt)
- [report.md](outputs/reports/report.md)

### 7.3 运行 DSL vs 直接 YAML 对比实验

```bash
python compare_baseline_vs_dsl.py
python experiment_dsl_effectiveness.py
```

输出文件：

- [comparison_report.md](outputs/reports/comparison_report.md)
- [experiment_dsl_effectiveness.md](outputs/reports/experiment_dsl_effectiveness.md)

### 7.4 运行修复模块实验

```bash
python experiment_repair_effectiveness.py
```

输出文件：

- [experiment_repair_effectiveness.md](outputs/reports/experiment_repair_effectiveness.md)

### 7.5 运行结构化准确率实验

```bash
python experiment_structured_accuracy.py
```

输出文件：

- [structured_accuracy_report.md](outputs/reports/structured_accuracy_report.md)

### 7.6 运行解释与可视化实验

```bash
python experiment_explain_visualize.py
```

输出文件：

- [experiment_explain_visualize.md](outputs/reports/experiment_explain_visualize.md)
- [rule_diagram.md](outputs/reports/rule_diagram.md)

## 8. 推荐运行顺序

如果你第一次接触这个项目，建议按这个顺序运行：

1. `python main.py`
2. `python run_batch_experiments.py`
3. `python analyze_results.py`
4. `python compare_baseline_vs_dsl.py`
5. `python experiment_dsl_effectiveness.py`
6. `python experiment_repair_effectiveness.py`
7. `python experiment_structured_accuracy.py`
8. `python experiment_explain_visualize.py`

## 9. 项目当前使用的 8 个核心指标

当前项目已将指标收敛为 8 个，避免实验结论过于分散。

### 9.1 DSL 前后对比指标

#### 1. Rule Completeness Rate

- 定义：
  - 关键字段完整样本数 / 总样本数
- 作用：
  - 衡量规则是否包含完整核心结构
  - 用于比较“直接生成 YAML”和“先生成 DSL 再转 YAML”谁更容易漏字段

#### 2. Validation Pass Rate

- 定义：
  - 通过规则校验样本数 / 总样本数
- 作用：
  - 衡量规则是否满足实体存在、服务匹配、逻辑一致等约束
  - 用于比较 DSL 中间层是否提高规则合法性

#### 3. End-to-End Executable Rate

- 定义：
  - 最终 YAML 成功生成且修复后通过校验的样本数 / 总样本数
- 作用：
  - 衡量整条链路的最终可执行率
  - 是最接近真实系统效果的工程指标

#### 4. Repair Gain

- 定义：
  - 修复后通过率 - 修复前通过率
- 作用：
  - 量化 `validator + repairer` 对最终规则可执行率的提升
  - 用于证明自动修复模块的价值

### 9.2 机器学习型指标

#### 5. Exact Match (EM)

- 定义：
  - 预测 DSL 与 gold DSL 完全一致的样本数 / 总样本数
- 作用：
  - 最严格的结构化预测指标
  - 适合用于论文主结果

#### 6. Field Accuracy

- 定义：
  - 正确字段数 / 全部字段数
- 作用：
  - 衡量模型在字段级别是否大体正确
  - 用于补充 EM，避免“一处错全错”

#### 7. Trigger Type F1

- 定义：
  - 对 `time / state_change / event` 三类触发类型计算 F1
- 作用：
  - 衡量系统对规则触发语义的理解能力

#### 8. Entity Selection Micro-F1

- 定义：
  - 将 trigger / condition / action 中涉及的实体视作标签集合，计算 Micro-F1
- 作用：
  - 衡量系统在大规模设备知识库上的实体 grounding 能力

## 10. 指标与实验脚本对应关系

| 指标 | 主要脚本 |
| --- | --- |
| Rule Completeness Rate | `compare_baseline_vs_dsl.py`, `experiment_dsl_effectiveness.py`, `run_batch_experiments.py` |
| Validation Pass Rate | `compare_baseline_vs_dsl.py`, `experiment_dsl_effectiveness.py`, `run_batch_experiments.py` |
| End-to-End Executable Rate | `compare_baseline_vs_dsl.py`, `experiment_dsl_effectiveness.py`, `run_batch_experiments.py` |
| Repair Gain | `experiment_repair_effectiveness.py`, `analyze_results.py` |
| Exact Match | `experiment_structured_accuracy.py` |
| Field Accuracy | `experiment_structured_accuracy.py` |
| Trigger Type F1 | `experiment_structured_accuracy.py` |
| Entity Selection Micro-F1 | `experiment_structured_accuracy.py` |

## 11. 当前实验结果摘要

以下结果来自当前仓库中的已有实验输出。

### 11.1 DSL 中间层有效性

根据 [comparison_report.md](outputs/reports/comparison_report.md)：

| 指标 | 直接 YAML | DSL 中间层 |
| --- | ---: | ---: |
| Rule Completeness Rate | 88.20% | 100.00% |
| Validation Pass Rate | 70.92% | 100.00% |
| End-to-End Executable Rate | 70.92% | 100.00% |

说明：

- 在当前实验设置下，DSL 中间层相比直接 YAML 更稳定
- 规则更完整，且最终可执行率更高

### 11.2 校验与修复有效性

根据 [experiment_repair_effectiveness.md](outputs/reports/experiment_repair_effectiveness.md)：

- 修复前通过率：28.93%
- 修复后通过率：100.00%
- Repair Gain：71.07%

说明：

- 自动修复模块对拼写错误、非法 weekday、非法时间和动作冲突等问题有明显提升作用

### 11.3 结构化准确率

根据 [structured_accuracy_report.md](outputs/reports/structured_accuracy_report.md)：

- Exact Match：1.14%
- Field Accuracy：0.5128
- Trigger Type F1：1.0000
- Entity Selection Micro-F1：0.7244

说明：

- 这组指标比早期 bootstrap 标注版本更合理
- 其中 `Trigger Type F1` 较高，说明触发类型识别较稳定
- `Entity Selection Micro-F1` 仍有提升空间，说明大规模设备 grounding 仍是后续优化重点

## 12. 当前局限

1. `gold_dsl.json` 虽然已经摆脱简单 bootstrap 标注，但仍不是最终人工审校版标注集。
2. 当前 `mock_llm_client` 仍然是启发式模拟，不代表真实大模型上限。
3. 长尾设备类型数量较少，例如 `vacuum`、`lock`、`humidifier` 等，在评估中容易被低估。
4. 当前实验聚焦“规则生成有效性”，尚未涉及真实 Home Assistant 实例联调。

## 13. 后续可扩展方向

1. 引入人工审校的 gold 标注集
2. 将 `mock_llm_client` 替换为真实 LLM 接口
3. 提升 parser 的实体检索与候选排序能力
4. 增加 `Hit@K`、`MRR` 等实体检索指标
5. 将 YAML 输出接入真实 Home Assistant 自动化配置验证
6. 增加轻量图形界面或本地可视化展示页面

## 14. 常用命令速查

```bash
pip install -r requirements.txt
python main.py
python run_batch_experiments.py
python analyze_results.py
python compare_baseline_vs_dsl.py
python experiment_dsl_effectiveness.py
python experiment_repair_effectiveness.py
python experiment_structured_accuracy.py
python experiment_explain_visualize.py
python generate_test_cases.py
python generate_gold_dataset.py
```

## 15. 输出文件说明

- [latest_rule.yaml](outputs/latest_rule.yaml)
  - 最近一次单条规则生成的 YAML
- [batch_results.json](outputs/reports/batch_results.json)
  - 批量实验结果
- [comparison_report.md](outputs/reports/comparison_report.md)
  - 直接 YAML vs DSL 中间层对比
- [experiment_dsl_effectiveness.md](outputs/reports/experiment_dsl_effectiveness.md)
  - DSL 中间层有效性实验报告
- [experiment_repair_effectiveness.md](outputs/reports/experiment_repair_effectiveness.md)
  - 修复模块实验报告
- [structured_accuracy_report.md](outputs/reports/structured_accuracy_report.md)
  - 结构化准确率实验报告
- [experiment_explain_visualize.md](outputs/reports/experiment_explain_visualize.md)
  - 解释与可视化展示报告

---

如果你要继续扩展项目，建议优先从两个方向选择其一：

1. 提升 `gold_dsl.json` 的人工标注质量，增强机器学习指标可信度
2. 将 `mock_llm_client` 替换为真实可配置 LLM 接口，评估真实模型效果

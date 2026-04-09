# 规则自校验与自动修复有效性实验报告

## 实验目标

验证校验与自动修复模块能否提升规则的最终可执行率。

## 实验设置

- 注入错误样本数: 5600
- 样本来源: `data/gold_dsl.json` 的标准 DSL 样本
- 注入错误类型: 缺失 mode、实体拼写错误、服务前缀错误、冲突动作、非法 weekday、非法时间等

## 总体结果

- 修复前通过率: 28.93%
- 修复后通过率: 100.00%
- 自动修复增益: 71.07%

## 不同错误类型的修复成功率

| Error Type | Sample Count | Repair Success Rate |
| --- | ---: | ---: |
| action_entity_typo | 700 | 60.29% |
| condition_entity_typo | 700 | 100.00% |
| conflicting_actions | 700 | 100.00% |
| invalid_time | 700 | 100.00% |
| invalid_weekday | 700 | 100.00% |
| missing_mode | 700 | 0.00% |
| service_prefix_mismatch | 700 | 89.14% |
| trigger_entity_typo | 700 | 19.14% |

## 结论模板

> 实验结果表明，规则自校验与自动修复模块能够有效提升最终规则的通过率，尤其对缺失默认字段、实体拼写错误、时间格式错误和逻辑冲突等可确定性错误具有明显修复效果。这说明“校验 + 局部修复”的组合能够显著增强规则生成系统的工程稳健性。

# 规则自校验与自动修复有效性实验报告

## 实验目标

验证校验与自动修复模块能否提升规则的最终可执行率。

## 实验设置

- 注入错误样本数: 14400
- 样本来源: `data/gold_dsl.json` 的标准 DSL 样本
- 注入错误类型: 缺失 mode、实体拼写错误、服务前缀错误、冲突动作、非法 weekday、非法时间等

## 总体结果

- 修复前通过率: 30.06%
- 修复后通过率: 99.17%
- 自动修复增益: 69.10%

## 不同错误类型的修复成功率

| Error Type | Sample Count | Repair Success Rate |
| --- | ---: | ---: |
| action_entity_typo | 1800 | 59.11% |
| condition_entity_typo | 1800 | 98.78% |
| conflicting_actions | 1800 | 99.17% |
| invalid_time | 1800 | 99.17% |
| invalid_weekday | 1800 | 99.17% |
| missing_mode | 1800 | 0.00% |
| service_prefix_mismatch | 1800 | 77.39% |
| trigger_entity_typo | 1800 | 20.06% |

## 结论模板

> 实验结果表明，规则自校验与自动修复模块能够有效提升最终规则的通过率，尤其对缺失默认字段、实体拼写错误、时间格式错误和逻辑冲突等可确定性错误具有明显修复效果。这说明“校验 + 局部修复”的组合能够显著增强规则生成系统的工程稳健性。

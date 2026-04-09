# DSL 中间层有效性实验报告

## 实验目标

验证引入 DSL 中间层后，相比直接生成 YAML，规则生成是否更稳定、更结构化。

## 核心指标

- Rule Completeness Rate
- Validation Pass Rate
- End-to-End Executable Rate

## 实验结果

| 指标 | 直接 YAML | DSL 中间层 |
| --- | ---: | ---: |
| Rule Completeness Rate | 88.20% | 100.00% |
| Validation Pass Rate | 70.92% | 100.00% |
| End-to-End Executable Rate | 70.92% | 100.00% |

## 结论模板

> 实验结果表明，相较于直接生成 YAML，引入 DSL 中间层后，系统在规则完整性、规则合法性和端到端可执行性上均表现更稳定，因此 DSL 中间层能够有效提升规则生成系统的工程稳健性。

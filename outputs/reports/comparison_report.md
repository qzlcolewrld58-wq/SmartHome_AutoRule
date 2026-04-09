# Baseline vs DSL Comparison

## Methods

- 方案 A: 直接从中文生成 YAML
- 方案 B: 先生成 DSL，再转换为 YAML

## Comparison Table

| Metric | Direct YAML Baseline | DSL Middle Layer |
| --- | ---: | ---: |
| Sample Count | 5000 | 5000 |
| Rule Completeness Rate | 88.20% | 100.00% |
| Validation Pass Rate | 70.92% | 100.00% |
| End-to-End Executable Rate | 70.92% | 100.00% |

## Conclusion

These three metrics are the main DSL-before-vs-after comparison metrics used in the paper draft.

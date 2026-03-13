#!/bin/bash
# 批量修复测试用例中的证据清单内容
# 只替换简单的证据清单，保持 heredoc 结构完整

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 需要修复的测试文件列表（从失败测试中筛选）
tests_to_fix=(
  "pre-commit-code-ref-valid.test.sh"
  "pre-commit-constraints-checklist.test.sh"
  "pre-commit-deferred-plan-required.test.sh"
  "pre-commit-deployment-acceptance-gate.test.sh"
  "pre-commit-deployment-cr-subset.test.sh"
  "pre-commit-deployment-required.test.sh"
  "pre-commit-incremental-carried.test.sh"
  "pre-commit-minor-gate.test.sh"
  "pre-commit-req-baseline-hash-gwt-lines.test.sh"
  "pre-commit-review-evidence-required.test.sh"
  "pre-commit-review-reqc-evidence-type.test.sh"
  "pre-commit-spot-check-count.test.sh"
  "pre-commit-test-report-conclusion.test.sh"
  "pre-commit-test-report-gwt-id-width.test.sh"
  "pre-write-dispatcher-minor-testing-round.test.sh"
)

for test_file in "${tests_to_fix[@]}"; do
  file_path="$SCRIPT_DIR/$test_file"
  if [ ! -f "$file_path" ]; then
    echo "Skip: $test_file (not found)"
    continue
  fi

  # 检查是否包含简单的证据清单模式
  if grep -q '## 证据清单' "$file_path" && grep -q '**命令：** echo "test"' "$file_path"; then
    echo "Fixing: $test_file"

    # 使用 sed 替换简单的证据清单内容
    sed -i '/## 证据清单/,/<!-- REVIEW-SUMMARY-BEGIN -->/{
      /## 证据清单/!{
        /<!-- REVIEW-SUMMARY-BEGIN -->/!d
      }
    }' "$file_path"

    # 在 ## 证据清单 后插入有效内容
    sed -i '/## 证据清单/a\
\
### 1. 测试执行\
\
EVIDENCE_TYPE: RUN_OUTPUT\
EVIDENCE: All tests passed (2/2)\
\
**命令：**\
```bash\
pytest -q tests/\
```\
\
**输出：**\
```\
..\
2 passed in 0.05s\
```\
\
**定位：**\
- tests/test_example.py:10-30\
' "$file_path"
  else
    echo "Skip: $test_file (no simple evidence pattern)"
  fi
done

echo "Done."

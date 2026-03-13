#!/bin/bash
# 批量修复测试用例中的证据清单内容

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 标准证据清单模板
EVIDENCE_TEMPLATE='## 证据清单

### 1. 测试执行

EVIDENCE_TYPE: RUN_OUTPUT
EVIDENCE: All tests passed (5/5)

**命令：**
```bash
pytest -q
```

**输出：**
```
.....
5 passed in 0.12s
```

**定位：**
- tests/test_example.py:10-50'

# 查找所有包含 "## 证据清单" 但内容可能不足的测试文件
for test_file in "$SCRIPT_DIR"/*.test.sh; do
  if grep -q "## 证据清单" "$test_file"; then
    echo "Processing: $(basename "$test_file")"

    # 使用 awk 替换证据清单段落
    awk -v template="$EVIDENCE_TEMPLATE" '
      /^## 证据清单/ {
        in_evidence=1
        print template
        next
      }
      in_evidence && /^## / {
        in_evidence=0
      }
      !in_evidence {
        print
      }
    ' "$test_file" > "$test_file.tmp" && mv "$test_file.tmp" "$test_file"
  fi
done

echo "Done. Fixed evidence checklists in test files."

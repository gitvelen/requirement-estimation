#!/bin/bash
# aicoding-hooks-managed
# Warning 7: CR 必填字段完整性
CR_FILES=$(echo "$CHANGED" | grep -E 'docs/.*/cr/CR-.*\.md$' || true)
for cr in $CR_FILES; do
  [ ! -f "$cr" ] && continue
  if grep -q '## 1\. 变更意图' "$cr"; then
    awk '/## 1\. 变更意图/{f=1;next} /^##/{f=0}
      f && NF>0 && !/<[^>]+>/ && !/^[ \t]*-?[ \t]*\.\.\.[ \t]*$/' "$cr" \
      | grep -q . || warn "$cr: §1 变更意图为空（或仅含模板占位符）"
  fi
  if grep -q '## 2\. 变更点' "$cr"; then
    awk '/## 2\. 变更点/{f=1;next} /^##/{f=0}
      f && NF>0 && !/^[ \t]*-?[ \t]*\.\.\.[ \t]*$/' "$cr" \
      | grep -q . || warn "$cr: §2 变更点为空（或仅含模板占位符）"
  fi
  if grep -q '## 3\. 影响面' "$cr"; then
    awk '/## 3\. 影响面/{f=1;next} /^## [0-9]/{f=0}
      f && NF>0 && !/^[ \t]*-?[ \t]*\.\.\.[ \t]*$/ && !/\[ \]是.*\[ \]否/ && !/^[ \t]*\|[ \t|:-]*$/' "$cr" \
      | grep -q . || warn "$cr: §3 影响面为空（或仅含模板占位符）"
  fi
  if grep -q '## 6\. 验收与验证' "$cr"; then
    awk '/## 6\. 验收与验证/{f=1;next} /^## [0-9]/{f=0}
      f && /Given / && !/<[^>]+>/' "$cr" \
      | grep -q . || warn "$cr: §6 缺少 GWT 验收标准（或仅含模板占位符）"
  fi
done

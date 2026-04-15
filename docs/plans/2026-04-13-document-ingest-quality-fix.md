# Document Ingest Quality Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the document compile pipeline so the loan accounting tech-solution document produces correct D1-D5 candidates instead of missing D2 modules and polluted cross-domain fields.

**Architecture:** Keep the existing `DocumentSkillAdapter` rule-based pipeline, but tighten it in three places: section boundary detection, per-domain extraction filters, and main-feature module parsing for inline `模块名：说明` lines. Verify the fix against both unit-style adapter tests and the real `贷款核算` workspace artifacts by recompiling the affected document and checking the deployed runtime APIs.

**Tech Stack:** Python, pytest, Docker Compose runtime patch deployment, React frontend restart for verification only.

---

### Task 1: Lock the regression with failing adapter tests

**Files:**
- Modify: `tests/test_document_skill_adapter_quality.py`
- Inspect: `data/system_profiles/sid_4bea552b__贷款核算/source/documents/src_doc_cf7b26df1841/chunks.jsonl`

**Step 1: Write the failing test**

Add tests that cover:
- `4.6 主要功能说明` using inline `模块名：说明`
- D1 scope staying inside intro/overview content
- D3 `other_integrations` excluding pure capability lines
- D4 architecture/network/performance excluding heading text and checklist rows
- D5 constraints/risks excluding boilerplate and security tables

**Step 2: Run test to verify it fails**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_document_skill_adapter_quality.py`

Expected: FAIL on the new regression assertions.

### Task 2: Fix section parsing and extraction rules

**Files:**
- Modify: `backend/service/document_skill_adapter.py`
- Inspect: `backend/service/document_text_cleaner.py`

**Step 1: Implement minimal parser changes**

Add support for:
- inline module lines like `产品工厂：...`
- section stop conditions for `名词解释` and other structural boundaries
- filtering of heading-only lines, table/checklist rows, template boilerplate, and non-integration business lines

**Step 2: Keep the write scope minimal**

Do not refactor unrelated import/runtime code. Limit changes to extraction helpers used by document compile.

### Task 3: Verify green locally

**Files:**
- Test: `tests/test_document_skill_adapter_quality.py`
- Test: `tests/test_system_profile_import_api.py`

**Step 1: Run targeted tests**

Run:
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_document_skill_adapter_quality.py`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_system_profile_import_api.py -k 'import'`

Expected: PASS for the adapter regression tests and no import regression failure.

### Task 4: Recompile the affected loan-accounting profile data

**Files:**
- Runtime data: `data/system_profiles/sid_4bea552b__贷款核算/`

**Step 1: Re-run the compile/import path**

Use the existing backend service/API path so the fixed rules regenerate:
- `candidate/latest/merged_candidates.json`
- `profile/working.json`
- `profile/published.json` if publish flow is involved

**Step 2: Inspect output**

Confirm:
- D2 contains the module list from 4.6
- D1/D3/D4/D5 no longer contain the known noisy values

### Task 5: Patch runtime and verify deployed behavior

**Files:**
- Modify runtime copy if needed: `backend/service/document_skill_adapter.py`
- Update docs: `docs/v2.8/status.md`, `docs/v2.8/deployment.md`

**Step 1: Sync backend/frontend runtime**

Run the established runtime patch flow for STAGING/TEST.

**Step 2: Verify with fresh evidence**

Run:
- container health checks
- profile board/data APIs for `贷款核算`
- artifact/hash checks if backend file is copied into the running container

Expected: deployed runtime reflects the fixed extraction results.

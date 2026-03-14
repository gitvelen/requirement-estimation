# System Profile Board Regression Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore the `SystemProfileBoardPage` interaction model to the `v2.6` baseline while keeping the `v2.7` canonical profile API and save/publish endpoints unchanged.

**Architecture:** Rebuild the page around the old interaction skeleton: top system tabs, left domain navigation, center preview-first field cards, right timeline card, plus global extension and memory sections. Keep current `v2.7` data loading, permission filtering, canonical save payload, and timeline/memory/completeness requests; replace raw JSON/path editors with typed human-facing editors for D1-D5 fields.

**Tech Stack:** React, Ant Design, React Router, Axios, Jest, React Testing Library

---

### Task 1: Lock the regression with tests

**Files:**
- Existing: `frontend/src/__tests__/systemProfileBoardPage.v27.test.js`

**Step 1: Run the failing regression test**

Run: `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v27.test.js`

Expected: FAIL because the current page still renders a long raw form, has no system tab role, and exposes canonical path labels.

### Task 2: Rebuild the board page interaction shell

**Files:**
- Modify: `frontend/src/pages/SystemProfileBoardPage.js`

**Step 1: Keep the current data-loading and permission model**

Retain:
- `/api/v1/system/systems`
- `/api/v1/system-profiles/{system_name}`
- `/api/v1/system-profiles/completeness`
- `/api/v1/system-profiles/{system_id}/profile/events`
- `/api/v1/system-profiles/{system_id}/memory`
- save/publish endpoints

**Step 2: Restore the baseline layout**

Render:
- top `Tabs` for systems
- compact meta row with status/completeness/update time
- left vertical domain nav for `D1`-`D5`
- center content card with preview-first fields and per-field edit buttons
- right timeline card with load-more support

**Step 3: Replace raw editors with human-facing editors**

Implement:
- text preview + `Input.TextArea`
- list preview + repeated `Input`
- D3 service table preview + repeated row editor
- D4 tech stack grouped tags + grouped list editor
- D4 performance baseline structured preview + structured inputs
- extension and memory sections without raw canonical path labels

### Task 3: Preserve save/publish behavior

**Files:**
- Modify: `frontend/src/pages/SystemProfileBoardPage.js`

**Step 1: Maintain canonical draft state**

Keep an in-memory `draftProfileData` in `v2.7` canonical shape so save/publish can submit `profile_data` directly without format conversion on submit.

**Step 2: Re-attach preview-first edit controls**

Ensure field edits only appear after clicking `编辑{字段名}`, and the save button submits the updated canonical payload.

### Task 4: Verify the regression fix

**Files:**
- Existing: `frontend/src/__tests__/systemProfileBoardPage.v27.test.js`

**Step 1: Re-run the focused regression test**

Run: `cd frontend && CI=true npm test -- --watchAll=false --runInBand src/__tests__/systemProfileBoardPage.v27.test.js`

Expected: PASS

**Step 2: Run a production build smoke check**

Run: `cd frontend && npm run build`

Expected: PASS without compile errors

# WI-001 Target System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 `WI-001` 落地“待评估系统”创建入口、候选项解析与任务元数据持久化，不进入编排分支与编辑锁定。

**Architecture:** 在现有 `POST /api/v1/tasks` multipart 创建链路上增加 `target_system_mode` / `target_system_name` 表单字段。前端 `UploadPage` 通过主系统清单 + 当前登录 PM 主责/B角规则生成候选项；后端在 `backend/api/routes.py` 中再次基于当前用户校验 specific 选择是否合法，并把结果持久化到 task record，同时通过任务详情与编辑结果基础接口回传给前端。

**Tech Stack:** React 18 + Ant Design + RTL/Jest；FastAPI + TestClient + pytest。

---

**Implementation note:** 当前仓库规则禁止使用 `worktree`，本计划默认在当前 `feature-v2.9` 分支内顺序执行。

### Task 1: 写前端失败测试，固定 UploadPage 的目标系统交互

**Files:**
- Create: `frontend/src/__tests__/uploadPage.targetSystem.test.js`
- Modify: `frontend/src/pages/UploadPage.js`

**Step 1: Write the failing test**

```javascript
it('renders target system radio group before task name and keeps unlimited last', async () => {
  renderPage();

  expect(await screen.findByText('待评估系统')).toBeInTheDocument();
  expect(screen.getByLabelText('支付系统')).toBeInTheDocument();
  expect(screen.getByLabelText('账务系统')).toBeInTheDocument();
  expect(screen.getByLabelText('不限')).toBeInTheDocument();
  expect(screen.getByPlaceholderText('例如：核心系统需求评估')).toBeInTheDocument();
});

it('shows only unlimited when manager owns no systems and still submits', async () => {
  axios.get.mockResolvedValueOnce({ data: { data: { systems: [{ id: 'sys_x', name: '核心账务', extra: { owner_username: 'other_pm' } }] } } });
  renderPage();

  expect(await screen.findByLabelText('不限')).toBeInTheDocument();
  expect(screen.queryByLabelText('核心账务')).not.toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/uploadPage.targetSystem.test.js`
Expected: FAIL，因为 `UploadPage` 还没有 `待评估系统` 字段，也没有读取系统清单。

**Step 3: Write minimal implementation**

```javascript
const [targetSystemOptions, setTargetSystemOptions] = useState([]);
const [targetSystemMode, setTargetSystemMode] = useState('');
const [targetSystemName, setTargetSystemName] = useState('');

useEffect(() => {
  // load systems -> filterResponsibleSystems -> append 不限
}, []);

formData.append('target_system_mode', targetSystemMode);
formData.append('target_system_name', targetSystemMode === 'specific' ? targetSystemName : '');
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/uploadPage.targetSystem.test.js`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/__tests__/uploadPage.targetSystem.test.js frontend/src/pages/UploadPage.js
git commit -m "test: cover upload target system selection"
```

### Task 2: 写后端失败测试，固定创建接口与详情字段

**Files:**
- Create: `tests/test_target_system_task_create.py`
- Modify: `backend/api/routes.py`
- Modify: `backend/api/system_routes.py`

**Step 1: Write the failing test**

```python
def test_create_task_persists_specific_target_system(client, tmp_path):
    _seed_manager("pm_target_1")
    _seed_systems_with_owner(tmp_path, [
        {"id": "sys_pay", "name": "支付系统", "extra": {"owner_username": "pm_target_1"}},
        {"id": "sys_crm", "name": "客户系统", "extra": {"owner_username": "other_pm"}},
    ])
    token = _login(client, "pm_target_1", "pwd123")

    response = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("req.docx", b"fake-docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        data={"target_system_mode": "specific", "target_system_name": "支付系统"},
    )

    assert response.status_code == 200
    task = _latest_task()
    assert task["target_system_mode"] == "specific"
    assert task["target_system_name"] == "支付系统"
```

```python
def test_create_task_rejects_specific_system_outside_manager_scope(client, tmp_path):
    ...
    assert response.status_code == 400
```

```python
def test_task_detail_and_requirement_result_return_target_system_fields(client):
    ...
    assert detail["data"]["targetSystemMode"] == "specific"
    assert detail["data"]["targetSystemName"] == "支付系统"
    assert result["data"]["target_system_mode"] == "specific"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_target_system_task_create.py -q`
Expected: FAIL，因为创建接口和详情/结果接口还没有这些字段和校验。

**Step 3: Write minimal implementation**

```python
def _list_manager_responsible_system_names(current_user):
    systems = system_routes._read_systems()
    return [item["name"] for item in systems if system_routes.resolve_system_ownership(current_user, system_name=item.get("name")).get("allowed_draft_write")]

task_record["target_system_mode"] = normalized_mode
task_record["target_system_name"] = normalized_name

task.setdefault("target_system_mode", "unlimited")
task.setdefault("target_system_name", "")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_target_system_task_create.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_target_system_task_create.py backend/api/routes.py backend/api/system_routes.py
git commit -m "feat: persist target system task metadata"
```

### Task 3: 接上前后端协议，完成提交校验与显示文案

**Files:**
- Modify: `frontend/src/pages/UploadPage.js`
- Modify: `frontend/src/utils/systemOwnership.js`
- Modify: `backend/api/routes.py`

**Step 1: Write the failing test**

```javascript
it('blocks submit until target system is selected and sends specific payload in form data', async () => {
  renderPage();
  fireEvent.click(await screen.findByRole('radio', { name: '支付系统' }));
  fireEvent.click(screen.getByRole('button', { name: '提交评估' }));
  await waitFor(() => expect(axios.post).toHaveBeenCalled());
});
```

```python
def test_create_task_accepts_unlimited_when_manager_has_no_owned_systems(client, tmp_path):
    ...
    assert task["target_system_mode"] == "unlimited"
    assert task["target_system_name"] == ""
```

**Step 2: Run tests to verify they fail**

Run:
- `cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/uploadPage.targetSystem.test.js`
- `pytest tests/test_target_system_task_create.py -q`

Expected: 至少有一个断言失败，说明表单提交或 unlimited 兼容尚未完整打通。

**Step 3: Write minimal implementation**

```javascript
const submitDisabled = uploading || fileList.length === 0 || !targetSystemMode;

<Radio.Group
  value={targetSystemMode === 'specific' ? targetSystemName : targetSystemMode}
  onChange={handleTargetSystemChange}
/>
```

```python
if normalized_mode == "unlimited":
    normalized_name = ""
elif normalized_name not in allowed_system_names:
    raise HTTPException(status_code=400, detail="待评估系统不在当前项目经理可选范围内")
```

**Step 4: Run tests to verify they pass**

Run:
- `cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/uploadPage.targetSystem.test.js`
- `pytest tests/test_target_system_task_create.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/pages/UploadPage.js frontend/src/utils/systemOwnership.js backend/api/routes.py
git commit -m "feat: submit target system selection on task creation"
```

### Task 4: 记录 WI-001 的 branch-local 测试证据

**Files:**
- Modify: `testing.md`

**Step 1: Add branch-local testing records**

```yaml
- acceptance_ref: ACC-001
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: cd frontend && CI=true npm test -- --runInBand --watch=false src/__tests__/uploadPage.targetSystem.test.js
  test_date: 2026-04-20
  artifact_ref: frontend/src/__tests__/uploadPage.targetSystem.test.js
  result: pass
```

```yaml
- acceptance_ref: ACC-002
  test_type: integration
  test_scope: branch-local
  verification_type: automated
  test_command: pytest tests/test_target_system_task_create.py -q
  test_date: 2026-04-20
  artifact_ref: tests/test_target_system_task_create.py
  result: pass
```

**Step 2: Verify formatting and evidence alignment**

Run: `sed -n '1,260p' testing.md`
Expected: 新记录位于 `Branch-Local Testing` 下，`acceptance_ref` 与 WI-001 一致。

**Step 3: Commit**

```bash
git add testing.md
git commit -m "docs: record wi-001 branch-local verification"
```

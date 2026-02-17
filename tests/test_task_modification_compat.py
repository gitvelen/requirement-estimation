import os
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.app import app
from backend.api import routes as task_routes
from backend.config.config import settings
from backend.service import user_service


@pytest.fixture()
def client(tmp_path, monkeypatch):
    data_dir = tmp_path / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, 'REPORT_DIR', str(data_dir))
    monkeypatch.setattr(settings, 'DEBUG', False)

    monkeypatch.setattr(user_service, 'USER_STORE_PATH', str(data_dir / 'users.json'))
    monkeypatch.setattr(user_service, 'USER_STORE_LOCK_PATH', str(data_dir / 'users.json.lock'))

    monkeypatch.setattr(task_routes, 'TASK_STORE_PATH', str(data_dir / 'task_storage.json'))
    monkeypatch.setattr(task_routes, 'TASK_STORE_LOCK_PATH', str(data_dir / 'task_storage.json.lock'))

    return TestClient(app)


def _seed_user(username: str, password: str, roles):
    user = user_service.create_user_record(
        {
            'username': username,
            'display_name': username,
            'password': password,
            'roles': roles,
        }
    )
    with user_service.user_storage_context() as users:
        users.append(user)
    return user


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post('/api/v1/auth/login', json={'username': username, 'password': password})
    assert response.status_code == 200
    return response.json()['data']['token']


def _seed_task_with_legacy_modification(task_id: str):
    task = {
        'task_id': task_id,
        'name': '修改记录兼容任务',
        'creator_id': 'mgr_legacy',
        'status': 'completed',
        'workflow_status': 'draft',
        'created_at': datetime.now().isoformat(),
        'systems_data': {
            'HOP': [
                {
                    'id': 'feat_1',
                    '功能点': '开户',
                    '业务描述': '旧描述',
                    '备注': '旧备注',
                }
            ]
        },
        'modifications': [
            {
                'id': 'legacy_mod_1',
                'timestamp': datetime.now().isoformat(),
                'operation': 'update',
                'system': 'HOP',
                'feature_id': 'feat_1',
                'feature_name': '开户',
                'field': '业务描述',
                'old_value': '更早描述',
                'new_value': '旧描述',
            }
        ],
    }
    with task_routes._task_storage_context() as data:
        data[task_id] = task


def test_legacy_modifications_still_readable(client):
    task_id = 'task_legacy_read'
    _seed_task_with_legacy_modification(task_id)

    response = client.get(f'/api/v1/requirement/modifications/{task_id}')

    assert response.status_code == 200
    payload = response.json()['data']
    assert payload['task_id'] == task_id
    assert payload['total'] == 1
    assert payload['modifications'][0]['id'] == 'legacy_mod_1'
    assert payload['modifications'][0].get('actor_id') is None
    assert payload['modifications'][0].get('actor_role') is None


def test_legacy_and_new_modifications_can_coexist(client):
    manager = _seed_user('legacy_actor_mgr', 'pwd123', ['manager'])
    token = _login(client, 'legacy_actor_mgr', 'pwd123')

    task_id = 'task_legacy_mix'
    _seed_task_with_legacy_modification(task_id)

    update_resp = client.put(
        f'/api/v1/requirement/features/{task_id}',
        json={
            'system': 'HOP',
            'operation': 'update',
            'feature_index': 0,
            'feature_data': {'业务描述': '新描述'},
        },
        headers={'Authorization': f'Bearer {token}'},
    )

    assert update_resp.status_code == 200

    task = task_routes._get_task(task_id)
    modifications = task.get('modifications') or []
    assert len(modifications) == 2
    assert modifications[0].get('id') == 'legacy_mod_1'
    assert modifications[0].get('actor_id') is None

    latest = modifications[-1]
    assert latest.get('actor_id') == manager['id']
    assert latest.get('actor_role') == 'manager'

    read_resp = client.get(f'/api/v1/requirement/modifications/{task_id}')
    assert read_resp.status_code == 200
    assert read_resp.json()['data']['total'] == 2

import logging

from backend.agent import system_identification_agent as sys_agent_module
from backend.api import system_list_routes


class _DummyAgent:
    def __init__(self):
        self.system_list = []

    def _load_system_list(self):
        return ["HOP", "CLMP"]


def test_reload_system_identification_cache_initializes_agent_when_global_is_none(monkeypatch, caplog):
    dummy_agent = _DummyAgent()
    monkeypatch.setattr(sys_agent_module, "system_identification_agent", None)
    monkeypatch.setattr(sys_agent_module, "get_system_identification_agent", lambda: dummy_agent)

    with caplog.at_level(logging.WARNING):
        system_list_routes._reload_system_identification_cache()

    assert dummy_agent.system_list == ["HOP", "CLMP"]
    assert "重载系统识别缓存失败" not in caplog.text

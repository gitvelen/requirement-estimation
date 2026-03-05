import logging

from backend.api import system_list_routes
from backend.agent import system_identification_agent as sys_agent_module


class _DummyAgent:
    def __init__(self):
        self.system_list = []
        self.subsystem_mapping = {}

    def _load_system_list(self):
        return ["HOP", "CLMP"]

    def _load_subsystem_mapping(self):
        return {"开放存": "HOP"}


def test_reload_system_identification_cache_initializes_agent_when_global_is_none(monkeypatch, caplog):
    dummy_agent = _DummyAgent()
    monkeypatch.setattr(sys_agent_module, "system_identification_agent", None)
    monkeypatch.setattr(sys_agent_module, "get_system_identification_agent", lambda: dummy_agent)

    with caplog.at_level(logging.WARNING):
        system_list_routes._reload_system_identification_cache()

    assert dummy_agent.system_list == ["HOP", "CLMP"]
    assert dummy_agent.subsystem_mapping == {"开放存": "HOP"}
    assert "重载系统识别缓存失败" not in caplog.text

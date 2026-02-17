import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.agent.system_identification_agent import SystemIdentificationAgent
from backend.api import subsystem_routes, system_routes
from backend.config.config import settings
from backend.service.knowledge_service import KnowledgeService


def test_unified_system_list_source_under_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))

    system_csv = data_dir / "system_list.csv"
    system_csv.write_text("系统名称,英文简称,系统状态\n核心系统,HOP,运行中\n", encoding="utf-8")

    monkeypatch.setattr(system_routes, "CSV_PATH", str(system_csv))
    systems = system_routes._read_systems()
    assert systems
    assert systems[0].get("name") == "核心系统"

    knowledge = KnowledgeService()
    loaded_names = knowledge._load_system_list()
    assert "核心系统" in loaded_names

    agent = SystemIdentificationAgent(knowledge_service=None)
    loaded_from_agent = agent._load_system_list()
    assert "核心系统" in loaded_from_agent


def test_unified_subsystem_source_under_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "REPORT_DIR", str(data_dir))

    subsystem_csv = data_dir / "subsystem_list.csv"
    subsystem_csv.write_text("子系统名称,所属主系统\n网银,HOP\n", encoding="utf-8")

    monkeypatch.setattr(subsystem_routes, "CSV_PATH", str(subsystem_csv))
    mappings = subsystem_routes._read_subsystem_mappings()
    assert mappings
    assert mappings[0].get("subsystem") == "网银"

    agent = SystemIdentificationAgent(knowledge_service=None)
    mapping = agent._load_subsystem_mapping()
    assert mapping.get("网银") == "HOP"


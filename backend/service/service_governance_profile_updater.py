from __future__ import annotations

from collections import defaultdict
import re
from typing import Any, Dict, List, Optional

from backend.api import system_routes
from backend.service.esb_service import get_esb_service
from backend.service.memory_service import get_memory_service
from backend.service.runtime_execution_service import get_runtime_execution_service
from backend.service.system_profile_service import get_system_profile_service


class ServiceGovernanceProfileUpdater:
    BRACKETED_NAME_SUFFIX_PATTERN = re.compile(r"[\(\[（【][^\)\]）】]*[\)\]）】]")
    PROVIDER_NAME_ALIASES = [
        "系统名称",
        "提供方系统名称",
        "服务方系统名称",
        "系统名称#2",
    ]
    CONSUMER_NAME_ALIASES = [
        "消费方系统名称",
        "调用方系统名称",
    ]
    SERVICE_NAME_ALIASES = [
        "服务名称",
        "服务名",
    ]
    TRANSACTION_NAME_ALIASES = [
        "交易名称",
        "交易名",
        "场景名称",
        "场景名",
    ]
    STATUS_ALIASES = [
        "状态",
        "使用状态",
    ]
    SCENARIO_CODE_ALIASES = [
        "服务场景码",
        "场景码",
    ]

    def __init__(self) -> None:
        self.esb_service = get_esb_service()
        self.memory_service = get_memory_service()
        self.execution_service = get_runtime_execution_service()
        self.profile_service = get_system_profile_service()

    def _resolve_system_map(self) -> Dict[str, Dict[str, Any]]:
        systems = system_routes._read_systems()
        result: Dict[str, Dict[str, Any]] = {}
        for system in systems:
            name = str(system.get("name") or "").strip()
            if name:
                result[name] = system
            normalized_name = self._normalize_system_name(name)
            if normalized_name:
                result[normalized_name] = system
        return result

    def _extract_rows(self, file_content: bytes, filename: str) -> List[Dict[str, Any]]:
        parsed_sheets = self.esb_service._parse_file(file_content, filename)
        rows: List[Dict[str, Any]] = []
        for _, sheet_rows in parsed_sheets.items():
            rows.extend(sheet_rows or [])
        return rows

    def _pick_value(self, row: Dict[str, Any], aliases: List[str]) -> str:
        for alias in aliases:
            value = row.get(alias)
            text = str(value or "").strip()
            if text:
                return text
        return ""

    def _normalize_system_name(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        normalized = self.BRACKETED_NAME_SUFFIX_PATTERN.sub("", text)
        normalized = re.sub(r"\s+", "", normalized)
        return normalized.strip()

    def _collect_updates(self, rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        systems_by_name = self._resolve_system_map()
        updates: Dict[str, Dict[str, Any]] = {}
        unmatched_items: List[Dict[str, Any]] = []
        matched_count = 0

        for row in rows:
            provider_name = self._pick_value(row, self.PROVIDER_NAME_ALIASES)
            service_name = self._pick_value(row, self.SERVICE_NAME_ALIASES)
            transaction_name = self._pick_value(row, self.TRANSACTION_NAME_ALIASES)
            consumer_name = self._pick_value(row, self.CONSUMER_NAME_ALIASES)
            status_value = self._pick_value(row, self.STATUS_ALIASES) or "正常使用"
            scenario_code = self._pick_value(row, self.SCENARIO_CODE_ALIASES)

            if not service_name:
                service_name = transaction_name
            if not transaction_name:
                transaction_name = service_name

            if not provider_name or not service_name:
                continue

            provider_system = systems_by_name.get(provider_name)
            if not provider_system:
                provider_system = systems_by_name.get(self._normalize_system_name(provider_name))
            if not provider_system:
                unmatched_items.append(
                    {
                        "system_name": provider_name,
                        "service_name": service_name,
                        "reason": "system_not_found",
                    }
                )
                continue

            matched_count += 1
            provider_id = str(provider_system.get("id") or "").strip()
            provider_system_name = str(provider_system.get("name") or provider_name).strip() or provider_name
            provider_payload = updates.setdefault(
                provider_id,
                {
                    "system_name": provider_system_name,
                    "provided_services": [],
                    "consumed_services": [],
                    "other_integrations": [],
                    "matched_rows": 0,
                },
            )
            provider_payload["matched_rows"] += 1
            provider_payload["provided_services"].append(
                {
                    "service_name": service_name,
                    "transaction_name": transaction_name,
                    "scenario_code": scenario_code,
                    "peer_system": consumer_name,
                    "status": status_value,
                }
            )

            consumer_system = systems_by_name.get(consumer_name)
            if not consumer_system:
                consumer_system = systems_by_name.get(self._normalize_system_name(consumer_name))
            if consumer_system:
                consumer_id = str(consumer_system.get("id") or "").strip()
                consumer_system_name = str(consumer_system.get("name") or consumer_name).strip() or consumer_name
                provider_payload["provided_services"][-1]["peer_system"] = consumer_system_name
                consumer_payload = updates.setdefault(
                    consumer_id,
                    {
                        "system_name": consumer_system_name,
                        "provided_services": [],
                        "consumed_services": [],
                        "other_integrations": [],
                        "matched_rows": 0,
                    },
                )
                consumer_payload["consumed_services"].append(
                    {
                        "service_name": service_name,
                        "transaction_name": transaction_name,
                        "scenario_code": scenario_code,
                        "peer_system": provider_system_name,
                        "status": status_value,
                    }
                )

        return {
            "updates": updates,
            "matched_count": matched_count,
            "unmatched_items": unmatched_items,
        }

    def _build_field_updates(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "integration_interfaces.canonical.provided_services": payload["provided_services"],
            "integration_interfaces.canonical.consumed_services": payload["consumed_services"],
            "integration_interfaces.canonical.other_integrations": payload["other_integrations"],
            "integration_interfaces.canonical.extensions": {
                "governance_summary": {
                    "active_provider_count": len(payload["provided_services"]),
                    "active_consumer_count": len(payload["consumed_services"]),
                    "matched_rows": payload["matched_rows"],
                }
            },
        }

    def _build_field_sources(
        self,
        *,
        execution_id: str,
        actor: Optional[Dict[str, Any]],
        field_paths: List[str],
    ) -> Dict[str, Any]:
        actor_name = (actor or {}).get("username") or (actor or {}).get("id") or "system"
        return {
            field_path: {
                "source": "governance",
                "scene_id": "admin_service_governance_import",
                "source_id": execution_id,
                "updated_at": None,
                "actor": actor_name,
            }
            for field_path in field_paths
        }

    def import_governance(
        self,
        *,
        file_content: bytes,
        filename: str,
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        execution = self.execution_service.create_execution(
            scene_id="admin_service_governance_import",
            system_id="",
            source_type="service_governance",
            source_file=filename,
            skill_chain=["service_governance_skill"],
        )

        rows = self._extract_rows(file_content, filename)
        collected = self._collect_updates(rows)
        updates = collected["updates"]
        unmatched_items = collected["unmatched_items"]

        status_name = "completed"
        errors: List[str] = []
        updated_system_ids: List[str] = []
        updated_systems: List[Dict[str, str]] = []

        for system_id, payload in updates.items():
            system_name = str(payload["system_name"] or "").strip()
            profile = self.profile_service.ensure_profile(system_name, system_id=system_id, actor=actor)
            field_sources = profile.get("field_sources") if isinstance(profile.get("field_sources"), dict) else {}

            desired_updates = self._build_field_updates(payload)
            applied_updates: Dict[str, Any] = {}
            policy_results: List[Dict[str, Any]] = []

            for field_path, value in desired_updates.items():
                existing_source = field_sources.get(field_path) if isinstance(field_sources.get(field_path), dict) else {}
                if str(existing_source.get("source") or "").strip() == "manual":
                    policy_results.append(
                        {
                            "field_path": field_path,
                            "decision": "reject",
                            "reason": "manual_source_wins",
                        }
                    )
                    continue
                applied_updates[field_path] = value
                policy_results.append(
                    {
                        "field_path": field_path,
                        "decision": "auto_apply",
                        "reason": "service_governance_d3_update",
                    }
                )

            if applied_updates:
                self.profile_service.apply_v27_field_updates(
                    system_name,
                    system_id=system_id,
                    field_updates=applied_updates,
                    field_sources=self._build_field_sources(
                        execution_id=execution["execution_id"],
                        actor=actor,
                        field_paths=list(applied_updates.keys()),
                    ),
                    actor=actor,
                )
                updated_system_ids.append(system_id)
                updated_systems.append(
                    {
                        "system_id": system_id,
                        "system_name": system_name,
                    }
                )
                try:
                    self.memory_service.append_record(
                        system_id=system_id,
                        memory_type="profile_update",
                        memory_subtype="service_governance",
                        scene_id="admin_service_governance_import",
                        source_type="service_governance",
                        source_id=execution["execution_id"],
                        summary="服务治理导入更新 D3 canonical",
                        payload={"changed_fields": list(applied_updates.keys())},
                        decision_policy="auto_apply",
                        confidence=1.0,
                        actor=(actor or {}).get("username"),
                    )
                except Exception as exc:  # pragma: no cover
                    status_name = "partial_success"
                    errors.append(str(exc))

        result_summary = {
            "updated_system_ids": updated_system_ids,
            "updated_systems": updated_systems,
            "skipped_items": unmatched_items,
        }
        updated_execution = self.execution_service.update_execution(
            execution["execution_id"],
            status=status_name,
            error="; ".join(errors) if errors else None,
            result_summary=result_summary,
        )

        return {
            "status": updated_execution["status"],
            "execution_id": execution["execution_id"],
            "matched_count": collected["matched_count"],
            "unmatched_count": len(unmatched_items),
            "unmatched_items": unmatched_items,
            "updated_system_ids": sorted(updated_system_ids),
            "updated_systems": sorted(updated_systems, key=lambda item: (item["system_id"], item["system_name"])),
            "errors": errors,
        }


_service_governance_profile_updater: Optional[ServiceGovernanceProfileUpdater] = None


def get_service_governance_profile_updater() -> ServiceGovernanceProfileUpdater:
    global _service_governance_profile_updater
    if _service_governance_profile_updater is None:
        _service_governance_profile_updater = ServiceGovernanceProfileUpdater()
    return _service_governance_profile_updater

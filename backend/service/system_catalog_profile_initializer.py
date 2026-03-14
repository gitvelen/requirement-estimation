from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.service.memory_service import get_memory_service
from backend.service.profile_schema_service import is_blank_profile
from backend.service.runtime_execution_service import get_runtime_execution_service
from backend.service.skill_runtime_service import get_skill_runtime_service
from backend.service.system_profile_service import get_system_profile_service


def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_items = value
    else:
        normalized = (
            str(value)
            .replace("，", ",")
            .replace("、", ",")
            .replace("；", ",")
            .replace(";", ",")
            .replace("\n", ",")
        )
        raw_items = normalized.split(",")

    result: List[str] = []
    for item in raw_items:
        text = _normalize_text(item)
        if text and text not in result:
            result.append(text)
    return result


def _merge_unique_lists(*values: Any) -> List[str]:
    result: List[str] = []
    for value in values:
        for item in _normalize_list(value):
            if item not in result:
                result.append(item)
    return result


class BlankProfileEvaluator:
    def is_blank(self, profile: Optional[Dict[str, Any]]) -> bool:
        return is_blank_profile(profile or {})


class SystemCatalogProfileInitializer:
    def __init__(self) -> None:
        self.blank_profile_evaluator = BlankProfileEvaluator()
        self.memory_service = get_memory_service()
        self.execution_service = get_runtime_execution_service()
        self.runtime_service = get_skill_runtime_service()
        self.profile_service = get_system_profile_service()

    def _build_field_updates(self, system_item: Dict[str, Any]) -> Dict[str, Any]:
        extra = system_item.get("extra") if isinstance(system_item.get("extra"), dict) else {}
        abbreviation = _normalize_text(system_item.get("abbreviation"))

        position_extensions: Dict[str, Any] = {}
        technical_extensions: Dict[str, Any] = {}
        constraint_extensions: Dict[str, Any] = {}
        interface_extensions: Dict[str, Any] = {}

        aliases = _merge_unique_lists(abbreviation, extra.get("英文简称"))
        if aliases:
            position_extensions["aliases"] = aliases

        business_lines = _normalize_list(extra.get("业务领域"))
        if business_lines:
            position_extensions["business_lines"] = business_lines

        status = _normalize_text(system_item.get("status") or extra.get("状态"))
        if status:
            position_extensions["status"] = status

        application_level = _normalize_text(extra.get("应用等级"))
        if application_level:
            position_extensions["application_level"] = application_level

        cloud_deployment = _normalize_text(extra.get("是否云部署"))
        if cloud_deployment:
            technical_extensions["cloud_deployment"] = cloud_deployment

        internet_exit = _normalize_text(extra.get("是否有互联网出口"))
        if internet_exit:
            technical_extensions["internet_exit"] = internet_exit

        dual_active = _normalize_text(extra.get("是否双活"))
        if dual_active:
            technical_extensions["dual_active"] = dual_active

        cluster_category = _normalize_text(extra.get("集群分类"))
        if cluster_category:
            technical_extensions["cluster_category"] = cluster_category

        virtualization_distribution = _normalize_text(extra.get("虚拟化分布"))
        if virtualization_distribution:
            technical_extensions["virtualization_distribution"] = virtualization_distribution

        innovation_stack = _normalize_text(extra.get("全栈信创"))
        if innovation_stack:
            constraint_extensions["innovation_stack"] = innovation_stack

        mlps_level = _normalize_text(extra.get("等保定级"))
        if mlps_level:
            constraint_extensions["mlps_level"] = mlps_level

        important_system = _normalize_text(extra.get("是否是重要信息系统"))
        if important_system:
            constraint_extensions["important_system"] = important_system

        dr_rto = _normalize_text(extra.get("系统RTO"))
        if dr_rto:
            constraint_extensions["dr_rto"] = dr_rto

        dr_rpo = _normalize_text(extra.get("系统RPO"))
        if dr_rpo:
            constraint_extensions["dr_rpo"] = dr_rpo

        dr_status = _normalize_text(extra.get("灾备情况"))
        if dr_status:
            constraint_extensions["dr_status"] = dr_status

        dr_site = _normalize_text(extra.get("灾备部署地"))
        if dr_site:
            constraint_extensions["dr_site"] = dr_site

        emergency_plan_updated_at = _normalize_text(extra.get("应急预案更新日期"))
        if emergency_plan_updated_at:
            constraint_extensions["emergency_plan_updated_at"] = emergency_plan_updated_at

        intellectual_property = _normalize_text(extra.get("知识产权"))
        if intellectual_property:
            constraint_extensions["intellectual_property"] = intellectual_property

        license_certificate_status = _normalize_text(extra.get("产品授权证书情况"))
        if license_certificate_status:
            constraint_extensions["license_certificate_status"] = license_certificate_status

        related_systems = _normalize_list(extra.get("关联系统"))
        if related_systems:
            interface_extensions["catalog_related_systems"] = related_systems

        updates: Dict[str, Any] = {}

        system_type = _normalize_text(extra.get("系统类型"))
        if system_type:
            updates["system_positioning.canonical.system_type"] = system_type

        business_domain = _normalize_list(extra.get("应用主题域"))
        if business_domain:
            updates["system_positioning.canonical.business_domain"] = business_domain

        architecture_layer = _normalize_text(extra.get("应用分层"))
        if architecture_layer:
            updates["system_positioning.canonical.architecture_layer"] = architecture_layer

        target_users = _normalize_list(extra.get("服务对象"))
        if target_users:
            updates["system_positioning.canonical.target_users"] = target_users

        service_scope = _normalize_text(extra.get("功能描述"))
        if service_scope:
            updates["system_positioning.canonical.service_scope"] = service_scope

        if position_extensions:
            updates["system_positioning.canonical.extensions"] = position_extensions

        languages = _normalize_list(extra.get("开发语言"))
        databases = _normalize_list(extra.get("RDBMS"))
        middleware = _normalize_list(extra.get("应用中间件"))
        others = _merge_unique_lists(extra.get("操作系统"), extra.get("芯片"), extra.get("新技术特征"))
        tech_stack = {}
        if languages:
            tech_stack["languages"] = languages
        if databases:
            tech_stack["databases"] = databases
        if middleware:
            tech_stack["middleware"] = middleware
        if others:
            tech_stack["others"] = others
        if tech_stack:
            updates["technical_architecture.canonical.tech_stack"] = tech_stack

        if technical_extensions:
            updates["technical_architecture.canonical.extensions"] = technical_extensions

        if constraint_extensions:
            updates["constraints_risks.canonical.extensions"] = constraint_extensions

        if interface_extensions:
            updates["integration_interfaces.canonical.extensions"] = interface_extensions

        return updates

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
                "source": "system_catalog",
                "scene_id": "admin_system_catalog_import",
                "source_id": execution_id,
                "updated_at": None,
                "actor": actor_name,
            }
            for field_path in field_paths
        }

    def initialize_catalog(
        self,
        *,
        systems: List[Dict[str, Any]],
        actor: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        scene = self.runtime_service.resolve_scene("admin_system_catalog_import", {})
        execution = self.execution_service.create_execution(
            scene_id=scene["scene_id"],
            system_id="",
            source_type="system_catalog",
            source_file="system_list_confirm",
            skill_chain=scene["skill_chain"],
        )

        updated_system_ids: List[str] = []
        updated_systems: List[Dict[str, str]] = []
        skipped_items: List[Dict[str, Any]] = []
        errors: List[str] = []
        policy_results: List[Dict[str, Any]] = []

        for system_item in systems or []:
            system_id = _normalize_text(system_item.get("id"))
            system_name = _normalize_text(system_item.get("name"))
            field_updates = self._build_field_updates(system_item)

            if not system_name or not field_updates:
                skipped_items.append(
                    {
                        "system_id": system_id,
                        "system_name": system_name,
                        "reason": "mapping_incomplete",
                    }
                )
                policy_results.append(
                    {
                        "system_id": system_id,
                        "field_path": "",
                        "decision": "reject",
                        "reason": "mapping_incomplete",
                    }
                )
                continue

            existing_profile = self.profile_service.get_profile(system_name)
            if existing_profile and not self.blank_profile_evaluator.is_blank(existing_profile):
                skipped_items.append(
                    {
                        "system_id": system_id,
                        "system_name": system_name,
                        "reason": "profile_not_blank",
                    }
                )
                policy_results.append(
                    {
                        "system_id": system_id,
                        "field_path": "",
                        "decision": "reject",
                        "reason": "profile_not_blank",
                    }
                )
                continue

            try:
                self.profile_service.ensure_profile(system_name, system_id=system_id, actor=actor)
                self.profile_service.apply_v27_field_updates(
                    system_name,
                    system_id=system_id,
                    field_updates=field_updates,
                    field_sources=self._build_field_sources(
                        execution_id=execution["execution_id"],
                        actor=actor,
                        field_paths=list(field_updates.keys()),
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
                policy_results.extend(
                    {
                        "system_id": system_id,
                        "field_path": field_path,
                        "decision": "auto_apply",
                        "reason": "blank_profile_catalog_init",
                    }
                    for field_path in field_updates.keys()
                )
                try:
                    self.memory_service.append_record(
                        system_id=system_id,
                        memory_type="profile_update",
                        memory_subtype="system_catalog_init",
                        scene_id="admin_system_catalog_import",
                        source_type="system_catalog",
                        source_id=execution["execution_id"],
                        summary="系统清单初始化画像",
                        payload={"changed_fields": list(field_updates.keys())},
                        decision_policy="auto_apply",
                        confidence=1.0,
                        actor=(actor or {}).get("username"),
                    )
                except Exception as exc:  # pragma: no cover
                    errors.append(str(exc))
            except Exception as exc:  # pragma: no cover
                errors.append(f"{system_name or system_id}: {exc}")

        status = "partial_success" if errors else "completed"
        updated_execution = self.execution_service.update_execution(
            execution["execution_id"],
            status=status,
            error="; ".join(errors) if errors else None,
            result_summary={
                "updated_system_ids": sorted(updated_system_ids),
                "updated_systems": sorted(updated_systems, key=lambda item: (item["system_id"], item["system_name"])),
                "skipped_items": skipped_items,
                "errors": errors,
            },
            policy_results=policy_results,
        )

        return {
            "status": updated_execution["status"],
            "execution_id": execution["execution_id"],
            "updated_system_ids": sorted(updated_system_ids),
            "updated_systems": sorted(updated_systems, key=lambda item: (item["system_id"], item["system_name"])),
            "skipped_items": skipped_items,
            "errors": errors,
        }


def get_system_catalog_profile_initializer() -> SystemCatalogProfileInitializer:
    return SystemCatalogProfileInitializer()

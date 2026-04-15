"""
大模型调用封装
统一封装阿里云大模型API调用，支持重试、错误处理
"""
import copy
import json
import time
import logging
from typing import Dict, List, Optional, Any
from openai import OpenAI
from backend.config.config import settings
from backend.utils.token_counter import extract_usage_from_response as extract_usage_from_token_response

logger = logging.getLogger(__name__)


def extract_usage_from_response(response: Any) -> Dict[str, int]:
    return extract_usage_from_token_response(response)


def _canonical_dedupe_key(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return json.dumps(value, ensure_ascii=False)


def _dedupe_stable(items: List[Any]) -> List[Any]:
    result: List[Any] = []
    seen = set()
    for item in items:
        key = _canonical_dedupe_key(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(copy.deepcopy(item))
    return result


def _merge_list_field(field_name: Optional[str], base: List[Any], update: List[Any]) -> List[Any]:
    if field_name in {
        "functional_modules",
        "business_scenarios",
        "business_flows",
        "business_constraints",
        "prerequisites",
        "sensitive_points",
    }:
        result = [copy.deepcopy(item) for item in base]
        index_by_name = {
            str(item.get("name") or "").strip(): idx
            for idx, item in enumerate(result)
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        }
        for item in update:
            item_name = str(item.get("name") or "").strip() if isinstance(item, dict) else ""
            if item_name and item_name in index_by_name:
                idx = index_by_name[item_name]
                result[idx] = deep_merge(result[idx], item)
            else:
                result.append(copy.deepcopy(item))
                if item_name:
                    index_by_name[item_name] = len(result) - 1
        return result

    if field_name == "data_reports":
        result = [copy.deepcopy(item) for item in base]
        index_by_name_type = {
            (
                str(item.get("name") or "").strip(),
                str(item.get("type") or "").strip(),
            ): idx
            for idx, item in enumerate(result)
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        }
        for item in update:
            item_key = (
                str(item.get("name") or "").strip(),
                str(item.get("type") or "").strip(),
            ) if isinstance(item, dict) else (_canonical_dedupe_key(item), "")
            if item_key[0] and item_key in index_by_name_type:
                idx = index_by_name_type[item_key]
                result[idx] = deep_merge(result[idx], item)
            else:
                result.append(copy.deepcopy(item))
                if item_key[0]:
                    index_by_name_type[item_key] = len(result) - 1
        return result

    if field_name == "risk_items":
        result = [copy.deepcopy(item) for item in base]
        index_by_name = {
            str(item.get("name") or "").strip(): idx
            for idx, item in enumerate(result)
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        }
        for item in update:
            item_name = str(item.get("name") or "").strip() if isinstance(item, dict) else ""
            if item_name and item_name in index_by_name:
                idx = index_by_name[item_name]
                result[idx] = deep_merge(result[idx], item)
            else:
                result.append(copy.deepcopy(item))
                if item_name:
                    index_by_name[item_name] = len(result) - 1
        return result

    if field_name == "module_structure":
        result = [copy.deepcopy(item) for item in base]
        index_by_name = {
            str(item.get("module_name") or "").strip(): idx
            for idx, item in enumerate(result)
            if isinstance(item, dict) and str(item.get("module_name") or "").strip()
        }
        for item in update:
            module_name = str(item.get("module_name") or "").strip() if isinstance(item, dict) else ""
            if module_name and module_name in index_by_name:
                idx = index_by_name[module_name]
                result[idx] = deep_merge(result[idx], item)
            else:
                result.append(copy.deepcopy(item))
                if module_name:
                    index_by_name[module_name] = len(result) - 1
        return result

    if field_name == "functions":
        result = [copy.deepcopy(item) for item in base]
        seen = {
            (
                str(item.get("name") or "").strip(),
                str(item.get("desc") or "").strip(),
            )
            for item in result
            if isinstance(item, dict)
        }
        for item in update:
            key = (
                str(item.get("name") or "").strip(),
                str(item.get("desc") or "").strip(),
            ) if isinstance(item, dict) else (_canonical_dedupe_key(item), "")
            if key in seen:
                continue
            seen.add(key)
            result.append(copy.deepcopy(item))
        return result

    if field_name == "integration_points":
        result = [copy.deepcopy(item) for item in base]
        seen = {
            (
                str(item.get("peer_system") or "").strip(),
                str(item.get("protocol") or "").strip(),
                str(item.get("direction") or "").strip(),
                str(item.get("description") or "").strip(),
            )
            for item in result
            if isinstance(item, dict)
        }
        for item in update:
            key = (
                str(item.get("peer_system") or "").strip(),
                str(item.get("protocol") or "").strip(),
                str(item.get("direction") or "").strip(),
                str(item.get("description") or "").strip(),
            ) if isinstance(item, dict) else (_canonical_dedupe_key(item), "", "", "")
            if key in seen:
                continue
            seen.add(key)
            result.append(copy.deepcopy(item))
        return result

    if field_name == "key_constraints":
        result = [copy.deepcopy(item) for item in base]
        seen = {
            (
                str(item.get("category") or "").strip(),
                str(item.get("description") or "").strip(),
            )
            for item in result
            if isinstance(item, dict)
        }
        for item in update:
            key = (
                str(item.get("category") or "").strip(),
                str(item.get("description") or "").strip(),
            ) if isinstance(item, dict) else (_canonical_dedupe_key(item), "")
            if key in seen:
                continue
            seen.add(key)
            result.append(copy.deepcopy(item))
        return result

    return _dedupe_stable(list(base) + list(update))


def deep_merge(base: Any, update: Any, *, field_name: Optional[str] = None) -> Any:
    if base is None:
        return copy.deepcopy(update)
    if update is None:
        return copy.deepcopy(base)

    if isinstance(base, dict) and isinstance(update, dict):
        result = copy.deepcopy(base)
        for key, value in update.items():
            if key not in result:
                result[key] = copy.deepcopy(value)
            else:
                result[key] = deep_merge(result[key], value, field_name=key)
        return result

    if isinstance(base, list) and isinstance(update, list):
        return _merge_list_field(field_name, base, update)

    if isinstance(base, str) and isinstance(update, str):
        if not base:
            return update
        if not update or update == base:
            return base
        return f"{base}; {update}"

    return copy.deepcopy(update)


def merge_stage1_responses(responses: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    merged_domains: List[str] = []
    merged_systems: List[str] = []

    for response in responses:
        if not isinstance(response, dict):
            raise ValueError("INVALID_STAGE1_RESPONSE")
        if "relevant_domains" not in response or "related_systems" not in response:
            raise ValueError("INVALID_STAGE1_RESPONSE")

        domains = response.get("relevant_domains") or []
        systems = response.get("related_systems") or []
        for domain in domains:
            normalized = str(domain or "").strip()
            if normalized and normalized not in merged_domains:
                merged_domains.append(normalized)
        for system in systems:
            normalized = str(system or "").strip()
            if normalized and normalized not in merged_systems:
                merged_systems.append(normalized)

    return {
        "relevant_domains": merged_domains,
        "related_systems": merged_systems,
    }

class LLMClient:
    """大模型客户端类"""

    def __init__(self):
        """初始化大模型客户端"""
        self.api_key = settings.DASHSCOPE_API_KEY
        self.base_url = settings.DASHSCOPE_API_BASE
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.timeout = settings.LLM_TIMEOUT

        if not self.api_key:
            logger.warning("DASHSCOPE_API_KEY 未配置，LLM调用将失败")

        # 初始化OpenAI客户端（兼容阿里云DashScope）
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        logger.info(f"LLM客户端初始化完成，模型: {self.model}")

    def _chat_raw(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        retry_times: int = 3,
        timeout: Optional[float] = None,
    ) -> Any:
        temperature = temperature or self.temperature
        max_tokens = max_tokens or self.max_tokens
        request_timeout = self.timeout if timeout is None else timeout
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY未配置")

        for attempt in range(retry_times):
            try:
                logger.info(f"LLM请求尝试 {attempt + 1}/{retry_times}")

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=request_timeout
                )

                usage = extract_usage_from_response(response)
                if usage.get("total_tokens") is not None:
                    logger.info(f"LLM请求成功，返回token数: {usage['total_tokens']}")
                else:
                    logger.info("LLM请求成功，usage缺失")

                return response

            except Exception as e:
                logger.warning(f"LLM请求失败（第{attempt + 1}次）: {str(e)}")

                if attempt < retry_times - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"LLM请求失败，已重试{retry_times}次")
                    raise

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        retry_times: int = 3,
        timeout: Optional[float] = None,
    ) -> str:
        """
        发起对话请求

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数（可选）
            max_tokens: 最大token数（可选）
            retry_times: 重试次数

        Returns:
            str: 模型返回的文本内容

        Raises:
            Exception: 调用失败且重试后仍失败
        """
        response = self._chat_raw(messages, temperature, max_tokens, retry_times, timeout)
        return response.choices[0].message.content

    def chat_with_system_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        retry_times: int = 3,
        timeout: Optional[float] = None,
    ) -> str:
        """
        使用系统提示词对话

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            temperature: 温度参数（可选）
            max_tokens: 最大token数（可选）

        Returns:
            str: 模型返回的文本内容
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self.chat(
            messages,
            temperature,
            max_tokens,
            retry_times=retry_times,
            timeout=timeout,
        )

    def extract_json(self, text: str) -> Dict[str, Any]:
        """
        从文本中提取JSON内容

        Args:
            text: 包含JSON的文本

        Returns:
            Dict: 解析后的JSON对象
        """
        import json
        import re

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取JSON代码块
        json_pattern = r'```json\s*(.*?)\s*```'
        matches = re.findall(json_pattern, text, re.DOTALL)

        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        # 尝试提取花括号内容
        brace_pattern = r'\{.*\}'
        matches = re.findall(brace_pattern, text, re.DOTALL)

        if matches:
            try:
                return json.loads(matches[0])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"无法从文本中提取有效的JSON: {text[:200]}...")


# 全局LLM客户端实例
llm_client = LLMClient()

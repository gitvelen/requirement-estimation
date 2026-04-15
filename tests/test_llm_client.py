from types import SimpleNamespace

import pytest

from backend.utils import llm_client as llm_client_module


class _FakeCompletions:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class _FakeOpenAIClient:
    def __init__(self, response):
        self.chat = SimpleNamespace(completions=_FakeCompletions(response))


def _build_response(content: str, *, prompt_tokens=12, completion_tokens=34, total_tokens=46):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )


def test_chat_preserves_text_contract_and_exposes_raw_response(monkeypatch):
    client = llm_client_module.LLMClient()
    client.api_key = "test-key"
    client.client = _FakeOpenAIClient(_build_response("raw-response"))

    raw_response = client._chat_raw(
        [{"role": "user", "content": "hello"}],
        temperature=0.2,
        max_tokens=123,
        retry_times=1,
    )
    text_response = client.chat(
        [{"role": "user", "content": "hello"}],
        temperature=0.2,
        max_tokens=123,
        retry_times=1,
    )

    assert raw_response.choices[0].message.content == "raw-response"
    assert text_response == "raw-response"
    assert client.client.chat.completions.calls[0]["max_tokens"] == 123


def test_extract_usage_from_response_returns_empty_dict_when_usage_missing():
    assert llm_client_module.extract_usage_from_response({}) == {}
    assert llm_client_module.extract_usage_from_response(SimpleNamespace()) == {}


def test_merge_stage1_stage2_responses():
    stage1_merged = llm_client_module.merge_stage1_responses(
        [
            {
                "relevant_domains": ["system_positioning", "business_capabilities"],
                "related_systems": ["ECIF", "ODS"],
            },
            {
                "relevant_domains": ["business_capabilities", "technical_architecture"],
                "related_systems": ["ODS", "MOB"],
            },
        ]
    )

    stage2_merged = llm_client_module.deep_merge(
        {
            "system_positioning": {"system_description": "范围A"},
            "business_capabilities": {
                "module_structure": [
                    {
                        "module_name": "M1",
                        "functions": [{"name": "开户", "desc": "开户登记"}],
                    }
                ]
            },
            "integration_interfaces": {},
            "constraints_risks": {
                "key_constraints": [{"category": "合规", "description": "旧约束"}]
            },
        },
        {
            "system_positioning": {"system_description": "范围B"},
            "business_capabilities": {
                "module_structure": [
                    {
                        "module_name": "M1",
                        "functions": [
                            {"name": "开户", "desc": "开户登记"},
                            {"name": "放款", "desc": "放款处理"},
                        ],
                    },
                    {
                        "module_name": "M2",
                        "functions": [{"name": "核算", "desc": "核算处理"}],
                    },
                ]
            },
            "integration_interfaces": {
                "integration_points": [
                    {
                        "peer_system": "ECIF",
                        "protocol": "REST",
                        "direction": "outbound",
                        "description": "同步客户信息",
                    }
                ]
            },
            "constraints_risks": {
                "key_constraints": [
                    {"category": "合规", "description": "旧约束"},
                    {"category": "性能", "description": "峰值 TPS 受限"},
                ]
            },
        },
    )

    assert stage1_merged == {
        "relevant_domains": [
            "system_positioning",
            "business_capabilities",
            "technical_architecture",
        ],
        "related_systems": ["ECIF", "ODS", "MOB"],
    }
    assert (
        stage2_merged["system_positioning"]["system_description"]
        == "范围A; 范围B"
    )
    assert stage2_merged["integration_interfaces"]["integration_points"] == [
        {
            "peer_system": "ECIF",
            "protocol": "REST",
            "direction": "outbound",
            "description": "同步客户信息",
        }
    ]
    assert stage2_merged["constraints_risks"]["key_constraints"] == [
        {"category": "合规", "description": "旧约束"},
        {"category": "性能", "description": "峰值 TPS 受限"},
    ]
    assert stage2_merged["business_capabilities"]["module_structure"] == [
        {
            "module_name": "M1",
            "functions": [
                {"name": "开户", "desc": "开户登记"},
                {"name": "放款", "desc": "放款处理"},
            ],
        },
        {
            "module_name": "M2",
            "functions": [{"name": "核算", "desc": "核算处理"}],
        },
    ]


def test_deep_merge_covers_generic_and_none_branches():
    assert llm_client_module.deep_merge(None, {"a": 1}) == {"a": 1}
    assert llm_client_module.deep_merge({"a": 1}, None) == {"a": 1}
    assert llm_client_module.deep_merge("", "新值") == "新值"
    assert llm_client_module.deep_merge("原值", "") == "原值"
    assert llm_client_module.deep_merge("原值", "原值") == "原值"
    assert llm_client_module.deep_merge(1, 2) == 2
    assert llm_client_module.deep_merge(
        [{"name": "A"}, {"name": "A"}],
        [{"name": "B"}, {"name": "A"}],
        field_name="generic_list",
    ) == [{"name": "A"}, {"name": "B"}]


def test_merge_stage1_responses_rejects_invalid_payloads():
    with pytest.raises(ValueError, match="INVALID_STAGE1_RESPONSE"):
        llm_client_module.merge_stage1_responses(["bad"])  # type: ignore[list-item]

    with pytest.raises(ValueError, match="INVALID_STAGE1_RESPONSE"):
        llm_client_module.merge_stage1_responses([{"relevant_domains": ["system_positioning"]}])


def test_chat_raw_retries_and_chat_with_system_prompt(monkeypatch):
    attempts = {"count": 0}
    waits = []

    class _RetryCompletions:
        def create(self, **kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("temporary")
            return _build_response("retry-ok", total_tokens=88)

    client = llm_client_module.LLMClient()
    client.api_key = "test-key"
    client.client = SimpleNamespace(chat=SimpleNamespace(completions=_RetryCompletions()))
    monkeypatch.setattr(llm_client_module.time, "sleep", lambda seconds: waits.append(seconds))

    response = client._chat_raw([{"role": "user", "content": "hello"}], retry_times=2)
    assert response.choices[0].message.content == "retry-ok"
    assert attempts["count"] == 2
    assert waits == [1]

    captured = {}
    monkeypatch.setattr(
        client,
        "chat",
        lambda messages, temperature=None, max_tokens=None, retry_times=3, timeout=None: captured.update(
            {
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "retry_times": retry_times,
                "timeout": timeout,
            }
        )
        or "ok",
    )
    assert (
        client.chat_with_system_prompt(
            "system",
            "user",
            temperature=0.3,
            max_tokens=222,
            retry_times=4,
            timeout=9,
        )
        == "ok"
    )
    assert captured["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
    assert captured["temperature"] == 0.3
    assert captured["max_tokens"] == 222
    assert captured["retry_times"] == 4
    assert captured["timeout"] == 9


def test_chat_raw_requires_api_key_and_extract_json_supports_fallbacks():
    client = llm_client_module.LLMClient()
    client.api_key = ""

    with pytest.raises(ValueError, match="DASHSCOPE_API_KEY未配置"):
        client._chat_raw([{"role": "user", "content": "hello"}])

    parser = llm_client_module.LLMClient()
    assert parser.extract_json('{"a": 1}') == {"a": 1}
    assert parser.extract_json("```json\n{\"b\": 2}\n```") == {"b": 2}
    assert parser.extract_json("prefix {\"c\": 3} suffix") == {"c": 3}

    with pytest.raises(ValueError, match="无法从文本中提取有效的JSON"):
        parser.extract_json("no json here")

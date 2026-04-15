from backend.service.document_skill_adapter import DocumentSkillAdapter


LOAN_ACCOUNTING_TECH_SOLUTION_TEXT = "\n".join(
    [
        "贷款核算系统项目",
        "技术方案建议书",
        "1.1. 编写目的 5",
        "1.2. 业务背景 5",
        "1.3. 需求概述 5",
        "1.4. 名词解释 6",
        "第四章 技术方案说明 9",
        "4.2. 整体架构 9",
        "4.6. 主要功能说明 13",
        "4.6.1. 产品工厂 13",
        "4.6.2. 贷款开户 13",
        "4.6.3. 贷款发放 14",
        "4.6.4. 贷款还款设置 14",
        "4.6.5. 贷款利率、费率设置 14",
        "4.6.6. 贷款还款 15",
        "4.6.7. 贷款核销及核销收回 15",
        "4.6.8. 贷款代偿 16",
        "4.6.9. 冲正功能 16",
        "4.6.10. 日终批量处理 17",
        "4.7. 工作说明 17",
        "4.9. 安全策略方案 19",
        "5.2. 实施风险 21",
        "第一章 引言",
        "编写目的",
        "本技术方案建议书编写为了指引后续的人员开发设计系统使用，使用对象不限于项目经理、开发人员、测试人员等。",
        "业务背景",
        "需求概述",
        "通过零售贷款核心系统提供贷款生命周期相关完整的功能，包括放款、还款、计息结息、账务处理和贷后处理。",
        "功能性需求要点",
        "产品工厂：灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。",
        "贷款开户：支持一般、特殊等各种类型的贷款开户操作。",
        "贷款发放：支持手动放款、渠道调用放款或根据合同约定的放款方式和金额进行自动贷款发放。",
        "贷款还款设置：设置贷款还款方式，还款规则，还款账号等信息。",
        "贷款利率、费率设置：灵活设置贷款利率、费率。",
        "贷款还款：支持客户主动、渠道调用及按还款计划自动扣款等贷款还款方式。",
        "贷款核销及核销收回：支持对非应计贷款进行核销，贷款催收回款后，进行核销贷款回收账务处理。",
        "贷款代偿：对已放款且逾期，并满足代偿要求的贷款进行代偿操作。",
        "冲正功能：支持对符合条件的贷款发放、贷款还款进行冲正。",
        "日终批量处理：日终批处理时，根据系统配置的参数处理贷款账户计提、结息、自动扣收、对账文件的生成等过程；完成与核心以及总账系统的对账处理；完成对数仓的供数操作。",
        "名词解释",
        "第二章 现有系统现状分析",
        "核心系统",
        "核心系统目前提供贷款相关功能包括：贷款开立，贷款回收，贷款余额查询，贷款信息查询，还款试算，还款计划查询。",
        "数据仓库",
        "每日晚间批量同步核心贷款信息，还款计划，交易流水文件至在线融资系统。",
        "在线融资系统",
        "在线融资系统调用核心贷款开立，贷款回收，贷款余额查询接口进行贷款交易，并通过每日日终批量，由数据仓库推送核心贷款信息，还款计划，交易流水文件进行对账。",
        "第三章 数据分析",
        "数据流向说明",
        "为本系统供数的系统：在线融资。",
        "使用本系统数据的系统：核心、核心支付、互联网支付、数据仓库。",
        "第四章 技术方案说明",
        "概要说明",
        "假设及约束",
        "整体架构",
        "整体架构图",
        "架构图说明",
        "贷款核算系统通过内联网关与服务总线与行内各业务系统相连。",
        "贷款核算系统在云上实施，注册在云上统一服务注册中心。",
        "在线融资通过esb访问云上内联网关与贷款核算交互。",
        "贷款核算通过云上内联网关访问云下esb，调用核心，统一支付，互联网支付接口。",
        "数仓抽取贷款核算数据，生成下游系统报送文件。",
        "应用部署架构",
        "服务采用分布式集群部署方式，每台应用服务器均部署相同的功能模块，且互为备份。",
        "单中心数据库每个实例部署采用一主多从方式，数据支持物理拆分多个实例。",
        "系统逻辑架构",
        "逻辑架构图",
        "系统采用组件化的模块设计方式和插件化的处理方式，具有结构清晰、符合标准、易于理解、扩展方便等优点。可根据实际需要灵活调整。",
        "提供系统参数可配置化管理功能，提供系统最大的灵活性和可扩展性。",
        "具备交易系统的基本可管理能力，包括流水登记、应用路由、流量控制、服务监控、异常诊断、资源监控、过程信息自动清理等；",
        "提供公共组件处理，包括日志、数据库连接池、应用配置、错误配置、数据标准映射、权限控制、订阅发布等。",
        "技术方案特点",
        "贷款系统批量机制",
        "贷款核算系统日终主要负责批量放款、还款等业务处理。通常情况下，贷款核算系统在核心系统之前日切。",
        "贷款核算系统交易引擎分为联机引擎与批量引擎，批量引擎中包括：日终批量、联机批量及定时任务。",
        "主要功能说明",
        "产品工厂",
        "功能简述",
        "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。",
        "贷款开户",
        "功能简述",
        "支持一般、特殊等各种类型的贷款开户操作。",
        "贷款发放",
        "功能简述",
        "支持手动放款、渠道调用放款或根据合同约定的放款方式和金额进行自动贷款发放。",
        "贷款还款设置",
        "功能简述",
        "设置贷款还款方式，还款规则，还款账号等信息。",
        "贷款利率、费率设置",
        "功能简述",
        "灵活设置贷款利率、费率。",
        "贷款还款",
        "功能简述",
        "支持客户主动、渠道调用及按还款计划自动扣款等贷款还款方式。",
        "贷款核销及核销收回",
        "功能简述",
        "支持对非应计贷款进行核销，贷款催收回款后，进行核销贷款回收账务处理。",
        "贷款代偿",
        "功能简述",
        "对已放款且逾期，并满足代偿要求的贷款进行代偿操作。",
        "冲正功能",
        "功能简述",
        "支持对符合条件的贷款发放、贷款还款进行冲正。",
        "日终批量处理",
        "功能简述",
        "日终批处理时，根据系统配置的参数处理贷款账户计提、结息、自动扣收、对账文件的生成等过程。",
        "工作说明",
        "每年进行灾备演练，将生产数据导入到灾备库中进行数据检测，数据同步过程及步骤参照我行统一灾备演练流程。",
        "安全方案 | 安全方案 | 安全方案",
        "安全风险分级 | 高风险 □中风险 低风险 | 高风险 □中风险 低风险",
        "开发的时候需支持国密算法，新系统上线要求漏洞扫描、渗透测试",
        "实施风险",
        "说明项目实施的前提条件与风险，如人员、时间、技术工具、外部压力及其它方面的特殊问题描述。",
        "其它要求",
    ]
)

LOAN_ACCOUNTING_D4_NOISE_TEXT = "\n".join(
    [
        "数据高可用方案",
        "数据备份方案",
        "每年进行灾备演练，将生产数据导入到灾备库中进行数据检测，数据同步过程及步骤参照我行统一灾备演练流程。",
        "整体架构",
        "应用部署架构",
        "服务采用分布式集群部署方式，每台应用服务器均部署相同的功能模块，且互为备份。",
        "单中心数据库每个实例部署采用一主多从方式，数据支持物理拆分多个实例。",
        "系统逻辑架构",
        "系统采用组件化的模块设计方式和插件化的处理方式，具有结构清晰、符合标准、易于理解、扩展方便等优点。可根据实际需要灵活调整。",
        "提供系统参数可配置化管理功能，提供系统最大的灵活性和可扩展性。",
        "具备交易系统的基本可管理能力，包括流水登记、应用路由、流量控制、服务监控、异常诊断、资源监控、过程信息自动清理等；",
        "提供公共组件处理，包括日志、数据库连接池、应用配置、错误配置、数据标准映射、权限控制、订阅发布等。",
        "业务控制模块：主要实现信息访问权限控制、客户升降级处理、客户识别处理、相似客户扫描处理等功能",
        "系统管理模块：主要实现业务规则、系统参数、系统日志管理、数据分析报表管理等功能",
        "基础监控 业务监控 云监控",
        "高可用方案",
        "应用级 系统级 □其他 （请注明要点）",
        "安全方案 | 安全方案 | 安全方案",
        "安全架构说明 | 身份认证",
        "安全架构说明 | 应用安全",
        "（互联网应用至少满足一项） | 代码审计 渗透测试 漏洞扫描 □签名/验签",
        "安全架构说明 | 数据安全 | 用户密码是否加密传输及加密存储：是 □否 □不涉及；",
        "（2）密钥是否加密传输及加密存储：是 否 不涉及；",
        "（3）是否需要部署硬件加密机：是否；",
        "安全架构说明 | 其他需说明的内容 | 开发的时候需支持国密算法，新系统上线要求漏洞扫描、渗透测试",
    ]
)


def test_build_suggestions_does_not_fallback_to_heading_only_lines():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    suggestions, snapshot = adapter._build_suggestions(
        "requirements",
        "需求概述\n系统说明",
        "requirements_skill",
        ["requirements"],
    )

    assert suggestions == {}
    assert snapshot["target_fields"] == [
        "system_positioning.canonical.core_responsibility",
        "business_capabilities.canonical.functional_modules",
        "business_capabilities.canonical.business_scenarios",
        "business_capabilities.canonical.business_flows",
        "business_capabilities.canonical.data_reports",
        "constraints_risks.canonical.business_constraints",
        "constraints_risks.canonical.prerequisites",
        "constraints_risks.canonical.sensitive_points",
        "constraints_risks.canonical.risk_items",
    ]


def test_build_suggestions_general_mode_extracts_cross_domain_candidates():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    suggestions, snapshot = adapter._build_suggestions(
        "general",
        "\n".join(
            [
                "系统说明",
                "负责支付受理与渠道服务编排",
                "系统采用分层架构部署在内网区域",
                "对接核心系统提供贷款核算查询接口",
            ]
        ),
        "tech_solution_skill",
        ["requirements", "design", "tech_solution"],
    )

    assert suggestions["system_positioning.canonical.core_responsibility"]["value"] == "负责支付受理与渠道服务编排"
    assert suggestions["technical_architecture.canonical.architecture_style"]["value"] == "系统采用分层架构部署在内网区域"
    assert suggestions["integration_interfaces.canonical.other_integrations"]["value"]
    assert snapshot["compiled_doc_types"] == ["requirements", "design", "tech_solution"]


def test_build_suggestions_extracts_modules_and_scenarios_from_main_feature_section():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    suggestions, snapshot = adapter._build_suggestions(
        "tech_solution",
        "\n".join(
            [
                "业务背景",
                "通过贷款核算系统提供贷款生命周期相关完整的功能。",
                "需求概述",
                "支持放款、还款、计息和日终批量处理。",
                "主要功能说明",
                "产品工厂",
                "功能简述",
                "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。",
                "贷款开户",
                "功能简述",
                "支持一般、特殊等各种类型的贷款开户操作。",
                "贷款发放",
                "功能简述",
                "支持手动放款、渠道调用放款或根据合同约定的放款方式和金额进行自动贷款发放。",
                "日终批量处理",
                "功能简述",
                "根据系统配置的参数处理贷款账户计提、结息、自动扣收和对账文件生成。",
                "整体架构",
                "系统采用分层微服务架构。",
                "性能分析",
                "系统联机性能分析：预计日交易量20万、交易响应时间1s。",
                "批量性能分析：批量数据量200万、处理时间半小时。",
                "实施风险",
                "批量窗口紧张，依赖核心系统日终处理时点。",
            ]
        ),
        "tech_solution_skill",
        ["requirements", "design", "tech_solution"],
    )

    assert snapshot["compiled_doc_types"] == ["requirements", "design", "tech_solution"]
    assert suggestions["business_capabilities.canonical.functional_modules"]["value"] == [
        {"name": "产品工厂", "description": "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。"},
        {"name": "贷款开户", "description": "支持一般、特殊等各种类型的贷款开户操作。"},
        {"name": "贷款发放", "description": "支持手动放款、渠道调用放款或根据合同约定的放款方式和金额进行自动贷款发放。"},
        {"name": "日终批量处理", "description": "根据系统配置的参数处理贷款账户计提、结息、自动扣收和对账文件生成。"},
    ]
    scenarios = suggestions["business_capabilities.canonical.business_scenarios"]["value"]
    assert {"name": "产品工厂", "description": "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。"} in scenarios
    assert {"name": "贷款开户", "description": "支持一般、特殊等各种类型的贷款开户操作。"} in scenarios
    assert suggestions["technical_architecture.canonical.performance_baseline"]["value"]["online"]["p95_latency_ms"] == "1000"


def test_build_suggestions_extracts_requirements_modules_from_non_fixed_function_sections():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    suggestions, snapshot = adapter._build_suggestions(
        "requirements",
        "\n".join(
            [
                "第一章 引言",
                "编写目的",
                "本文档编写的目的是说明贷款核算系统需求。",
                "业务背景",
                "贷款核算系统负责贷款生命周期内的账务处理、计息结息和批量对账。",
                "第三章 功能描述",
                "3.1 功能分类",
                "产品工厂",
                "贷款开户",
                "3.2 功能描述",
                "产品工厂：维护贷款产品定义和参数配置。",
                "贷款开户：支持一般贷款、特殊贷款开户和信息校验。",
                "其他要求",
                "本文档需经评审后发布。",
            ]
        ),
        "requirements_skill",
        ["requirements"],
    )

    assert snapshot["compiled_doc_types"] == ["requirements"]
    assert suggestions["system_positioning.canonical.core_responsibility"]["value"] == "贷款核算系统负责贷款生命周期内的账务处理、计息结息和批量对账。"
    assert suggestions["system_positioning.canonical.core_responsibility"]["value"] != "本文档编写的目的是说明贷款核算系统需求。"
    assert suggestions["business_capabilities.canonical.functional_modules"]["value"] == [
        {"name": "产品工厂", "description": "维护贷款产品定义和参数配置。"},
        {"name": "贷款开户", "description": "支持一般贷款、特殊贷款开户和信息校验。"},
    ]
    assert suggestions["business_capabilities.canonical.business_scenarios"]["value"] == [
        {"name": "产品工厂", "description": "维护贷款产品定义和参数配置。"},
        {"name": "贷款开户", "description": "支持一般贷款、特殊贷款开户和信息校验。"},
    ]


def test_build_suggestions_extracts_general_d4_design_deployment_and_quality_fields():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    suggestions, _snapshot = adapter._build_suggestions(
        "tech_solution",
        LOAN_ACCOUNTING_TECH_SOLUTION_TEXT,
        "tech_solution_skill",
        ["requirements", "design", "tech_solution"],
    )

    assert suggestions["technical_architecture.canonical.extensions.deployment_mode"]["value"] == (
        "服务采用分布式集群部署方式，每台应用服务器均部署相同的功能模块，且互为备份。"
    )
    assert suggestions["technical_architecture.canonical.extensions.topology_characteristics"]["value"] == [
        "单中心数据库每个实例部署采用一主多从方式，数据支持物理拆分多个实例。"
    ]
    assert suggestions["technical_architecture.canonical.extensions.infrastructure_components"]["value"] == [
        "云上统一服务注册中心",
        "内联网关",
        "服务总线",
    ]
    assert suggestions["technical_architecture.canonical.extensions.design_methods"]["value"] == [
        "系统采用组件化的模块设计方式和插件化的处理方式，具有结构清晰、符合标准、易于理解、扩展方便等优点。",
        "提供系统参数可配置化管理功能，提供系统最大的灵活性和可扩展性。",
    ]
    assert suggestions["technical_architecture.canonical.extensions.common_capabilities"]["value"] == [
        "具备交易系统的基本可管理能力，包括流水登记、应用路由、流量控制、服务监控、异常诊断、资源监控、过程信息自动清理等",
        "提供公共组件处理，包括日志、数据库连接池、应用配置、错误配置、数据标准映射、权限控制、订阅发布等。",
    ]
    assert suggestions["technical_architecture.canonical.extensions.availability_design"]["value"] == [
        "服务采用分布式集群部署方式，每台应用服务器均部署相同的功能模块，且互为备份。",
        "单中心数据库每个实例部署采用一主多从方式，数据支持物理拆分多个实例。",
        "每年进行灾备演练，将生产数据导入到灾备库中进行数据检测，数据同步过程及步骤参照我行统一灾备演练流程。",
    ]
    assert suggestions["technical_architecture.canonical.extensions.security_requirements"]["value"] == [
        "开发的时候需支持国密算法，新系统上线要求漏洞扫描、渗透测试"
    ]


def test_build_suggestions_filters_d4_noise_from_tables_headings_and_module_descriptions():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    suggestions, _snapshot = adapter._build_suggestions(
        "tech_solution",
        LOAN_ACCOUNTING_D4_NOISE_TEXT,
        "tech_solution_skill",
        ["design", "tech_solution"],
    )

    assert suggestions["technical_architecture.canonical.extensions.common_capabilities"]["value"] == [
        "具备交易系统的基本可管理能力，包括流水登记、应用路由、流量控制、服务监控、异常诊断、资源监控、过程信息自动清理等",
        "提供公共组件处理，包括日志、数据库连接池、应用配置、错误配置、数据标准映射、权限控制、订阅发布等。",
    ]
    assert suggestions["technical_architecture.canonical.extensions.availability_design"]["value"] == [
        "每年进行灾备演练，将生产数据导入到灾备库中进行数据检测，数据同步过程及步骤参照我行统一灾备演练流程。",
        "服务采用分布式集群部署方式，每台应用服务器均部署相同的功能模块，且互为备份。",
        "单中心数据库每个实例部署采用一主多从方式，数据支持物理拆分多个实例。",
    ]
    assert suggestions["technical_architecture.canonical.extensions.security_requirements"]["value"] == [
        "开发的时候需支持国密算法，新系统上线要求漏洞扫描、渗透测试"
    ]


def test_quality_report_flags_recognized_main_feature_section_without_d2_candidate():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    suggestions, snapshot = adapter._build_suggestions(
        "tech_solution",
        "\n".join(
            [
                "需求概述",
                "系统用于承接贷款全流程支撑。",
                "主要功能说明",
                "功能简述",
                "仅做业务摘要。",
            ]
        ),
        "tech_solution_skill",
        ["requirements", "tech_solution"],
    )

    quality_report = adapter._build_quality_report(
        target_fields=snapshot["target_fields"],
        suggestions=suggestions,
        facts=[],
        llm_bundle={"llm_used": False, "error": None, "related_systems": []},
        section_analysis=snapshot["section_analysis"],
    )
    review_queue = adapter._build_review_queue(
        quality_report=quality_report,
        llm_bundle={"llm_used": False, "error": None, "related_systems": []},
        suggestions=suggestions,
        section_analysis=snapshot["section_analysis"],
    )

    assert any(
        gap["target_field"] == "business_capabilities.canonical.functional_modules"
        for gap in quality_report["recognized_section_gaps"]
    )
    assert any(item["reason"] == "recognized_section_without_candidate" for item in review_queue)


def test_quality_report_records_semantic_gate_rejections():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    suggestions, snapshot = adapter._build_suggestions(
        "requirements",
        "\n".join(
            [
                "编写目的",
                "本文档编写的目的是说明贷款核算系统需求。",
            ]
        ),
        "requirements_skill",
        ["requirements"],
    )

    quality_report = adapter._build_quality_report(
        target_fields=snapshot["target_fields"],
        suggestions=suggestions,
        facts=[],
        llm_bundle={"llm_used": False, "error": None, "related_systems": []},
        rejected_candidates=snapshot["rejected_candidates"],
        section_analysis=snapshot["section_analysis"],
    )

    assert suggestions == {}
    assert quality_report["validator_failures"] == [
        {
            "field_path": "system_positioning.canonical.core_responsibility",
            "logical_field": "system_positioning.core_responsibility",
            "reason": "document_purpose_noise",
        }
    ]
    assert quality_report["rejected_candidates"][0]["field_path"] == "system_positioning.canonical.core_responsibility"


def test_build_llm_candidate_entries_skips_governed_d3_fields():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    entries = adapter._build_llm_candidate_entries(
        llm_bundle={
            "suggestions": {
                "integration_interfaces": {
                    "canonical": {
                        "provided_services": [{"service_name": "文档推断服务"}],
                        "consumed_services": [{"service_name": "文档推断依赖"}],
                        "other_integrations": ["对接核心系统提供贷款核算查询接口"],
                    }
                }
            }
        },
        source_lines=["对接核心系统提供贷款核算查询接口"],
    )

    assert "integration_interfaces.canonical.provided_services" not in entries
    assert "integration_interfaces.canonical.consumed_services" not in entries
    assert entries["integration_interfaces.canonical.other_integrations"]["value"] == [
        "对接核心系统提供贷款核算查询接口"
    ]


def test_build_suggestions_uses_real_main_feature_section_instead_of_toc_and_inline_noise():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    suggestions, snapshot = adapter._build_suggestions(
        "tech_solution",
        LOAN_ACCOUNTING_TECH_SOLUTION_TEXT,
        "tech_solution_skill",
        ["requirements", "design", "tech_solution"],
    )

    assert not any(
        line.startswith("产品工厂：")
        for line in snapshot["section_analysis"]["positioning_lines"]
    )
    assert snapshot["section_analysis"]["module_titles"] == [
        "产品工厂",
        "贷款开户",
        "贷款发放",
        "贷款还款设置",
        "贷款利率、费率设置",
        "贷款还款",
        "贷款核销及核销收回",
        "贷款代偿",
        "冲正功能",
        "日终批量处理",
    ]
    assert suggestions["business_capabilities.canonical.functional_modules"]["value"] == [
        {"name": "产品工厂", "description": "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。"},
        {"name": "贷款开户", "description": "支持一般、特殊等各种类型的贷款开户操作。"},
        {"name": "贷款发放", "description": "支持手动放款、渠道调用放款或根据合同约定的放款方式和金额进行自动贷款发放。"},
        {"name": "贷款还款设置", "description": "设置贷款还款方式，还款规则，还款账号等信息。"},
        {"name": "贷款利率、费率设置", "description": "灵活设置贷款利率、费率。"},
        {"name": "贷款还款", "description": "支持客户主动、渠道调用及按还款计划自动扣款等贷款还款方式。"},
        {"name": "贷款核销及核销收回", "description": "支持对非应计贷款进行核销，贷款催收回款后，进行核销贷款回收账务处理。"},
        {"name": "贷款代偿", "description": "对已放款且逾期，并满足代偿要求的贷款进行代偿操作。"},
        {"name": "冲正功能", "description": "支持对符合条件的贷款发放、贷款还款进行冲正。"},
        {"name": "日终批量处理", "description": "日终批处理时，根据系统配置的参数处理贷款账户计提、结息、自动扣收、对账文件的生成等过程；完成与核心以及总账系统的对账处理；完成对数仓的供数操作。"},
    ]
    scenarios = suggestions["business_capabilities.canonical.business_scenarios"]["value"]
    assert {"name": "产品工厂", "description": "灵活新建和复制现有贷款产品，并对贷款基本信息进行维护。"} in scenarios
    assert {
        "name": "日终批量处理",
        "description": "日终批处理时，根据系统配置的参数处理贷款账户计提、结息、自动扣收、对账文件的生成等过程；完成与核心以及总账系统的对账处理；完成对数仓的供数操作。",
    } in scenarios


def test_build_suggestions_filters_d3_d4_d5_noise_for_loan_accounting_style_doc():
    adapter = DocumentSkillAdapter.__new__(DocumentSkillAdapter)

    suggestions, _ = adapter._build_suggestions(
        "tech_solution",
        LOAN_ACCOUNTING_TECH_SOLUTION_TEXT,
        "tech_solution_skill",
        ["requirements", "design", "tech_solution"],
    )

    assert suggestions["technical_architecture.canonical.architecture_style"]["value"] == (
        "服务采用分布式集群部署方式，每台应用服务器均部署相同的功能模块，且互为备份。"
    )
    assert suggestions["technical_architecture.canonical.network_zone"]["value"] == (
        "贷款核算系统通过内联网关与服务总线与行内各业务系统相连。"
    )
    assert "technical_architecture.canonical.performance_baseline" not in suggestions

    integrations = suggestions["integration_interfaces.canonical.other_integrations"]["value"]
    assert any(
        item.startswith("在线融资系统调用核心贷款开立，贷款回收，贷款余额查询接口进行贷款交易，并通过每日日终批量")
        for item in integrations
    )
    assert any(
        item.startswith("贷款核算通过云上内联网关访问云下esb，调用核心，统一支付，互联网支付接口")
        for item in integrations
    )
    assert not any(item.startswith("贷款发放：") for item in integrations)
    assert not any(item.startswith("贷款还款：") for item in integrations)

    assert "constraints_risks.canonical.technical_constraints" not in suggestions
    assert "constraints_risks.canonical.business_constraints" not in suggestions
    assert "constraints_risks.canonical.known_risks" not in suggestions
